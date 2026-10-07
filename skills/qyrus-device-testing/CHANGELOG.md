# Changelog

## 0.3.4 — 2026-10-06

- Use the private execution wrapper for credential-bearing inputs and history,
  filtering CLI echoes and isolating temporary logs.

- Default objective-driven web/mobile execution to Qyrion, preserve new-test
  versus existing-test intent, and reuse known ticket/login context.
- Support independent concurrent CLI sessions without requiring subagents;
  check account/state dependencies and clean up every owned session.
- Correct the unsupported account-alias claim; apply host policies and safe
  handling of authorized target test credentials, distinct from Qyrus keys.
- Route reusable scoped metadata and accepted CLI updates through the shared
  local-state and update-check references.

## 0.3.1 — 2026-10-05

- Document the Windows Rich JSON encoding failure and the required CLI fix;
  a traceback with exit 0 is not successful setup or proof of bad credentials.
- Use the shared Windows subprocess launcher for credential-wrapped CLI/SDK
  commands and MCP; distinguish native launch crashes from auth failures
  and resolve helper paths from the installed plugin.
- Refresh the shared setup runbook: choose the newest published CLI release
  including betas, download only the platform binary without checksum
  checks, and handle Windows installation and download timeouts explicitly.

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
