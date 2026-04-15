from fastapi.testclient import TestClient

from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_marketing_internal_non_booker_check_matches_trigger_contract(monkeypatch) -> None:
    class StubBookingService:
        def run_non_booker_check(self, request):
            assert request.lead_id == "lead_1"
            assert request.business_id == "limitless"
            assert request.environment == "dev"
            return {
                "booking_status": "pending",
                "should_enroll_in_sequence": True,
                "start_day": 0,
            }

    from app.api import marketing as marketing_api

    monkeypatch.setattr(marketing_api, "booking_service", StubBookingService())
    client = TestClient(app)

    response = client.post(
        "/marketing/internal/non-booker-check",
        json={"leadId": "lead_1", "businessId": "limitless", "environment": "dev"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == {
        "bookingStatus": "pending",
        "shouldEnrollInSequence": True,
        "startDay": 0,
    }


def test_marketing_internal_sequence_guard_matches_trigger_contract(monkeypatch) -> None:
    class StubBookingService:
        def get_lease_option_sequence_guard(self, request):
            assert request.day == 2
            return {
                "booking_status": "pending",
                "sequence_status": "active",
                "opted_out": False,
            }

    from app.api import marketing as marketing_api

    monkeypatch.setattr(marketing_api, "booking_service", StubBookingService())
    client = TestClient(app)

    response = client.post(
        "/marketing/internal/lease-option-sequence/guard",
        json={
            "leadId": "lead_1",
            "businessId": "limitless",
            "environment": "dev",
            "day": 2,
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == {
        "bookingStatus": "pending",
        "sequenceStatus": "active",
        "optedOut": False,
    }


def test_marketing_internal_sequence_step_matches_trigger_contract(monkeypatch) -> None:
    class StubInboundSmsService:
        def dispatch_lease_option_sequence_step(self, request):
            assert request.template_id == "lease_option_day_2_sms"
            assert request.channel == "sms"
            return {
                "message_id": "msg_123",
                "channel": request.channel,
                "status": "queued",
            }

    from app.api import marketing as marketing_api

    monkeypatch.setattr(marketing_api, "inbound_sms_service", StubInboundSmsService())
    client = TestClient(app)

    response = client.post(
        "/marketing/internal/lease-option-sequence/step",
        json={
            "leadId": "lead_1",
            "businessId": "limitless",
            "environment": "dev",
            "day": 2,
            "channel": "sms",
            "templateId": "lease_option_day_2_sms",
            "manualCallCheckpoint": True,
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == {
        "messageId": "msg_123",
        "channel": "sms",
        "status": "queued",
    }


def test_marketing_internal_manual_call_task_matches_trigger_contract(monkeypatch) -> None:
    class StubBookingService:
        def create_manual_call_task(self, request):
            assert request.reason == "lease_option_sequence_checkpoint"
            return {"task_id": "task_456", "status": "open"}

    from app.api import marketing as marketing_api

    monkeypatch.setattr(marketing_api, "booking_service", StubBookingService())
    client = TestClient(app)

    response = client.post(
        "/marketing/internal/manual-call-task",
        json={
            "leadId": "lead_1",
            "businessId": "limitless",
            "environment": "dev",
            "sequenceDay": 2,
            "reason": "lease_option_sequence_checkpoint",
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == {"taskId": "task_456", "status": "open"}
