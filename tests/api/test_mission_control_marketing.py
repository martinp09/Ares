from datetime import UTC, datetime, timedelta

from app.models.mission_control import (
    MissionControlContactRecord,
    MissionControlMessageRecord,
    MissionControlThreadRecord,
)
from app.services.mission_control_service import mission_control_service
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_dashboard_endpoint_returns_marketing_read_model_counts(client) -> None:
    reset_control_plane_state()
    base_time = datetime(2026, 4, 14, 14, 0, tzinfo=UTC)
    due_at = base_time - timedelta(minutes=10)

    mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=1,
            contact=MissionControlContactRecord(
                display_name="Alex Booker",
                phone="+15551230001",
            ),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="I can talk after work, what are my next steps?",
                    created_at=base_time - timedelta(minutes=3),
                )
            ],
            context={
                "booking_status": "pending",
                "sequence_status": "active",
                "next_sequence_step": "day_2_sms",
                "manual_call_due_at": due_at.isoformat(),
                "reply_needs_review": True,
            },
            created_at=base_time - timedelta(minutes=20),
            updated_at=base_time,
        )
    )
    mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="waiting",
            unread_count=0,
            contact=MissionControlContactRecord(
                display_name="Sam Booked",
                phone="+15551230002",
            ),
            messages=[],
            context={
                "booking_status": "booked",
                "sequence_status": "completed",
                "reply_needs_review": False,
            },
            created_at=base_time - timedelta(minutes=22),
            updated_at=base_time - timedelta(minutes=1),
        )
    )

    response = client.get(
        "/mission-control/dashboard?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pending_lead_count"] == 1
    assert body["booked_lead_count"] == 1
    assert body["active_non_booker_enrollment_count"] == 1
    assert body["due_manual_call_count"] == 1
    assert body["replies_needing_review_count"] == 1


def test_inbox_and_tasks_endpoints_return_marketing_thread_state(client) -> None:
    reset_control_plane_state()
    base_time = datetime(2026, 4, 14, 16, 30, tzinfo=UTC)
    due_at = base_time + timedelta(minutes=15)

    thread = mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=2,
            contact=MissionControlContactRecord(
                display_name="Jordan Pending",
                phone="+15551230003",
                email="jordan@example.com",
            ),
            messages=[
                MissionControlMessageRecord(
                    direction="outbound",
                    channel="sms",
                    body="Thanks for reaching out. Can we confirm your timeline?",
                    created_at=base_time - timedelta(minutes=6),
                ),
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Yes, if it helps I can call tonight.",
                    created_at=base_time - timedelta(minutes=2),
                ),
            ],
            context={
                "booking_status": "pending",
                "sequence_status": "active",
                "next_sequence_step": "manual_call_day_3",
                "manual_call_due_at": due_at.isoformat(),
                "reply_needs_review": True,
            },
            created_at=base_time - timedelta(minutes=20),
            updated_at=base_time,
        )
    )

    inbox_response = client.get(
        f"/mission-control/inbox?business_id=limitless&environment=dev&selected_thread_id={thread.id}",
        headers=AUTH_HEADERS,
    )
    assert inbox_response.status_code == 200
    inbox_body = inbox_response.json()
    selected_thread = inbox_body["selected_thread"]
    assert selected_thread["booking_status"] == "pending"
    assert selected_thread["sequence_status"] == "active"
    assert selected_thread["next_sequence_step"] == "manual_call_day_3"
    assert selected_thread["manual_call_due_at"] == due_at.isoformat()
    assert selected_thread["recent_reply_preview"] == "Yes, if it helps I can call tonight."
    assert selected_thread["reply_needs_review"] is True

    tasks_response = client.get(
        "/mission-control/tasks?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert tasks_response.status_code == 200
    tasks_body = tasks_response.json()
    assert tasks_body["due_count"] == 1
    assert tasks_body["tasks"] == [
        {
            "thread_id": thread.id,
            "lead_name": "Jordan Pending",
            "channel": "sms",
            "booking_status": "pending",
            "sequence_status": "active",
            "next_sequence_step": "manual_call_day_3",
            "manual_call_due_at": due_at.isoformat(),
            "recent_reply_preview": "Yes, if it helps I can call tonight.",
            "reply_needs_review": True,
        }
    ]
