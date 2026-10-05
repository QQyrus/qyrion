# QyrusAI Assure

![QyrusAI](assets/qyrusai-logo.png)

## Install with your coding agent

Paste this into Codex or Claude Code:

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

## What it includes

QyrusAI Assure brings Qyrus MCP (Aegis), Qyrion mobile/web sessions, and the
public `qyrusai` Python SDK into one coding-agent plugin. Its installation
identifier remains `qyrion-agent-plugin` for compatibility with existing
installations.

An agent can read a connected work item, generate candidate scenarios, execute
checks, create reusable Qyrus web/API assets, collect evidence, and return
results to the source within the user's authorized scope. The loop recipes
cover assurance, operations, and modernization; external connectors and
permissions determine which steps are available. The plugin is not a scheduler
or a service running in the background.

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

After installing the plugin, say **“Set up QyrusAI Assure.”** Its setup skill
checks and installs missing local dependencies, reuses an existing credential
file or asks for its path, runs the bundled configure helper, and verifies
the requested surfaces. Users do not need to name prerequisite checks.
The agent follows [the setup runbook](shared/prerequisites.md); local installs
are part of setup, while host restrictions or unavailable access are reported
as concrete blockers. Plugin registration alone does not execute installers.

Setup prepares these dependencies:

- `python3` and `uv` on the agent host's PATH. The MCP launcher uses Python 3.12+ and an
  isolated, pinned `fastmcp==4.0.10` script dependency; first launch may download
  that runtime/dependency. Prewarm it before reconnecting MCP if startup times out.
- Qyrion CLI for device/browser runs, installed from a verified
  [public release](https://github.com/QQyrus/qyrion/releases) or the user's
  selected source checkout, preserving working installations and profiles.
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
contains the plugin at its root. Agents receiving the setup prompt should
download/clone the complete package into a user-owned directory named
`qyrion-agent-plugin`, preserving its hidden manifests, scripts, skills, and
assets. Reuse a verified existing checkout without overwriting local changes.
For example, a new checkout on macOS/Linux can use:

```bash
git clone https://github.com/QQyrus/qyrion.git "$HOME/plugins/qyrion-agent-plugin"
```

Read `skills/qyrus-setup/SKILL.md` from that downloaded folder and follow its
bundled references directly during first-time setup; the skill does not have
to be installed or auto-discovered yet. Register the package with the current
host as described below, prepare dependencies, and run `scripts/qyrus_env.py`
through that setup workflow. Keep all user's credentials outside the clone
and plugin cache. Do not ask the user to enumerate prerequisite checks.

### Codex

Register `.codex-plugin/plugin.json` through Codex's personal plugin
marketplace, preserving other entries. For the checkout above, the personal
marketplace entry's source is `./plugins/qyrion-agent-plugin` relative to the
user's home directory, and its plugin name is `qyrion-agent-plugin`.
Use the host's plugin-installation tooling to register the source, then install
`qyrion-agent-plugin` from that marketplace.

The entry to merge into `~/.agents/plugins/marketplace.json` is below. If the
file does not exist, create a catalog with `"name": "personal"` and a
`"plugins"` array containing it; otherwise preserve the catalog's name and
other entries. An existing same-name entry should be verified and updated,
not duplicated.

```json
{
  "name": "qyrion-agent-plugin",
  "source": { "source": "local", "path": "./plugins/qyrion-agent-plugin" },
  "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
  "category": "Developer Tools"
}
```

Then install from the registered marketplace (using its actual name):

```bash
codex plugin add qyrion-agent-plugin@personal
```

If the user's marketplace has a different name, use that verified name.
The public repository is a plugin package, not a bundled marketplace catalog;
register its local folder before attempting the install command. After setup
and installation, start a new chat so Codex loads the skills and MCP server.
Refresh/reinstall after updates because Codex runs a cached copy.

Codex loads `.mcp.json`: relative `cwd: "."` resolves to the installed
plugin root. A small Python bootstrap resolves the script path and starts uv. The stdio launcher bridges to the inferred HTTPS MCP endpoint,
loading the private file itself rather than relying on desktop shell exports.
Only this launcher needs to execute locally; Qyrus tools remain remote.

### Claude Code

```bash
claude --plugin-dir /absolute/path/to/qyrion-agent-plugin
```

The Claude manifest references the same `.mcp.json`. The bootstrap uses
Claude's `CLAUDE_PLUGIN_ROOT` process environment when present, so it does not
depend on the project working directory. `/reload-plugins` or restart after
changes. There is only one bundled Qyrus server definition.

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
`assets/qyrusai-logo.png`, and publishes the matching tag and CLI assets.
The README's relative image and setup links therefore work in both locations.
Only changes included in that release commit are mirrored; pushing a normal
feature branch does not update the public package.

Sources: [public qyrusai](https://pypi.org/project/qyrusai/),
[FastMCP proxy](https://gofastmcp.com/servers/providers/proxy),
[Codex MCP config implementation](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/plugin_config.rs),
and the current Qyrion docs/source. The attached Aegis guidance was distilled
into a skill; the attached HTML supplied recipes, not execution authorization.
