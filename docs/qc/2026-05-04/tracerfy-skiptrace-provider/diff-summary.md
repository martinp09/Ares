# Diff Summary

## git diff --stat
```
 .env.example                            |   2 +
 CONTEXT.md                              |  20 ++++---
 TODO.md                                 |  12 ++--
 app/api/mission_control.py              |  23 +++++++
 app/core/config.py                      |   8 +++
 app/db/automation_runs.py               |   4 +-
 app/db/campaign_memberships.py          |   4 +-
 app/db/campaigns.py                     |   4 +-
 app/db/contacts.py                      |   4 +-
 app/db/crm_records.py                   |  10 +++-
 app/db/lead_events.py                   |   4 +-
 app/db/leads.py                         |   4 +-
 app/db/opportunities.py                 |   4 +-
 app/db/suppression.py                   |   4 +-
 app/models/mission_control.py           |  27 +++++++++
 app/providers/instantly.py              |  18 ++++++
 app/services/_control_plane_runtime.py  |   5 +-
 app/services/agent_registry_service.py  |   8 ++-
 app/services/mission_control_service.py |  55 +++++++++++++++++
 docs/curative-title-wiki/index.md       | 102 ++------------------------------
 memory.md                               |  69 +++++++++++++++++----
 tests/conftest.py                       |  18 ++++++
 tests/providers/test_instantly.py       |  26 ++++++++
 23 files changed, 296 insertions(+), 139 deletions(-)
```

## Changed/untracked files before commit

- ` M .env.example`
- ` M CONTEXT.md`
- ` M TODO.md`
- ` M app/api/mission_control.py`
- ` M app/core/config.py`
- ` M app/db/automation_runs.py`
- ` M app/db/campaign_memberships.py`
- ` M app/db/campaigns.py`
- ` M app/db/contacts.py`
- ` M app/db/crm_records.py`
- ` M app/db/lead_events.py`
- ` M app/db/leads.py`
- ` M app/db/opportunities.py`
- ` M app/db/suppression.py`
- ` M app/models/mission_control.py`
- ` M app/providers/instantly.py`
- ` M app/services/_control_plane_runtime.py`
- ` M app/services/agent_registry_service.py`
- ` M app/services/mission_control_service.py`
- ` M docs/curative-title-wiki/index.md`
- ` M memory.md`
- ` M tests/conftest.py`
- ` M tests/providers/test_instantly.py`
- `?? .env.before-docker-normalize`
- `?? .env.before-instantly-real-account-20260503T215318Z`
- `?? .env.before-supabase-backend-20260429T023141Z`
- `?? Dockerfile.api`
- `?? Dockerfile.ui`
- `?? app/providers/tracerfy.py`
- `?? app/services/skiptrace_service.py`
- `?? deploy/`
- `?? docs/curative-title-wiki/bankruptcy-records-deal-source.md`
- `?? docs/integrations/`
- `?? docs/lead-scoring/`
- `?? docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-create-payloads-2026-05-02.json`
- `?? docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-nurture-subsequence-create-payloads-2026-05-02.json`
- `?? docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-nurture-subsequence-readback-2026-05-02.json`
- `?? docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-nurture-subsequence-upload-results-2026-05-02.json`
- `?? docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-readback-2026-05-02.json`
- `?? docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-upload-results-2026-05-02.json`
- `?? docs/qc/2026-05-02/instantly-campaign-draft-upload/`
- `?? docs/qc/2026-05-02/instantly-campaign-nurture-upload/`
- `?? docs/qc/2026-05-02/instantly-client-fingerprint-patch/`
- `?? docs/qc/2026-05-03/`
- `?? docs/qc/2026-05-04/`
- `?? tests/providers/test_tracerfy.py`
- `?? tests/services/test_skiptrace_service.py`
