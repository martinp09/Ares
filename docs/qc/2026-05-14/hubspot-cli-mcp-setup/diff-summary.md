# Diff Summary: HubSpot CLI + MCP Setup

## Local Hermes files
- `/root/.hermes/scripts/hubspot-cli-env.sh`
  - New safe wrapper for HubSpot CLI with Ares HubSpot PAK env mapping.
- `/root/.hermes/scripts/hubspot-mcp-start.sh`
  - New stdio MCP start wrapper for HubSpot Developer MCP.
- `/root/.hermes/config.yaml`
  - Added `mcp_servers.hubspot` pointing at the MCP start wrapper.
- `/root/.hermes/home/.hscli/config.yml`
  - Created HubSpot CLI global config for `ares-limitless`; contains secrets and is mode `0600`.

## Ares QC artifacts
- `docs/qc/2026-05-14/hubspot-cli-mcp-setup/REPORT.md`
- `docs/qc/2026-05-14/hubspot-cli-mcp-setup/test-output.txt`
- `docs/qc/2026-05-14/hubspot-cli-mcp-setup/diff-summary.md`

## Skill maintenance
- Patched `ares-engineering-discipline` HubSpot reference to clarify that HubSpot PAKs are refresh/local-dev keys, not direct CRM bearer tokens.

## Provider side effects
- Live HubSpot mutations: `0`.
