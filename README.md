# QyrusAI Assure

![QyrusAI](assets/qyrusai-logo.png)

[Installation guide and API-key video](https://qqyrus.github.io/qyrion/)

## Install with your coding agent

Paste this into Codex, Claude Code, or Antigravity:

> Set up QyrusAI Assure from https://github.com/QQyrus/qyrion.

Your agent downloads and installs the plugin, follows its bundled setup skill,
prepares missing dependencies, and checks the Qyrus connections. You only need
your Qyrus application URL and API key in a private file; provide the file's
path when asked, not the key in chat. Setup reuses an existing configuration
and asks you to select a team when needed.

If the plugin is already installed, **“Set up QyrusAI Assure”** is enough.
Your agent will tell you if the host needs a new chat or restart to load it.
See [installation details](#install--refresh) for agent/host instructions and
[private credentials](#one-private-key-file) for the file format.

The [landing page](https://qqyrus.github.io/qyrion/) includes the setup prompt,
a video showing how to generate your X-API-Key, and example tasks. To preview
it from a local checkout, open `index.html` or serve the plugin folder with
`python3 -m http.server 8766` and visit `http://localhost:8766`.
See [page maintenance](docs/landing-page.md) when updating the tutorial.

## What it includes

QyrusAI Assure brings Qyrus MCP (Aegis), Qyrion mobile/web sessions, and the
public `qyrusai` Python SDK into one coding-agent plugin. Its installation
identifier is `qyrusai-assure`. Existing `qyrion-agent-plugin` installations
should migrate to the new ID using the host instructions below.

An agent can read a connected work item, generate candidate scenarios, execute
checks, create reusable Qyrus web/API assets, collect evidence, and return
results to the source within the user's authorized scope. The loop recipes
cover assurance, operations, and modernization; external connectors and
permissions determine which steps are available. The plugin is not a scheduler
or a service running in the background.

## How testing works

Ask for the outcome: “Create and save tests for this ticket” or “Run our
existing checkout tests.” New web and mobile coverage runs through Qyrion's
cloud agents. The plugin uses the URL and authorized test-account details
already supplied for the task; it does not substitute the coding agent's
own browser or ask users to choose among implementation tools.

When the intent is unclear, the agent asks only: **“Create and save a new
test, or look for an existing one?”** Explicit requests and preferences
already given take precedence. Independent objectives can run concurrently;
shared logins, test data, and dependencies must permit it. If simultaneous
sign-in support is unknown, the agent asks about that dependency or runs
sequentially. Each session remains bounded and is cleaned up by its owner.
See [execution routing](shared/execution-routing.md) and
[parallel sessions](shared/parallel-orchestration.md).

Target-app login details are separate from the Qyrus API key. When the host
permits using already-authorized test credentials, the plugin's
[private execution helper](shared/private-execution.md) carries objective
input to Qyrus and filters echoed text from CLI output, while isolating and
removing temporary CLI logs. Such
input may remain in Qyrus session history; a local private file or stdin does
not make it a secret-vault channel. Human-only authentication steps still
follow the host's rules. See [credential handling](shared/safety-policy.md).

## Remembering results and checking updates

The agent records reusable session, test, suite, and project IDs in a private
`qyrusai-assure/` subfolder beside the selected credentials file. With the
default setup this is `~/.config/qyrus/qyrusai-assure/`. Records are scoped
to the Qyrus environment, team, and optional target origin; IDs are checked
against the live service before reuse. Passwords, keys, objectives, raw
responses, and signed URLs do not belong in these records. Hosts with a
permitted memory facility may remember the record-store pointer and scoped
IDs. The file store remains usable without host memory.

During plugin use, the agent checks public Qyrion releases at most once
every **four hours**, including published betas. A timestamped state file
tracks checks, offers/declines, and verified installations. Unchanged or
declined updates stay quiet; an available update is installed only after
acceptance. Source/editable installations and executable overrides are
preserved. This is an activity-triggered check, not a background timer;
plugin/skill updates still use the host's plugin update mechanism.
See [local records](shared/local-state.md) and
[update checks](shared/update-checks.md) for commands and recovery.

## One private key file

The user creates a file outside Git and the plugin cache, for example
`~/.config/qyrus/credentials.env`, containing:

```dotenv
X-API-Key=<your-xapi-key>
QYRION_APP_URL=stg.qyrus.com
```

Use `.env.example` as a template. Do not paste real keys into chat. On macOS
or Linux, run `chmod 600 /absolute/path/to/credentials.env`. Then give the
agent the path. From the installed plugin root:

```bash
python3 scripts/qyrus_env.py configure --env-file /absolute/path/to/credentials.env
python3 scripts/qyrus_env.py check
```

`configure` installs `qyrusai==1.0.9` in a uv-managed isolated environment
when missing (or reuses the cached environment), then derives and writes
`QYRUS_MCP_URL` into that private file:

| Qyrus application URL | Derived MCP URL |
|---|---|
| `stg.qyrus.com` | `https://stg-mcp.qyrus.com/mcp` |
| `app.qyrus.com` | `https://app-mcp.qyrus.com/mcp` |
| `<env_name>.qyrus.com` | `https://<env_name>-mcp.qyrus.com/mcp` |

It saves only the file path in `~/.config/qyrus/plugin.json`. At runtime the
endpoint is derived again from the application URL, preventing a stale saved
endpoint from changing the destination. `QYRUS_MCP_URL` is generated, not a
separate user setting. The key must belong to that environment and have the
needed product entitlements.

The helper never sources shell code or prints secrets. It maps `X-API-Key`
to `QYRION_API_KEY` and `QYRUS_API_KEY` for child processes; the MCP bridge
sends the same key in the `X-API-Key` header. Hyphenated dotenv keys cannot
be shell-sourced. See [credential contract](shared/credentials.md) and
[environment reference](docs/env.md) for parsing and precedence.

## Setup and first use

If you only installed the plugin, say **“Set up QyrusAI Assure.”** Its setup skill
checks and installs missing local dependencies, reuses an existing credential
file or asks for its path, runs the bundled configure helper, and verifies
the requested surfaces. Users do not need to name prerequisite checks.
The agent follows [the setup runbook](shared/prerequisites.md); local installs
are part of setup, while host restrictions or unavailable access are reported
as concrete blockers. Plugin registration alone does not execute installers.
If your original request was to set up QyrusAI Assure, the agent completes
these steps during that request. A host reload does not require repeating setup.

Setup prepares these dependencies:

- `python3` and `uv` on the agent host's PATH. The MCP launcher uses Python 3.12+ and an
  isolated, pinned `fastmcp==4.0.10` script dependency; first launch may download
  that runtime/dependency. Prewarm it before reconnecting MCP if startup times out.
- Qyrion CLI for device/browser runs, installed from the newest published
  [public release](https://github.com/QQyrus/qyrion/releases), including betas,
  or the user's selected source checkout. Setup downloads only the platform
  binary/archive, without checksum-file or hash checks, and preserves working
  installations and profiles. It uses the release list because GitHub's
  `/releases/latest` endpoint excludes prereleases. On Windows, setup saves
  the x64 executable as `qyrion.exe` on the user's PATH and checks its version
  and capabilities.
- `qyrusai==1.0.9` is prepared automatically by setup. SDK commands also
  ensure it is present, using the same uv-managed environment; no manual
  global pip installation is required.
- An independently connected work-management app for reading/writing issues.
  The Qyrus key does not authenticate Jira, Linear, Azure DevOps, etc.

After configuring the file, restart/reconnect MCP. Discover Qyrus tools and
call `qyrus_guide_get` first, read its setup/identifier sections, then call
`qyrus_teams_get_by_api_key` with `{}` to discover the available teams using
the same API key. For Qyrion, check capabilities:

```bash
python3 scripts/qyrus_env.py run -- qyrion capabilities --json
```

Select the intended team from the MCP response's `Web Automation Teams`;
if multiple are returned and no choice exists, ask the user. Preserve its
UUID exactly; do not use the separate organization ID. Set `QYRION_TEAM_ID`
in the private file for repeatable automation (or use the verified Qyrion
profile team), then check Qyrion access with helper-wrapped
`qyrion sessions list --json`.

The plugin does not require `qyrion auth teams`: that command calls a separate
gateway route whose authentication policy can reject the same key accepted
by MCP. No additional Authorization token is needed for the MCP team lookup.
MCP success does not establish authorization on other Qyrus services; check
the surface needed for the task. See [team setup](shared/credentials.md).
The Qyrus application URL is distinct from the website being tested:

```bash
python3 scripts/qyrus_env.py run -- qyrion run \
  --message-file /absolute/path/web-objective.md \
  --platform web --start-url https://test.example.com \
  --mode ci --timeout 1800 --jsonl
```

Require `features.web_sessions`; omit mobile device/app flags. A submitted
run is not a completed verification. Retain its run ID and inspect results.

SDK scripts run through the same loader and automatically install missing SDK
packages in the isolated environment:

```bash
python3 scripts/qyrus_env.py sdk -- /absolute/path/generate.py
```

## Skills

| Skill | Responsibility |
|---|---|
| `qyrus-setup` | Dependency installation, private env-file onboarding, URL derivation, key rotation, team selection |
| `qyrus-mcp` | Guide-first team discovery and Aegis web/API test authoring, execution and diagnosis |
| `qyrusai-sdk` | Nova scenarios/steps, synthetic data, API assertions/specs, image analysis and explicit evaluator workflows |
| `qyrus-web-testing` | Qyrion browser verification and evidence-to-Aegis reusable web assets |
| `qyrus-value-loops` | Work-item-to-evidence orchestration, resumption and authorized write-back; adaptable recipes for all 18 supplied loops |
| `qyrion-cli` | Mobile/web session lifecycle, questions, artifacts, troubleshooting |
| `qyrus-device-testing` | Codebase/requirement-driven physical-device tests |
| `qyrus-change-impact` | Diff-driven minimal test selection and triage |
| `answer-qyrion-agent-questions` | Evidence-based answers to mid-run questions |

Example requests:

- “Validate this story against the staging website and attach the evidence.”
- “Explore this flow and save a reusable Qyrus web test, then rerun it.”
- “Reproduce this bug on the named build and report the smallest failing case.”
- “Compare this journey on legacy and target systems; explain parity gaps.”

Write-back must be authorized, deduplicated, and read back after submission.
A pass does not automatically authorize closing a bug, merging, deploying,
or decommissioning a system. Operate/Modernize recipes need additional
telemetry, deployment, or data connectors as described in the loop catalog.

## Install / refresh

The public [QQyrus/qyrion repository](https://github.com/QQyrus/qyrion)
contains the plugin at its root, including a Claude marketplace catalog.
For Claude Code, use the [marketplace installation](#claude-code) below;
Claude obtains the complete package. For hosts that need a local source,
download/clone the complete package into a user-owned directory named
`qyrusai-assure`, preserving its hidden manifests, scripts, skills, and
assets. Reuse a verified existing checkout without overwriting local changes.
For example, a new checkout on macOS/Linux can use:

```bash
git clone https://github.com/QQyrus/qyrion.git "$HOME/plugins/qyrusai-assure"
```

Read `skills/qyrus-setup/SKILL.md` from the installed/downloaded folder and
follow its bundled references directly during first-time setup; the skill does not have
to be installed or auto-discovered yet. Register the package with the current
host as described below, prepare dependencies, and run `scripts/qyrus_env.py`
through that setup workflow. Keep all user's credentials outside the clone
and plugin cache. Do not ask the user to enumerate prerequisite checks.

### Codex

Register `.codex-plugin/plugin.json` through Codex's personal plugin
marketplace, preserving other entries. For the checkout above, the personal
marketplace entry's source is `./plugins/qyrusai-assure` relative to the
user's home directory, and its plugin name is `qyrusai-assure`.
Use the host's plugin-installation tooling to register the source, then install
`qyrusai-assure` from that marketplace.

The entry to merge into `~/.agents/plugins/marketplace.json` is below. If the
file does not exist, create a catalog with `"name": "personal"` and a
`"plugins"` array containing it; otherwise preserve the catalog's name and
other entries. An existing same-name entry should be verified and updated,
not duplicated.

```json
{
  "name": "qyrusai-assure",
  "source": { "source": "local", "path": "./plugins/qyrusai-assure" },
  "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
  "category": "Developer Tools"
}
```

Then install from the registered marketplace (using its actual name):

```bash
codex plugin add qyrusai-assure@personal
```

If the user's marketplace has a different name, use that verified name.
The bundled `.claude-plugin/marketplace.json` uses Claude's schema, not Codex's;
register the local folder in Codex before attempting the install command.
After setup and installation, start a new chat so Codex loads the skills and MCP server.
Refresh/reinstall after updates because Codex runs a cached copy.
For an old `qyrion-agent-plugin` install, register and verify the new ID before
disabling/removing only the old plugin through Codex's plugin tooling. Preserve
other marketplace entries, private credentials, and working CLI installs;
Claude's rename map does not migrate Codex or Cursor registrations.

Codex loads `.mcp.json`: relative `cwd: "."` resolves to the installed
plugin root. A small Python bootstrap resolves the script path and starts uv. The stdio launcher bridges to the inferred HTTPS MCP endpoint,
loading the private file itself rather than relying on desktop shell exports.
Only this launcher needs to execute locally; Qyrus tools remain remote.
The bootstrap and credential wrapper use a waiting subprocess on Windows,
preserving output and exit status without the CRT `exec*e` path. POSIX keeps
process replacement. If an older cached wrapper reports an access violation
while direct CLI checks work, update the plugin and retry the read-only check;
the failure does not by itself establish bad credentials or a broken CLI.
The `UnicodeEncodeError` seen when 0.3.4-beta renders a session list through
Rich is a separate CLI output issue. It requires a CLI release containing the
plain-JSON fix; a plugin refresh alone cannot change the downloaded executable.
See [Windows JSON troubleshooting](shared/cli-contract.md#windows-json-encoding-failures).

### Claude Code

Install persistently from the public repository in user scope:

```bash
claude plugin marketplace add QQyrus/qyrion
claude plugin install qyrusai-assure@qyrusai-assure --scope user
claude plugin list
claude plugin details qyrusai-assure
```

Inside a Claude session, the equivalent commands start with `/plugin`
instead of `claude plugin`. The repository includes its own
`.claude-plugin/marketplace.json`, named `qyrusai-assure`, with source `./`.
The plugin therefore stays within the marketplace root in both the public
repository and this development repository. No private repository access or
handmade `personal` marketplace is needed.
The catalog maps the former `qyrion-agent-plugin` name to `qyrusai-assure`
for existing installs from this marketplace. After refreshing the catalog,
run the install command above to populate the renamed plugin's cache.
Older `@personal` registrations need the migration described below.

During a setup request, read the installed `skills/qyrus-setup/SKILL.md`
directly and complete dependency, credential and connection checks now.
Run `/reload-plugins` if Claude requests it, or start a new session, to activate
the skills and MCP server in that session. Report activation pending separately
from successful helper/connection checks; do not ask the user to repeat setup.

For subsequent public updates:

```bash
claude plugin marketplace update qyrusai-assure
claude plugin update qyrusai-assure@qyrusai-assure
```

For explicit local development, resolve the plugin directory's real path
before registering it as a local marketplace, or launch it for one session:

```bash
claude --plugin-dir /absolute/path/to/qyrusai-assure
```

`--plugin-dir` is a development launch, not persistent installation. Do not
wrap a symlink into a marketplace whose root excludes its real target, create
an ad hoc catalog in the user's project, or edit `.git/info/exclude` during
setup. See [Claude setup and migration](skills/qyrus-setup/references/claude-installation.md)
for existing `@personal` installs and unreleased local packages.

The Claude manifest references the same `.mcp.json`. The bootstrap uses
Claude's `CLAUDE_PLUGIN_ROOT` process environment when present, so it does not
depend on the project working directory. `/reload-plugins` or restart after
changes. There is only one bundled Qyrus server definition.

### Antigravity

The root `plugin.json` lets Antigravity load the same nine skills. For
Antigravity 2.0 or the standalone IDE, install the complete package under
`~/.gemini/config/plugins/qyrusai-assure/` (global) or
`<workspace>/.agents/plugins/qyrusai-assure/` (workspace-only). In Antigravity
CLI, use `agy plugin install /absolute/path/to/qyrusai-assure` and locate the
installed copy before setup. See Google's [plugin documentation](https://antigravity.google/docs/plugins).

Say **“Set up QyrusAI Assure.”** The agent follows
[Antigravity setup](skills/qyrus-setup/references/antigravity-installation.md),
prepares prerequisites and the existing private file, then runs this helper
from the installed package:

```bash
python3 scripts/qyrus_antigravity.py
```

It registers the Qyrus bridge in `~/.gemini/config/mcp_config.json`, using
absolute executable/script paths and preserving other servers. The key stays
in the private `.env`; Antigravity receives a local stdio connection. For a
workspace-only install, pass `--config /absolute/workspace/.agents/mcp_config.json`.
If the host shows a different config path, use that explicit path. Refresh MCP
and verify guide/team discovery before claiming the connection works.

Connectors such as Atlassian, Linear, and GitHub are separate MCP servers with
their own authentication and permissions. They can supply work items to the
Qyrus value-loop skills; the Qyrus key does not authenticate those services.
See Google's [MCP documentation](https://antigravity.google/docs/mcp).
This package supports local installation; it is not a claim of a Google
marketplace listing. Native Antigravity discovery and live connection checks
must still be verified on the target host.

### Cursor

The existing Cursor skill manifest is retained, but native plugin/MCP loading
remains unverified. For manual MCP registration use an absolute path to
`scripts/qyrus_mcp.py` with command `uv` and args
`["run", "--quiet", "--script", "/absolute/plugin/path/scripts/qyrus_mcp.py"]`.
Do not assume Claude's root placeholder works in Cursor.

## Development and verification

Shared reference sources live in `shared/`. Run `scripts/build-packages.sh`
after editing them; generated `skills/*/references/` copies are not hand-edited.
Skills include these references so their contracts travel with the bundle;
credential/MCP executable helpers require the whole plugin to be installed.

From the plugin root (the public repository root, or
`plugins/qyrion-agent-plugin` in the development repository):

```bash
bash scripts/build-packages.sh
uv run --with pytest --with fastmcp==4.0.10 --python 3.12 \
  pytest tests -q
```

Tests use synthetic keys and a loopback MCP fixture, including a real stdio ↔
HTTP guide call. The SDK/bootstrap checks may download public packages if
the uv cache is cold. They do not authenticate to Qyrus, spend cloud session time,
or modify work items. See `tests/trigger-evals.md` for behavioral cases and
`CHANGELOG.md` for the release summary. Live host loading and authenticated
MCP/Qyrion/SDK acceptance remain separate checks.

## Public release updates

Qyrion releases in the development repository trigger the public mirror after
the CLI release succeeds. The mirror copies this entire plugin folder to
`QQyrus/qyrion`'s `master` branch, including this README and
`assets/qyrusai-logo.png`, the Antigravity root `plugin.json`/setup helper,
and `.claude-plugin/marketplace.json`, and publishes
the matching tag and CLI assets.
The README's relative image and setup links therefore work in both locations.
Only changes included in that release commit are mirrored; pushing a normal
feature branch does not update the public package.
The plugin version in the host manifests is independent of the CLI release
version; bump it when changing the plugin so cached installations receive
updates. A working editable CLI may report the source version instead of the
release version; setup verifies capabilities and its installation source.

Sources: [public qyrusai](https://pypi.org/project/qyrusai/),
[FastMCP proxy](https://gofastmcp.com/servers/providers/proxy),
[Codex MCP config implementation](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/plugin_config.rs),
and the current Qyrion docs/source. The attached Aegis guidance was distilled
into a skill; the attached HTML supplied recipes, not execution authorization.
