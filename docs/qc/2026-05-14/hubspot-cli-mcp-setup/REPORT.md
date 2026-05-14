# HubSpot CLI + MCP Setup Report

## Scope
- Configured HubSpot CLI access for Ares using the operator-supplied HubSpot Personal Access Key (PAK).
- Added a local HubSpot CLI wrapper that safely reads `/opt/ares/Ares/.env` without shell-sourcing it.
- Configured HubSpot Developer MCP for Hermes native MCP startup.
- Verified the MCP server and docs fetch path without printing secrets.

## Files / local config changed
- `/root/.hermes/scripts/hubspot-cli-env.sh`
  - Wrapper for `hs` using `@hubspot/cli@8.6.0` through `npm exec`.
  - Reads `HUBSPOT_PERSONAL_KEY` from `/opt/ares/Ares/.env` and exports `HUBSPOT_PERSONAL_ACCESS_KEY`, `HUBSPOT_ACCOUNT_ID`, and `USE_ENVIRONMENT_HUBSPOT_CONFIG=true`.
- `/root/.hermes/scripts/hubspot-mcp-start.sh`
  - Starts `hs mcp start --ai-agent hermes` through the wrapper.
- `/root/.hermes/home/.hscli/config.yml`
  - HubSpot global CLI config for account `ares-limitless`.
  - Mode: `0600`.
  - Contains secrets; do not commit or print.
- `/root/.hermes/config.yaml`
  - Added native MCP server config:
    - server name: `hubspot`
    - command: `/root/.hermes/scripts/hubspot-mcp-start.sh`
    - timeout: `180`
    - connect_timeout: `120`

## Verification
- HubSpot CLI account list works with default account `ares-limitless`.
- HubSpot CLI read-only owners API call works.
- HubSpot Developer MCP server discovery works via mcporter.
- MCP advertised 21 tools, including:
  - `search-docs`
  - `fetch-doc`
  - `find-projects`
  - `validate-project`
  - `deploy-project`
  - `get-build-status`
  - `get-build-logs`
  - CMS module/template/function tools
- MCP `fetch-doc` successfully fetched HubSpot docs for:
  - `developer-tooling/local-development/mcp-server`
  - `developer-tooling/local-development/hubspot-cli/personal-access-key`

## Important notes
- HubSpot PAKs are not direct CRM bearer tokens. They are CLI/local-dev refresh keys.
- The CLI/MCP can refresh from the PAK via `~/.hscli/config.yml`.
- Ares app code still needs durable PAK-to-OAuth refresh support if it will use PAKs directly instead of a Private App token.
- Native Hermes MCP tools require a Hermes process restart before `mcp_hubspot_*` tools appear in future chats.

## Provider side effects
- Live HubSpot mutations: `0`.
- No properties, pipelines, contacts, deals, outreach, or provider writes were created.
