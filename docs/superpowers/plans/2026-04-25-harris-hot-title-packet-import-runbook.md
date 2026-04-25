# Harris HOT Title Packet Import Runbook

Ares tracks Hermes-built curative-title packets through the canonical lead store first, then richer title-packet tables later.

## Current no-wire slice

This slice adds a Mission Control import endpoint and service for `ares.lead_import.v1` payloads:

```text
POST /mission-control/lead-machine/title-packets/import
```

The endpoint upserts by `LeadRecord.identity_key()`, so HOT packet imports are idempotent when `external_key` stays stable:

```text
external_key = harris-hot18:{hctax_account}
dedupe key = external:{external_key}
```

## HOT 18 local artifacts

The active Hermes run produced local artifacts outside the repo because they contain live lead/operator data:

```text
/root/.hermes/output/harris_tax_verify/HOT_18_title_packets_enriched.xlsx
/root/.hermes/output/harris_tax_verify/HOT_18_title_packet_report.md
/root/.hermes/output/harris_tax_verify/HOT_18_operator_queue.csv
/root/.hermes/output/harris_tax_verify/HOT_18_operator_queue.md
/root/.hermes/output/harris_tax_verify/HOT_18_probate_case_addendum.md
/root/.hermes/output/harris_tax_verify/HOT_18_ares_import.json
```

Do **not** commit those lead artifacts to the public repo unless Martin explicitly decides the data exposure is acceptable. The repo keeps the importer and runbook; the lead packet evidence stays local/runtime-owned.

## Import payload shape

Minimum record fields:

```json
{
  "schema": "ares.lead_import.v1",
  "source": "hermes.harris_hot18_title_packet_run",
  "import_mode": "upsert_by_external_key",
  "records": [
    {
      "business_id": "limitless",
      "environment": "dev",
      "source": "manual",
      "lifecycle_status": "ready",
      "external_key": "harris-hot18:0611340530007",
      "company_name": "PLUMMER LETITIA W ESTATE OF",
      "mailing_address": "3324 S MACGREGOR WAY HOUSTON TX 77021-1107",
      "property_address": "3324 S MACGREGOR WAY 77021",
      "probate_case_number": "500741",
      "score": 93,
      "verification_status": "operator_packet_built",
      "enrichment_status": "hcad_tax_clerk_probate_enriched",
      "upload_method": "hermes_hot18_packet_import",
      "personalization": {
        "operator_lane": "A — probate-first estate lead",
        "why_now": "estate owner on tax roll; 1 probate hit(s); low debt-to-value"
      },
      "custom_variables": {
        "hctax_account": "0611340530007",
        "tax_due": 63829.57,
        "delinquent_years": "2022,2023,2024,2025",
        "manual_pull_queue": "Probate case 500741: pull application/order docs"
      },
      "raw_payload": {
        "source_row": {}
      }
    }
  ]
}
```

## Field mapping

- `LeadRecord.external_key`: stable import key, usually `harris-hot18:{hctax_account}`.
- `LeadRecord.company_name`: tax-roll owner / estate name.
- `LeadRecord.property_address`: subject property.
- `LeadRecord.mailing_address`: first contact address from packet.
- `LeadRecord.probate_case_number`: first exact-ish probate case when present.
- `LeadRecord.score`: HOT/WARM lead score.
- `LeadRecord.personalization`: operator-facing lane/posture/why-now text.
- `LeadRecord.custom_variables`: tax debt, years, HCAD account, document-pull queue, value metrics.
- `LeadRecord.raw_payload`: full packet source row and artifact pointers.

## Runtime boundary

This is intentionally in-memory/no-wire for the current branch. Live Supabase persistence remains deferred. When live wiring is enabled, the same import service should write through `LeadsRepository` into the configured control-plane backend.

## Next durable model

The next slice should split `raw_payload` into first-class records:

```text
Lead
  ├── PropertySnapshot
  ├── TaxDelinquencySnapshot
  ├── ProbateCaseSnapshot
  ├── ClerkInstrumentSnapshot
  ├── TitlePacket
  └── OperatorTask
```

Until then, Ares can still track the lead queue, owner/address, tax/probate summary, operator lane, and manual pull queue through the canonical lead record.
