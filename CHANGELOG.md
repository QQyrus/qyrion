# Changelog

## 0.3.4 — 2026-10-06

- Make Qyrion the default executor for new web/mobile coverage; ask a plain
  new-versus-existing preference only when intent is ambiguous, and reuse
  known URLs and authorized target test-account details without a tool menu.
- Remove the unsupported server-side account-alias claim and document the
  actual objective input and session-history boundary.
- Add private input/output handling for credential-bearing objectives and
  history, including JSON echo filtering and temporary CLI-log cleanup.
- Allow independent web/mobile objectives to run concurrently through
  multiple CLI calls, with account/state dependency checks and owned cleanup.
- Add private, scoped result records beside the credentials file and optional
  host-memory pointers, without copying secrets or raw test transcripts.
- Add cached four-hour public-release checks, quiet unchanged/declined state,
  user-accepted upgrades, and verified installation timestamps.
- Retain the offered release/asset across newer discovery results so a
  verified user-selected installation can still be recorded correctly.
- Bump Codex, Claude, and Cursor package manifests to 0.3.4 and verify new
  helpers and distributed references in the public mirror package gate.

## 0.3.3 — 2026-10-05

- Add Antigravity's root plugin manifest and setup instructions for 2.0,
  the standalone IDE, and CLI, reusing all nine existing skills.
- Add credential-free MCP registration with absolute installed paths,
  atomic JSON merging, conflict detection, and preserved connector settings.
- Document separate work-tracker authentication and native host verification;
  local packaging is independent of Google marketplace publication.
- Bump Codex, Claude, and Cursor manifests to 0.3.3. Antigravity's documented
  minimal manifest has no version field.

## 0.3.2 — 2026-10-05

- Add a single HTML landing page with QyrusAI branding, Qyrus light/dark
  themes, agent-owned setup, private credentials guidance, example tasks,
  and a redacted API-key tutorial video with written instructions. It also
  presents the value-loop stages, the seven assurance loop recipes, and the
  nine bundled skills, with scroll and hover motion that turns off for
  reduced-motion readers.
- Package the page and media with the public plugin. The release mirror
  configures GitHub Pages and verifies the mirrored commit and served HTML.
- Bump all host manifests to 0.3.2 for the new package content.

## 0.3.1 — 2026-10-05

- Document the confirmed 0.3.4-beta Windows Rich JSON encoding failure and
  the separate CLI fix. Require parseable output as well as exit status;
  preserve credentials and distinguish plugin refresh from binary upgrade.
- Replace Windows CRT `exec*e` launches with a shared waiting subprocess for
  the CLI/SDK wrapper and MCP bootstrap; preserve stdio, executable overrides
  and exit status, including native Windows failure codes. POSIX keeps exec.
  Add process-boundary regressions and a native Windows release-test gate.
  The later supplied traceback identifies a separate CLI encoding error;
  it does not confirm the earlier reported native access violation. Native
  Windows validation and the affected user's read-only retry remain pending.
- Select the newest published public CLI release including betas, using the
  release list rather than GitHub's stable-only `/releases/latest`. Setup
  downloads only the platform binary/archive without checksum or signature
  checks; Windows instructions cover `qyrion.exe`, user PATH and capability
  verification. Binary timeouts are reported separately from release discovery.
- Bundle the `qyrusai-assure` Claude marketplace with plugin source `./`,
  portable from the development package to the public repository root.
- Document persistent Claude installation, updates, safe handling of local
  symlinks and existing personal registrations, and host activation status.
  Setup completes its checks in the original request without a second setup
  prompt or ad hoc project marketplace/Git-exclude changes.
- Bump all host manifests to 0.3.1 so cached plugin updates are discoverable;
  preserve working user-selected CLI installations.
- Rename the install ID to `qyrusai-assure` in all host manifests and the
  Claude catalog. Add the Claude rename map and document migration for old
  personal registrations; keep the source directory and release mirror path.
- Verified with Claude Code 2.1.289: strict manifest validation, isolated
  local installation through a resolved symlink, and cached Git installation
  from a temporary local repository. Claude reports all nine skills and one
  `qyrus` MCP definition. Authenticated Qyrus calls and interactive session
  reload were not repeated for this packaging change.

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
