AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_ares_run_executes_phase1_runtime_path(client) -> None:
    response = client.post(
        "/ares/run",
        json={
            "run": {
                "counties": ["harris", "travis"],
                "include_briefs": True,
                "include_drafts": True,
            },
            "probate_records": [
                {
                    "county": "harris",
                    "source_lane": "probate",
                    "property_address": "123 Main St, Houston, TX",
                    "owner_name": "Estate of Jane Doe",
                },
                {
                    "county": "travis",
                    "source_lane": "probate",
                    "property_address": "88 River Rd, Austin, TX",
                    "owner_name": "Alex Rivers",
                },
            ],
            "tax_records": [
                {
                    "county": "harris",
                    "source_lane": "tax_delinquent",
                    "property_address": "123 Main St, Houston, TX",
                    "owner_name": "Estate of Jane Doe",
                },
                {
                    "county": "dallas",
                    "source_lane": "tax_delinquent",
                    "property_address": "999 Elm St, Dallas, TX",
                    "owner_name": "Estate of Filtered Out",
                },
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counties"] == ["harris", "travis"]
    assert body["lead_count"] == 2
    assert body["include_briefs"] is True
    assert body["include_drafts"] is True

    ranked = body["ranked_leads"]
    assert ranked[0]["rank"] == 1
    assert ranked[0]["tier"] == "PROBATE_WITH_VERIFIED_TAX"
    assert ranked[0]["lead"]["county"] == "harris"
    assert ranked[0]["tax_delinquent"] is True
    assert ranked[0]["brief"]["rank"] == 1
    assert ranked[0]["draft"]["approval_status"] == "pending_human_approval"

    assert ranked[1]["rank"] == 2
    assert ranked[1]["tier"] == "PROBATE_ONLY"
    assert ranked[1]["lead"]["county"] == "travis"
    assert ranked[1]["tax_delinquent"] is False


def test_ares_run_honors_copy_flags(client) -> None:
    response = client.post(
        "/ares/run",
        json={
            "run": {
                "counties": ["harris"],
                "include_briefs": False,
                "include_drafts": False,
            },
            "probate_records": [
                {
                    "county": "harris",
                    "source_lane": "probate",
                    "property_address": "123 Main St, Houston, TX",
                }
            ],
            "tax_records": [],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lead_count"] == 1
    assert body["include_briefs"] is False
    assert body["include_drafts"] is False
    assert body["ranked_leads"][0]["brief"] is None
    assert body["ranked_leads"][0]["draft"] is None


def test_ares_execution_run_triggers_bounded_execution_path(client) -> None:
    response = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris", "travis"],
            "action_budget": 6,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                    "tax": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                },
                "travis": {
                    "probate": [
                        {
                            "property_address": "88 River Rd, Austin, TX",
                            "owner_name": "Alex Rivers",
                        }
                    ],
                    "tax": [],
                },
            },
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["business_id"] == "limitless"
    assert body["environment"] == "dev"
    assert body["state"] == "completed"
    assert body["lead_count"] == 2
    assert body["interrupted"] is False
    assert body["failures"] == []
    assert body["ranked_leads"][0]["tier"] == "PROBATE_WITH_VERIFIED_TAX"
    assert body["ranked_leads"][0]["tax_delinquent"] is True
    assert body["ranked_leads"][1]["tier"] == "PROBATE_ONLY"


def test_ares_execution_run_excludes_tax_only_non_estate_records(client) -> None:
    response = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "action_budget": 6,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [],
                    "tax": [
                        {
                            "property_address": "999 Main St, Houston, TX",
                            "owner_name": "John Doe",
                        }
                    ],
                }
            },
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lead_count"] == 0
    assert body["ranked_leads"] == []
