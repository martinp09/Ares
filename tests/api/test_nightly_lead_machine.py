import pytest

from app.db.source_runs import source_runs_repository

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


@pytest.fixture(autouse=True)
def reset_source_runs_repository():
    source_runs_repository.reset()
    yield
    source_runs_repository.reset()


def _payload():
    return {
        "business_id": "biz-api",
        "environment": "test",
        "source_runs": [
            {
                "source_key": "probate-api",
                "source_label": "Probate API fixture",
                "source_lane": "harris_county_probate",
                "artifacts": [
                    {
                        "path": "artifacts/probate-api.jsonl",
                        "artifact_type": "fixture_jsonl",
                        "record_count": 2,
                        "metadata": {"hot_lead_count": 1, "blocked_count": 1},
                    }
                ],
            }
        ],
    }


def test_nightly_source_pull_endpoint_returns_expected_shape(client):
    response = client.post("/lead-machine/internal/nightly-source-pull", json=_payload(), headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["would_call_external_sources"] is False
    assert body["live_source_calls_enabled"] is False
    assert body["source_runs"][0]["source_key"] == "probate-api"
    assert body["source_runs"][0]["artifacts"][0]["path"] == "artifacts/probate-api.jsonl"
    assert body["morning_brief"]["new_record_count"] == 2
    assert body["morning_brief"]["hot_lead_count"] == 1
    assert body["morning_brief"]["blocked_count"] == 1


def test_morning_brief_endpoint_builds_from_existing_runs(client):
    first = client.post("/lead-machine/internal/nightly-source-pull", json=_payload(), headers=AUTH_HEADERS)
    assert first.status_code == 200

    response = client.post(
        "/lead-machine/internal/morning-brief",
        json={"business_id": "biz-api", "environment": "test"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["new_record_count"] == 2
    assert body["source_runs"][0]["source_key"] == "probate-api"


def test_mission_control_latest_brief_and_source_runs(client):
    created = client.post("/lead-machine/internal/nightly-source-pull", json=_payload(), headers=AUTH_HEADERS)
    assert created.status_code == 200

    latest = client.get(
        "/mission-control/morning-brief/latest?business_id=biz-api&environment=test",
        headers=AUTH_HEADERS,
    )
    assert latest.status_code == 200
    assert latest.json()["morning_brief"]["new_record_count"] == 2

    runs = client.get(
        "/mission-control/source-runs?business_id=biz-api&environment=test&source_lane=harris_county_probate",
        headers=AUTH_HEADERS,
    )
    assert runs.status_code == 200
    assert [run["source_key"] for run in runs.json()["source_runs"]] == ["probate-api"]


def test_endpoints_require_auth(client):
    response = client.post("/lead-machine/internal/nightly-source-pull", json=_payload())
    assert response.status_code in {401, 403}

    response = client.get("/mission-control/morning-brief/latest?business_id=biz-api&environment=test")
    assert response.status_code in {401, 403}


def test_unknown_fields_are_rejected(client):
    payload = _payload()
    payload["unknown"] = True
    response = client.post("/lead-machine/internal/nightly-source-pull", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422

    artifact_payload = _payload()
    artifact_payload["source_runs"][0]["artifacts"][0]["county_url"] = "https://example.invalid"
    response = client.post("/lead-machine/internal/nightly-source-pull", json=artifact_payload, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_live_source_calls_endpoint_rejected(client):
    payload = _payload()
    payload["live_source_calls"] = True
    response = client.post("/lead-machine/internal/nightly-source-pull", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422
    assert "live source calls are disabled" in response.json()["detail"]



def test_runtime_endpoints_accept_trigger_lifecycle_fields(client):
    payload = _payload()
    payload.update(
        {
            "run_id": "run_123",
            "command_id": "cmd_123",
            "idempotency_key": "nightly-life-key",
            "trigger_run_id": "trig_123",
        }
    )
    response = client.post("/lead-machine/internal/nightly-source-pull", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200

    brief_response = client.post(
        "/lead-machine/internal/morning-brief",
        json={
            "business_id": "biz-api",
            "environment": "test",
            "run_id": "run_456",
            "command_id": "cmd_456",
            "idempotency_key": "brief-life-key",
            "trigger_run_id": "trig_456",
        },
        headers=AUTH_HEADERS,
    )
    assert brief_response.status_code == 200


def test_nightly_source_pull_idempotency_key_replays_without_appending_runs(client):
    payload = _payload()
    payload["idempotency_key"] = "api-nightly-key"

    first = client.post("/lead-machine/internal/nightly-source-pull", json=payload, headers=AUTH_HEADERS)
    second = client.post("/lead-machine/internal/nightly-source-pull", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["source_runs"][0]["id"] == first.json()["source_runs"][0]["id"]

    runs = client.get("/mission-control/source-runs?business_id=biz-api&environment=test", headers=AUTH_HEADERS)
    assert len(runs.json()["source_runs"]) == 1


def test_morning_brief_idempotency_key_keeps_counts_stable(client):
    created = client.post("/lead-machine/internal/nightly-source-pull", json=_payload(), headers=AUTH_HEADERS)
    assert created.status_code == 200

    request = {"business_id": "biz-api", "environment": "test", "idempotency_key": "api-brief-key"}
    first = client.post("/lead-machine/internal/morning-brief", json=request, headers=AUTH_HEADERS)
    assert first.status_code == 200

    extra = _payload()
    extra["source_runs"][0]["source_key"] = "extra-api"
    extra["source_runs"][0]["record_count"] = 50
    extra["source_runs"][0].pop("artifacts")
    assert client.post("/lead-machine/internal/nightly-source-pull", json=extra, headers=AUTH_HEADERS).status_code == 200

    second = client.post("/lead-machine/internal/morning-brief", json=request, headers=AUTH_HEADERS)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["new_record_count"] == first.json()["new_record_count"] == 2


def test_mission_control_source_run_and_brief_responses_do_not_echo_raw_metadata(client):
    payload = _payload()
    payload["metadata"] = {"operator_secret": "TOP-SECRET-BRIEF"}
    payload["source_runs"][0]["metadata"] = {"provider_secret": "TOP-SECRET-RUN"}
    payload["source_runs"][0]["artifacts"][0]["metadata"] = {"artifact_secret": "TOP-SECRET-ARTIFACT"}
    created = client.post("/lead-machine/internal/nightly-source-pull", json=payload, headers=AUTH_HEADERS)
    assert created.status_code == 200

    latest = client.get(
        "/mission-control/morning-brief/latest?business_id=biz-api&environment=test",
        headers=AUTH_HEADERS,
    )
    runs = client.get(
        "/mission-control/source-runs?business_id=biz-api&environment=test",
        headers=AUTH_HEADERS,
    )
    assert latest.status_code == 200
    assert runs.status_code == 200
    response_text = f"{latest.text}\n{runs.text}"
    assert "TOP-SECRET-BRIEF" not in response_text
    assert "TOP-SECRET-RUN" not in response_text
    assert "TOP-SECRET-ARTIFACT" not in response_text
    assert latest.json()["morning_brief"]["new_record_count"] == 2
    assert runs.json()["source_runs"][0]["source_lane"] == "harris_county_probate"
