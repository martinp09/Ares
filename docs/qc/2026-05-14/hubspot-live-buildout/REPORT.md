# HubSpot Live Buildout QC

## Scope

Built the HubSpot portal side for the Ares operating spine after operator instruction.

This live buildout applied only HubSpot CRM customization:

- `ares_information` property group on contacts, companies, and deals
- 12 Ares contact properties
- 20 Ares deal properties
- 4 Ares company properties
- Ares acquisition stages inside the existing deal pipeline

## Live-side-effect posture

- Live HubSpot portal mutations: **yes**
- HubSpot records synced: **no**
- Instantly enrollments/sends: **no**
- Vapi calls: **no**
- County/source-provider pulls: **no**
- Slack/provider sends: **no**

## What happened

1. Read-only HubSpot probe passed for owners, properties, and deal pipelines.
2. First live customization apply attempted to create a new `Ares Acquisitions` deal pipeline.
3. HubSpot returned `400 API_LIMIT`: the portal has a maximum of one deal pipeline.
4. The code was hardened to reuse the existing single deal pipeline when the portal cannot create another pipeline.
5. Re-running live customization succeeded:
   - property groups created/skipped to final complete state
   - all Ares properties present
   - existing `Sales Pipeline` reused
   - 11 missing Ares stages created
   - `Closed Won` skipped because it already existed

## Result

HubSpot itself is now built out for the Ares CRM mirror surface.

Final verification confirmed:

- contacts Ares properties: `12/12`
- deals Ares properties: `20/20`
- companies Ares properties: `4/4`
- Ares deal stages present: `12/12`
- deal pipeline count: `1`
- reused pipeline: `Sales Pipeline` / `default`
- default next live record-sync seed stage: `New Lead` / `3668226794`

## Safety notes

- Token values were not printed.
- Local env gates were enabled only for the one HubSpot customization apply process.
- Because the portal is limited to one deal pipeline, Ares stages live in the existing `Sales Pipeline` rather than a separate `Ares Acquisitions` pipeline.
- Record sync should use the real pipeline ID `default` and the captured HubSpot stage IDs/labels before any live record write.

## Verification summary

- Focused HubSpot tests after code hardening: `44 passed`.
- Live HubSpot customization apply: succeeded.
- Read-only post-apply verification: succeeded.
- Full backend/frontend/Trigger verification should be rerun before committing because this slice changed staged code after the previous final readiness run.
