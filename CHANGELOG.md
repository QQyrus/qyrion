## 2026-11-11 — Existing report sharing

- Route report-resend requests to email-report/email-status instead of rerunning. Update canonical CLI/session guidance and generated skill copies. Requires matching deployed gateway aliases.

# Changelog

## Unreleased — 2026-11-05 (unknown @NAME becomes a choice)

- `shared/cli-contract.md` ("Confirming one @NAME as literal data") and `shared/test-data-workflows.md`
  ("An @NAME with no test data") replace "a reference without a selected project must be corrected before
  provisioning" with the AS-1436 decision path: the structured `unresolved_references` rejection and its
  occurrences, repeatable `--literal-reference NAME` on `run` / `sessions create` / `sessions send`, the
  interactive single question versus exit 2 with the occurrences in `--json`/`--jsonl`, `literal_references`
  on local and hosted MCP, and repeated `--literal-reference` on the retained TUI's `/run` and `/send`.
- States the two rules an agent must not break: never confirm a literal on the person's behalf or retry a
  rejection hoping it passes, and never substitute a secret value on the command line, in shell history or in
  machine output — literal is not public text, and a confirmed `@pass1` is still protected. Regenerated the
  embedded copies in all nine skills; host manifest versions remain release-workflow owned.

## Unreleased — 0.4.0 report email

- Document optional fresh-run email, saved-test rerun inheritance, explicit replacement and suppression, MCP arrays and retained TUI pending recipients in the shared CLI guide and generated skill copies.
- Describe 48-hour PDF/HTML download links, recipient privacy and backend rollout order. Host manifest versions remain stamped by the release mirror.

## Unreleased — 2026-11-03

- Document the caller-requested initial-objective credential-pattern bypass, plaintext handling, and backend rollout order. Regenerate embedded CLI contracts; host manifest versions remain release-workflow owned.
## Unreleased — 2026-11-02 (act on a parked session)

- `shared/session-workflows.md` (and the embedded copies) adds "Act on a parked session": read
  `sessions question --json` and act on `waiting_for` (`answer`, `next_instruction` with `last_message`,
  `replay_input`); a live run's next step goes to the same run with `sessions send`. `shared/cli-contract.md`:
  `sessions result --wait` also returns on a park, at once when the run is already parked.
  `answer-qyrion-agent-questions` names the `waiting_for` field. Why: an Assure Box thread waited out a desktop
  run's park after its instruction and cancelled it (`cnv_73a6c7ece6984fa1`, 2026-11-02, desktop-agent plan 26).

## Unreleased — 2026-11-02 (end a done live session with `finish`)

- `shared/session-workflows.md` (and the embedded copies) adds "End a live session": a live session whose work is
  done and read ends with `qyrion sessions finish <run_id> --json` (MCP `qyrion_finish_session`) and reads COMPLETED;
  `sessions cancel` is for abandoning one. Why: a thread had only `cancel` for a finished live desktop run, so
  History read CANCELLED (`cnv_73a6c7ece6984fa1`, 2026-11-02; plan 26 lane 26b).

## Unreleased — 2026-10-29 (directory listing metadata)

- Shorten the Codex listing subtitle to 29 characters and add the public Qyrus website, support, privacy policy, and terms URLs required by directory review. The command MCP launcher remains unchanged; its submission requires OpenAI desktop-only approval or a supported remote authentication integration.

## Unreleased — 2026-10-22 (one wait over several sessions)

- `shared/cli-contract.md` (and the embedded copies) adds "Several sessions at once": with the new
  `session_wait_any` feature, watch every session you started with one
  `qyrion sessions wait --any <run_id> <run_id> ... --timeout 240 --json`, handle the session that woke it
  (`question`, `finished`, `failed_to_start` or `timeout`), then wait again on `watch_next`. `shared/parallel-orchestration.md`
  monitors all active run ids with that one wait (bounded streams or result polls without the feature). `qyrion-cli`
  says the same. Why: an Assure Box thread waiting on one session at a time left another session's question unseen
  (`cnv_444d7ec7038a4d21`, 2026-10-22). `tests/test_session_wait_docs.py` checks the skill, the contract and that every
  skill's embedded copy matches `shared/`.

## Unreleased — 2026-10-22 (compact session output)

- `shared/cli-contract.md` (and the embedded copies) adds "Read compact, not whole": waits use
  `qyrion sessions result <run_id> --wait --timeout 240 --json --compact` and steps are read with
  `qyrion sessions steps <run_id> --json --compact --limit 500` (or `--fields a,b,c`), gated on the new
  `compact_session_output` feature. Plain `--json` repeats artifact paths, hashes, screenshots, raw input/output and
  locator chains: a 500-step page was about 555 KB and filled an Assure Box thread's context until its next model call
  failed (`cnv_444d7ec7038a4d21`, 2026-10-22). Compact keeps `run.status`, `run.step_count`, the newest
  `run.recent_events` entry, `run.pending_question`, the summary/verdict and `next_cursor`.
- `shared/test-preservation.md` says preservation reads the full rows a page at a time, not `--compact`.
  `qyrion-cli`, `qyrus-web-testing` and `qyrus-device-testing` use the compact forms for waiting and reporting; the
  Aegis save step keeps the full `--locators` read.

## Unreleased — 2026-10-22 (Qyrus detail lives in the skills)

- The Assure Box runtime now carries only general asking rules (scopes, kinds, paging for any connector), and the
  Qyrus and Qyrion detail lives here, where its threads read it (owner decision, lane Q2). `shared/execution-routing.md`
  (and the embedded copies) adds the team rule beside the product table: teams come from `qyrus_teams_get_by_api_key`, a
  named or single team needs no question, several are asked about with names as choices and one recommended, never by
  reading every team's lists; "save to Web Testing" names the Aegis destination when a run is saved.
  `shared/credentials.md`, "Team discovery through MCP", says the same.
- `qyrus-mcp` states the Web Testing meaning and the product question in `SKILL.md` itself, and the team rule next to
  team discovery; `qyrion-cli` and `qyrus-web-testing` say at their save step that "save it to my Web Testing" is a Web
  Testing script through the MCP, never a Qyrion project named "Web Testing".

## Unreleased — 2026-10-22 (product names and paging)

- `shared/execution-routing.md` (and the embedded copies) names the Qyrus products and what serves each: Web Testing, API
  Testing, Orchestration and TDM through the Aegis MCP, Mobility and website sessions through Qyrion, a saved Qyrion test
  through `qyrion sessions save-test`. "Save it to my Web Testing" means a Web Testing script in one of the person's teams,
  never a Qyrion project named "Web Testing" (conversation `cnv_ddda46daa9034751`, 2026-10-22). Ask which product when
  "projects" could be either, and which team when several fit, with choices and one recommended where the host can.
- `qyrus-mcp` pages a list with one `size` until a page returns fewer items, and treats a list heading such as
  "Projects (108)" as the total, never as a page count to compare across sizes.

## Unreleased — 2026-10-22 (evidence in work items)

- `shared/safety-policy.md` (and the embedded copies) says what goes into a
  work item, page or check: findings, evidence and durable links only, never the
  agent's own tool limits, how it worked or ids the reader cannot open; those go
  to the user in chat. It points to the connector's discovery tool before
  concluding an operation (such as attaching a file) is missing, to
  `qyrion sessions artifacts` / `sessions download` for screenshots (there is no
  `qyrion artifacts`), and to posting the run link when an upload fails.

## Unreleased — 2026-10-22 (long sessions)

- `shared/cli-contract.md` (and the embedded copies) tells hosts that limit one
  command to start long sessions with `qyrion sessions create ... --json` and
  observe them with `sessions result --wait --timeout 240` loops instead of
  holding a command with `qyrion run`; a wait that ran out is not a failure, and
  a `run` that the host ended after printing its run ID leaves a running session.
  `qyrion-cli` recommends `--timeout 240` for waits.

## Unreleased — 2026-10-22 (waiting for a session)

- `qyrion sessions result --wait` without `--timeout` now waits 300 seconds
  (it returned at once, because `--timeout` defaulted to 0, which sent agents
  into polling `sessions steps`). The CLI contract documents the wait, the
  `run.status` check after it and the `sessions question` check between waits;
  scripts keep passing `--timeout` explicitly for older binaries.
- `qyrion-cli` lists exit `5` (`run` parked on an agent question) in its
  exit-code table and says how to continue after a killed `run` (exit `-9`):
  the session keeps running; take its `run_id` and wait with `result --wait`.
  The embedded `cli-contract.md` copies are regenerated.

## Unreleased — 2026-10-22

- The MCP bridge lists six Qyrus tools instead of 310 by default
  (`QYRUS_MCP_TOOLS=progressive`): the three core tools plus `qyrus_tools`,
  `qyrus_tool_schema` and `qyrus_tool_call` to find, read and call the rest.
  `QYRUS_MCP_PINNED_TOOLS` lists chosen tools directly; `QYRUS_MCP_TOOLS=all`
  keeps the full proxy. Both settings come from the private file or the host
  environment, and `qyrus_env.py check` validates them (`scripts/qyrus_mcp.py`,
  new `scripts/qyrus_catalogue.py`, `mcp_tool_settings` in `scripts/qyrus_env.py`).
- An argument mismatch names the failing path and the schema rule only
  (`amount: must be of type integer`), never the value that was given.
- Skills `qyrus-mcp`, `qyrus-setup`, `qyrus-web-testing`, `qyrus-change-impact`
  and `qyrus-value-loops` send the model through find, read, call for
  non-core tools; README, `docs/env.md` and `shared/credentials.md` document
  the switch.

## Unreleased — 2026-10-21

- The private file may name local session services (`QYRION_TESTHUB_URL`,
  `QYRION_RUNBRIDGE_URL`) for developers running testhub and runbridge on
  their computer; only `localhost` / `127.0.0.1` URLs are accepted, otherwise
  the tenant gateway is still used (`scripts/qyrus_env.py`, `local_service_url`).

## 0.3.9 — 2026-10-23

- Clarify browser pre-send consent versus CLI/MCP reference workflows, final value-free audit and encrypted Default capture. Regenerate all shared skill copies.

- Document Text/Secret variable kinds, explicit Secret-to-Text confirmation,
  typed dataset templates/exports, and the `variable_types` capability.
- Clarify that saved-test UI reruns select test-owned datasets while CLI/MCP/API
  retain project-variable sources and historical replay preserves its source.
- Clarify Secret defaults for new variables and kind preservation on edits.
- Regenerate distributed skill references. Refresh Qyrion and the plugin;
  this source update does not publish a release.

## 0.3.8 — 2026-10-22

- Document advisory/unverified JSONL outcomes, separate evidence counts and why
  completed/exit 0 does not establish a passed assertion. Regenerate skill copies.
- Correct legacy `--dataset` guidance: preserve saved-test JSON variables and
  distinguish the reference-based `--test-dataset` selection.

- Add capability-gated CLI and Qyrion MCP workflows for project references,
  variable management, automatic Default capture and test-owned datasets.
- Document metadata-only discovery, explicit file export, revision-aware edits,
  exact replacement confirmation and saved-source preferences.
- Regenerate embedded skill references. Refresh Qyrion and the plugin and
  reconnect MCP after installation; no release is published by this change.

## 0.3.7 — 2026-10-14

- Host manifest versions (Claude, Codex, Cursor) are stamped from the
  `qyrion/v<version>` release when the public mirror publishes; the
  committed manifests move to 0.3.7 as the baseline.

## CLI workflow guidance — 2026-10-09

- Document session names and aliases, paginated project/test discovery,
  platform-specific reruns, new run IDs and submission-versus-pass semantics.
- Distinguish Qyrion MCP from Aegis and backend creator attribution from
  target-app login credentials; check installed/deployed support before use.

## Unreleased — 2026-10-09

- Clarify authorized target-login handoff without blanket password refusal;
  exclude unrelated SDK Memory accounts and scope encryption claims to evidence.
- Require complete paginated execution export, source-to-saved-step mapping,
  and read-back; distinguish partial conversion from a verified runnable test.
- Resolve one project/module per work-item scope before parallel saves.

## Unreleased — 2026-10-07

- Make private-input test fixtures portable on Windows with explicit UTF-8,
  a native fake-CLI launcher, and POSIX-only permission assertions.

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
