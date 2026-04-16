from app.models.providers import ProviderTransportError
from app.providers.instantly import InstantlyClient


def test_bulk_add_respects_batch_size_and_waits_between_batches() -> None:
    requests: list[dict] = []
    sleeps: list[float] = []

    def sender(payload: dict) -> dict:
        requests.append(payload)
        return {"ok": True, "accepted": len(payload["payload"]["leads"])}

    client = InstantlyClient(api_key="inst_123", request_sender=sender, sleep_fn=sleeps.append, batch_size=100)

    leads = [{"email": f"lead{index}@example.com"} for index in range(230)]
    responses = client.bulk_add_leads(leads, campaign_id="cmp_123")

    assert len(responses) == 3
    assert [response["accepted"] for response in responses] == [100, 100, 30]
    assert [len(request_payload["payload"]["leads"]) for request_payload in requests] == [100, 100, 30]
    assert sleeps == [0.25, 0.25]


def test_bulk_add_fails_fast_after_repeated_rate_limits() -> None:
    attempts: list[int] = []

    def sender(_: dict) -> dict:
        attempts.append(1)
        raise ProviderTransportError("rate limited", status_code=429, headers={"Retry-After": "0"})

    client = InstantlyClient(api_key="inst_123", request_sender=sender, sleep_fn=lambda _: None)

    try:
        client.bulk_add_leads([{"email": "lead@example.com"}], campaign_id="cmp_123")
    except ProviderTransportError as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("expected ProviderTransportError")

    assert len(attempts) == 3
