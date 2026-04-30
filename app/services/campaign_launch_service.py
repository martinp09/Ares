from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.approvals import ApprovalsRepository
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.commands import CommandsRepository
from app.db.runs import RunsRepository
from app.models.approvals import ApprovalRecord
from app.models.commands import CommandPolicy, CommandStatus
from app.services.approval_service import ApprovalService

DEFAULT_HARRIS_PROBATE_SOURCE_DIR = Path("/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw")
DEFAULT_HARRIS_PROBATE_EXPORT_DIR = Path("docs/marketing/exports/harris-probate-2026-04-30")
HARRIS_PROBATE_CAMPAIGN_SLUG = "harris-probate-hot-warm-cold-2026-04-30"
HARRIS_PROBATE_COMMAND_TYPE = "campaign.launch.approve_exports"


@dataclass(frozen=True, slots=True)
class CampaignLaunchExport:
    channel: str
    segment: str
    path: str
    record_count: int


@dataclass(frozen=True, slots=True)
class CampaignLaunchSegment:
    segment: str
    source_count: int
    email_ready_count: int
    sms_ready_count: int
    direct_mail_ready_count: int
    recommended_daily_cap: int
    exports: list[CampaignLaunchExport]


@dataclass(frozen=True, slots=True)
class CampaignLaunchPreview:
    campaign_slug: str
    source_directory: str
    output_directory: str
    total_lead_count: int
    segments: list[CampaignLaunchSegment]
    channel_totals: dict[str, int]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class CampaignLaunchApproval:
    campaign_slug: str
    command_id: str
    approval_id: str
    approval_status: str
    payload_snapshot: dict[str, Any]


class CampaignLaunchService:
    def __init__(self, client: ControlPlaneClient | None = None) -> None:
        self.client = client or get_control_plane_client()
        self.commands_repository = CommandsRepository(client=self.client)
        approval_repository = ApprovalsRepository(client=self.client)
        self.approval_service = ApprovalService(
            approvals_repository=approval_repository,
            commands_repository=self.commands_repository,
            runs_repository=RunsRepository(client=self.client),
        )

    def build_harris_probate_preview(
        self,
        *,
        source_directory: Path | str = DEFAULT_HARRIS_PROBATE_SOURCE_DIR,
        output_directory: Path | str = DEFAULT_HARRIS_PROBATE_EXPORT_DIR,
    ) -> CampaignLaunchPreview:
        source_path = Path(source_directory)
        output_path = Path(output_directory)
        rows = self._read_source_rows(source_path)
        output_path.mkdir(parents=True, exist_ok=True)

        segments: list[CampaignLaunchSegment] = []
        channel_totals = Counter()
        warnings: list[str] = []
        for segment in ("HOT", "WARM", "COLD"):
            segment_rows = [row for row in rows if self._segment_for_row(row) == segment]
            email_rows = [row for row in segment_rows if self._has_value(row, "email")]
            sms_rows = [row for row in segment_rows if self._has_value(row, "phone")]
            direct_mail_rows = [row for row in segment_rows if self._direct_mail_ready(row)]
            exports = [
                self._write_export(output_path, segment=segment, channel="email", rows=email_rows),
                self._write_export(output_path, segment=segment, channel="sms", rows=sms_rows),
                self._write_export(output_path, segment=segment, channel="direct_mail", rows=direct_mail_rows),
            ]
            for export in exports:
                channel_totals[export.channel] += export.record_count
            if segment_rows and not email_rows:
                warnings.append(f"{segment} has no email-ready rows in the current artifact; enrich before Instantly enrollment.")
            if segment_rows and not sms_rows:
                warnings.append(f"{segment} has no SMS-ready rows in the current artifact; do not TextGrid-blast until phone confidence exists.")
            segments.append(
                CampaignLaunchSegment(
                    segment=segment,
                    source_count=len(segment_rows),
                    email_ready_count=len(email_rows),
                    sms_ready_count=len(sms_rows),
                    direct_mail_ready_count=len(direct_mail_rows),
                    recommended_daily_cap=self._daily_cap_for_segment(segment),
                    exports=exports,
                )
            )

        manifest_path = output_path / "manifest.json"
        manifest_path.write_text(
            self._manifest_json(
                campaign_slug=HARRIS_PROBATE_CAMPAIGN_SLUG,
                source_directory=str(source_path),
                output_directory=str(output_path),
                total_lead_count=len(rows),
                segments=segments,
                channel_totals=dict(channel_totals),
                warnings=warnings,
            ),
            encoding="utf-8",
        )
        return CampaignLaunchPreview(
            campaign_slug=HARRIS_PROBATE_CAMPAIGN_SLUG,
            source_directory=str(source_path),
            output_directory=str(output_path),
            total_lead_count=len(rows),
            segments=segments,
            channel_totals=dict(channel_totals),
            warnings=warnings,
        )

    def request_harris_probate_launch_approval(
        self,
        *,
        business_id: str,
        environment: str,
        actor_id: str,
        source_directory: Path | str = DEFAULT_HARRIS_PROBATE_SOURCE_DIR,
        output_directory: Path | str = DEFAULT_HARRIS_PROBATE_EXPORT_DIR,
    ) -> CampaignLaunchApproval:
        preview = self.build_harris_probate_preview(source_directory=source_directory, output_directory=output_directory)
        payload_snapshot = {
            "campaign_slug": preview.campaign_slug,
            "source_directory": preview.source_directory,
            "output_directory": preview.output_directory,
            "total_lead_count": preview.total_lead_count,
            "segments": [self._segment_dict(segment) for segment in preview.segments],
            "channel_totals": preview.channel_totals,
            "warnings": preview.warnings,
            "approval_scope": "exports_and_provider_enrollment_gate",
            "live_send_policy": "approval_required_before_any_instantly_textgrid_or_direct_mail_vendor_enrollment",
            "requested_by": actor_id,
        }
        command = self.commands_repository.create(
            business_id=business_id,
            environment=environment,
            command_type=HARRIS_PROBATE_COMMAND_TYPE,
            idempotency_key=f"{HARRIS_PROBATE_COMMAND_TYPE}:{preview.campaign_slug}:{business_id}:{environment}",
            payload=payload_snapshot,
            policy=CommandPolicy.APPROVAL_REQUIRED,
            status=CommandStatus.ACCEPTED,
        )
        approval: ApprovalRecord = self.approval_service.create_approval(command, payload_snapshot=payload_snapshot)
        return CampaignLaunchApproval(
            campaign_slug=preview.campaign_slug,
            command_id=command.id,
            approval_id=approval.id,
            approval_status=approval.status.value,
            payload_snapshot=approval.payload_snapshot,
        )

    @staticmethod
    def _read_source_rows(source_path: Path) -> list[dict[str, str]]:
        source_file = source_path / "hot_warm_ranked_enriched.csv"
        if not source_file.exists():
            raise FileNotFoundError(f"missing campaign source artifact: {source_file}")
        with source_file.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    @staticmethod
    def _segment_for_row(row: dict[str, str]) -> str:
        tier = (row.get("priority_tier") or "").strip().upper()
        if tier == "HOT":
            return "HOT"
        if tier == "WARM":
            return "WARM"
        return "COLD"

    @staticmethod
    def _has_value(row: dict[str, str], field: str) -> bool:
        return bool((row.get(field) or "").strip())

    @classmethod
    def _direct_mail_ready(cls, row: dict[str, str]) -> bool:
        return any(
            cls._has_value(row, field)
            for field in ("mailing_address", "hcad_site_address", "property_address", "style", "decedent_name")
        )

    @staticmethod
    def _daily_cap_for_segment(segment: str) -> int:
        return {"HOT": 15, "WARM": 30, "COLD": 50}[segment]

    @classmethod
    def _write_export(cls, output_path: Path, *, segment: str, channel: str, rows: list[dict[str, str]]) -> CampaignLaunchExport:
        export_path = output_path / f"{segment.lower()}-{channel}.csv"
        fieldnames = cls._fieldnames_for_channel(channel)
        with export_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(cls._export_row(row, segment=segment, channel=channel))
        return CampaignLaunchExport(channel=channel, segment=segment, path=str(export_path), record_count=len(rows))

    @staticmethod
    def _fieldnames_for_channel(channel: str) -> list[str]:
        common = ["segment", "case_number", "priority_score", "decedent_name", "campaign_slug", "do_not_send_before_approval"]
        if channel == "email":
            return common + ["email", "first_name", "last_name", "subject_context"]
        if channel == "sms":
            return common + ["phone", "first_name", "message_context"]
        return common + ["recipient_name", "mailing_address", "property_address", "letter_template"]

    @staticmethod
    def _export_row(row: dict[str, str], *, segment: str, channel: str) -> dict[str, str]:
        common = {
            "segment": segment,
            "case_number": row.get("case_number", ""),
            "priority_score": row.get("priority_score", ""),
            "decedent_name": row.get("decedent_name", ""),
            "campaign_slug": HARRIS_PROBATE_CAMPAIGN_SLUG,
            "do_not_send_before_approval": "true",
        }
        if channel == "email":
            return {
                **common,
                "email": row.get("email", ""),
                "first_name": row.get("first_name", ""),
                "last_name": row.get("last_name", ""),
                "subject_context": row.get("priority_flags", ""),
            }
        if channel == "sms":
            return {
                **common,
                "phone": row.get("phone", ""),
                "first_name": row.get("first_name", ""),
                "message_context": row.get("priority_flags", ""),
            }
        return {
            **common,
            "recipient_name": row.get("recipient_name", "") or row.get("decedent_name", ""),
            "mailing_address": row.get("mailing_address", "") or row.get("hcad_site_address", ""),
            "property_address": row.get("property_address", "") or row.get("hcad_site_address", ""),
            "letter_template": f"harris_probate_{segment.lower()}_letter",
        }

    @staticmethod
    def _segment_dict(segment: CampaignLaunchSegment) -> dict[str, Any]:
        return {
            "segment": segment.segment,
            "source_count": segment.source_count,
            "email_ready_count": segment.email_ready_count,
            "sms_ready_count": segment.sms_ready_count,
            "direct_mail_ready_count": segment.direct_mail_ready_count,
            "recommended_daily_cap": segment.recommended_daily_cap,
            "exports": [
                {
                    "channel": export.channel,
                    "segment": export.segment,
                    "path": export.path,
                    "record_count": export.record_count,
                }
                for export in segment.exports
            ],
        }

    @classmethod
    def _manifest_json(
        cls,
        *,
        campaign_slug: str,
        source_directory: str,
        output_directory: str,
        total_lead_count: int,
        segments: list[CampaignLaunchSegment],
        channel_totals: dict[str, int],
        warnings: list[str],
    ) -> str:
        import json

        return json.dumps(
            {
                "campaign_slug": campaign_slug,
                "source_directory": source_directory,
                "output_directory": output_directory,
                "total_lead_count": total_lead_count,
                "segments": [cls._segment_dict(segment) for segment in segments],
                "channel_totals": channel_totals,
                "warnings": warnings,
            },
            indent=2,
            sort_keys=True,
        ) + "\n"


campaign_launch_service = CampaignLaunchService()
