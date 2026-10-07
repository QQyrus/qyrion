# Choose the testing workflow

Scope: QyrusAI Assure tasks on every host. Apply this before opening a browser,
searching a test inventory, or starting a run. The user's explicit choice and
host policies take precedence. Users need to describe the outcome, not know
which Qyrus tool implements it.

## Resolve intent with the context already available

| User intent | Route |
|---|---|
| Test, explore, or reproduce behavior on a website from an objective/ticket | Qyrion web session: `--platform web --start-url <target-url>` |
| Test, explore, or reproduce behavior on a mobile app | Qyrion mobile session with the selected device/build |
| Create new web/mobile coverage, run and save a test, or explicitly use an agent | New Qyrion objective, inspect evidence, then save within the requested scope |
| Find, reuse, update, or rerun an existing test/suite; a supplied test ID | Discover/read the matching saved asset through Qyrion or MCP, then the requested operation |
| Create API tests or explicitly author Qyrus automation steps without exploration | MCP or SDK as appropriate, using the live guide and schemas |
| Explicit Playwright/CUA/local-browser request | Honor that choice and host policies; do not substitute Qyrion |
| Generate test ideas only, review read-only, or write unit tests | No cloud execution or saved-test mutation unless requested |

A generic bounded request such as "test the login flow on this website" is
an objective, so run it with Qyrion. Do not ask the user to select a browser
tool. If the requested saved-test work genuinely leaves **new coverage vs
reuse** unclear, and no applicable preference is known, ask once:
**"Create and save a new test, or look for an existing test to run?"**
Use the answer for this scope. Explicit new-test intent needs no such question.
A remembered preference is a hint; the current request overrides it.

The host's Playwright, CUA, browser tab, or local login is not the default
execution surface. Never silently substitute one when Qyrion is unavailable.
Report the concrete blocker and prepare the objective; a different execution
surface requires the user's choice. Reading connectors or viewing downloaded
Qyrion artifacts is still useful and does not change the execution surface.

## Reuse facts, not assumptions

Read the requested ticket once and use its target URL, assertions, environment,
and authorized test-account details. Do not ask again for values already
provided and unambiguous. The shared `QYRION_APP_URL` is the Qyrus tenant;
`--start-url` is the website being tested, even if both are Qyrus hosts.
Follow `safety-policy.md` for target credentials and human authentication.
Use `private-execution.md`'s input/output wrapper for credential-bearing
calls and history; plain stdin does not prevent CLI echoes or local logs.
The parent's inability to type a password in its own browser does not by
itself establish a Qyrion limitation. Host restrictions still apply to
delegated actions; never route around them.

Reuse working setup and confirmed team selection via `credentials.md`.
Ask only for a genuinely missing target/build, destination for saving,
unresolved environment/team, or material scope/account dependency. Do not
make execution wait for project/module/suite metadata needed only at save
time when the authorized objective can already run.

## New coverage stays new

For a new objective, finding a similar saved script may inform assertions or
avoid an accidental duplicate save; it does not replace the requested fresh
web/mobile session. Do not begin with an exhaustive MCP project inventory.
After verifying a new run, save it using supported Qyrion `sessions save-test`
or the requested Aegis destination. Inspect captured login inputs and the live
save contract: do not assume `save-test` redacts them. Use supported runtime
parameters/secret references only when verified; never invent alias support.
Keep credentials out of plaintext exports, shared scripts and local records;
resolve a required save-time credential decision without blocking the
authorized exploratory run. Read the created asset back. "Create
and save" already authorizes that bounded save; do not ask again.
Save success is distinct from a successful rerun and verified reuse.

## Independent runs and continuity

Split independent objectives using `parallel-orchestration.md`; multiple CLI
processes are sufficient and do not require host subagent support. Preserve
sequential order for shared login/state or dependent flows. User-facing plans
describe the scenarios and relevant concurrency dependency, not tool catalogs.

Use `local-state.md` to retain scoped IDs, outcomes, and a safe host-memory
pointer after creation/completion. Revalidate saved IDs before reuse. Use
`update-checks.md` for the throttled CLI release check during active tasks;
do not interrupt a run or install an update without the user's acceptance.
