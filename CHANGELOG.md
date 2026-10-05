# Changelog

## Unreleased — 2026-09-30

- Correct CLI troubleshooting for TestHub team discovery, encoded artifact
  IDs, resource versus route 404s, replay prerequisites, and ambiguous creates.

- Put the QyrusAI PNG and public-repository setup prompt first in the README.
  Document initial loading of the bundled setup skill before host discovery,
  personal marketplace registration, and public-root development commands.
- Explain that the Qyrion release mirror copies the README and logo with the
  complete plugin; feature-branch pushes alone do not publish these updates.

## Unreleased — 2026-09-29

- Make plain “Set up QyrusAI Assure” requests own Python/uv/Qyrion dependency
  preparation, shared-file reuse, SDK configuration, and read-only checks.
  Replace manual prerequisite/upgrade handoffs with a bundled agent runbook;
  preserve working tools and explicit overrides. No new installer script or
  plugin-install hook: the setup skill orchestrates trusted installers and
  the existing credential helper when invoked.
- Prefer verified public Qyrion release binaries over a private npm fallback
  on supported platforms; source-only installations still require repo access.
- Add routing acceptance cases for plain setup, missing tools, obsolete CLI,
  missing access, and narrow MCP-only setup. These are manual acceptance cases,
  not a claim of testing fresh installations on every operating system.

## 0.3.0 — 2026-09-29

- Name the plugin QyrusAI Assure and bundle the supplied QyrusAI logo for
  the Codex plugin listing, composer, and README. Preserve the existing
  `qyrion-agent-plugin` installation identifier.
- Correct setup to discover teams through MCP `qyrus_teams_get_by_api_key`
  after the guide. Remove mandatory gateway `qyrion auth teams` probes from
  the skills; preserve exact team UUIDs and verify Qyrion authorization
  separately through read-only session discovery. Live MCP lookup succeeded
  with the configured key while the separate gateway route returned 401.
- Add Qyrus Aegis MCP via a pinned local stdio-to-HTTPS bridge, with a shared
  Codex/Claude launch configuration and no packaged credentials.
- Add one private-file credential loader for MCP, Qyrion, and qyrusai. Infer
  `<env_name>-mcp.qyrus.com/mcp` from the Qyrus URL and write it to the user's
  file; keep `app` as `app-mcp`. Persist only the file path in user settings.
- Automatically prepare qyrusai 1.0.9 during setup; the SDK runner installs
  it if missing and reuses the isolated uv environment.
- Add setup, guide-first MCP, public SDK, web testing/export, and value-loop
  skills. Include all 18 supplied loop recipes with explicit capability and
  evidence requirements, plus an open-ended composition contract.
- Refresh Qyrion auth guidance (no required legacy gateway token) and web
  session commands. Preserve the existing installation identity and mobile skills.
- Add offline setup and real stdio/HTTP protocol coverage using fake credentials.
  Live Qyrus and desktop host acceptance are not claimed by these tests.
- Source conflict resolved: the old plugin claimed mobile-only/CLI-only and
  three required credentials; current Qyrion implementation supports web and
  API-key headers. This describes the client, not acceptance by every gateway
  route. The previously claimed repo marketplace is absent.
