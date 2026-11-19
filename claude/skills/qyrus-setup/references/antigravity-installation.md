# Antigravity installation and connectors

Scope: native QyrusAI Assure skills plus the existing Qyrus MCP bridge on
Antigravity 2.0, the standalone IDE, and Antigravity CLI. This runbook follows
Google's current [plugin](https://antigravity.google/docs/plugins) and
[MCP](https://antigravity.google/docs/mcp) contracts. Older hosts may expose
different configuration locations; use the file opened by their MCP manager
rather than creating a competing configuration.

## Install the complete package

The package's root `plugin.json` identifies `qyrusai-assure`; Antigravity loads
the existing nine `skills/*/SKILL.md` folders. Do not install the Claude
marketplace manifest as an Antigravity marketplace or copy only the skills:
their setup also needs this package's scripts and shared references.

- **Antigravity 2.0 / IDE:** place the full package at
  `~/.gemini/config/plugins/qyrusai-assure/` for global use, or at
  `<workspace>/.agents/plugins/qyrusai-assure/` for that workspace only.
- **Antigravity CLI:** use `agy plugin install /absolute/path/to/qyrusai-assure`,
  or `/plugin install /absolute/path/to/qyrusai-assure` in its interactive
  prompt. Inspect the installed package location; the documented CLI cache is
  `~/.gemini/antigravity-cli/plugins/qyrusai-assure/`.

For a new global IDE/2.0 installation, cloning the public repository into the
global plugin directory is sufficient packaging. Resolve the user's home
directory using the host OS; preserve an existing checkout and local changes.
On macOS/Linux, for example:

```bash
git clone https://github.com/QQyrus/qyrion.git "$HOME/.gemini/config/plugins/qyrusai-assure"
```

Read this package's `skills/qyrus-setup/SKILL.md` directly during bootstrap;
do not wait for discovery before following it. Run prerequisite installation
and `qyrus_env.py configure` from the actual installed package as usual.
Preserve a working Qyrion install and the private credentials path. On Windows,
use the verified Python/uv executable paths when PATH has not refreshed.

## Register the connection without duplicating the key

After configuring the private file, run from the installed package:

```bash
python3 scripts/qyrus_antigravity.py
```

The helper merges a `qyrus` stdio server into
`~/.gemini/config/mcp_config.json`, preserving unrelated connectors. It writes
absolute paths to the verified uv executable, bridge script, and working
directory. It never reads the credentials file or copies the key into JSON.
The bridge uses the saved/default private file and derives the endpoint at
runtime. No Claude-specific plugin-root variable or relative-cwd assumption
is involved. The package deliberately does not ship a second root
`mcp_config.json` with guessed paths or a duplicate Qyrus server.

For workspace-only installation, target that workspace's configuration:

```bash
python3 scripts/qyrus_antigravity.py --config /absolute/workspace/.agents/mcp_config.json
```

Do not point a global server at a temporary or workspace-only plugin folder.
For a host using a different configuration path, pass the path shown by
**Manage MCP Servers → View raw config**. Never dump an existing config into
chat; it may contain other connectors' secrets.

The helper preserves an identical Qyrus registration. If it finds a different
`qyrus` entry, it leaves the file unchanged. Determine whether that entry is
the user's existing Qyrus integration before using `--replace-qyrus`; preserve
an intentionally different connection or ask about the actual conflict.
Replacement retains disabled status and disabled-tool choices. It does not
grant tool approvals or change Antigravity permission policies.

Refresh MCP through the host's manager (`/mcp` in the CLI), then verify tool
discovery, `qyrus_guide_get`, and `qyrus_teams_get_by_api_key` with `{}`. Verify
Qyrion and SDK readiness using the main setup runbook. Report nine discovered
skills, the Qyrus connection, and any pending host restart separately. After
a plugin update or path move, rerun setup from the current installed package.
CLI/IDE recognition must be checked in the actual host; offline configuration
tests alone do not establish it.

## Other connectors and work-item loops

Antigravity's MCP manager connects external tools. Each service has its own
configuration and authentication: remote connections use `serverUrl` and may
use OAuth, Google credentials, or custom headers; local servers use `command`
and `args`. The Qyrus integration uses the local bridge to keep one private
key file. A direct remote Qyrus connection is possible but is not this setup
path, since it would duplicate key handling.

Connect a work tracker such as Atlassian or Linear separately through its
supported MCP integration. Codex or Claude authentication is not automatically
an Antigravity login. Verify the connection's read/write capabilities before
starting a loop; the Qyrus key authenticates only Qyrus. The value-loop skill
can then coordinate reading the work item, running Qyrus checks, and writing
back authorized evidence. Host permissions still apply, and unavailable
connectors are reported as blockers instead of invented tool calls.

This local installation path does not list QyrusAI Assure in Google's curated
marketplace. Do not describe marketplace discovery or native host validation
as complete until each is separately verified.
