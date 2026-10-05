# Changelog

## Unreleased — 2026-09-30

- Distinguish updated TestHub team discovery from older direct gateway
  binaries; retain MCP-first plugin setup and separate service checks.

## Unreleased — 2026-09-29

- Embed the agent-owned dependency setup runbook; plain setup handles
  missing tools and reuses the selected private file. Replace shared
  CLI install/upgrade handoffs with verified installation and one recheck.

## 0.3.0 — 2026-09-29

- Route shared team setup through MCP `qyrus_teams_get_by_api_key`; preserve
  exact team UUIDs and check Qyrion scope separately instead of requiring the
  gateway team-list probe.
- Added or refreshed this skill for the expanded Qyrus agent plugin.
- Shared credentials use one private X-API-Key file and tenant-derived MCP
  endpoint. MCP team discovery needs no separate Authorization token.
- See the plugin CHANGELOG for source conflicts and validation boundaries.
