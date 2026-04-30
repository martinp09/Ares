import csv
from pathlib import Path

from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def write_source_fixture(source_dir: Path) -> None:
    source_dir.mkdir(parents=True)
    rows = [
        {
            "priority_tier": "HOT",
            "priority_score": "95",
            "case_number": "543001",
            "decedent_name": "Jane Hot",
            "email": "hot@example.com",
            "phone": "+13460000001",
            "mailing_address": "1 Hot St Houston TX",
            "priority_flags": "tax;heirship",
        },
        {
            "priority_tier": "WARM",
            "priority_score": "55",
            "case_number": "543002",
            "decedent_name": "John Warm",
            "email": "",
            "phone": "+13460000002",
            "mailing_address": "2 Warm St Houston TX",
            "priority_flags": "applicant_address",
        },
        {
            "priority_tier": "REST",
            "priority_score": "15",
            "case_number": "543003",
            "decedent_name": "Cold Lead",
            "email": "cold@example.com",
            "phone": "",
            "mailing_address": "3 Cold St Houston TX",
            "priority_flags": "",
        },
    ]
    with (source_dir / "hot_warm_ranked_enriched.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_campaign_launch_preview_exports_segments_and_channel_manifests(client, tmp_path) -> None:
    reset_control_plane_state()
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "exports"
    write_source_fixture(source_dir)

    response = client.get(
        "/mission-control/campaign-launches/harris-probate-hot-warm-cold",
        params={"source_directory": str(source_dir), "output_directory": str(output_dir)},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["campaign_slug"] == "harris-probate-hot-warm-cold-2026-04-30"
    assert body["total_lead_count"] == 3
    assert {segment["segment"]: segment["source_count"] for segment in body["segments"]} == {
        "HOT": 1,
        "WARM": 1,
        "COLD": 1,
    }
    assert body["channel_totals"] == {"email": 2, "sms": 2, "direct_mail": 3}
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "hot-email.csv").exists()
    assert (output_dir / "warm-sms.csv").exists()
    assert (output_dir / "cold-direct_mail.csv").exists()
    hot_email = (output_dir / "hot-email.csv").read_text(encoding="utf-8")
    assert "do_not_send_before_approval" in hot_email
    assert "hot@example.com" in hot_email


def test_campaign_launch_approval_creates_pending_approval_without_live_send(client, tmp_path) -> None:
    reset_control_plane_state()
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "exports"
    write_source_fixture(source_dir)

    response = client.post(
        "/mission-control/campaign-launches/harris-probate-hot-warm-cold/approval",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "source_directory": str(source_dir),
            "output_directory": str(output_dir),
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["approval_status"] == "pending"
    assert body["payload_snapshot"]["live_send_policy"] == (
        "approval_required_before_any_instantly_textgrid_or_direct_mail_vendor_enrollment"
    )
    assert body["approval_id"].startswith("apr_")
    assert body["command_id"].startswith("cmd_")
    assert body["payload_snapshot"]["approval_scope"] == "exports_and_provider_enrollment_gate"
