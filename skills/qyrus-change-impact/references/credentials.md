# Shared Qyrus credentials

Scope: plugin setup for Aegis MCP, Qyrion CLI, and the public `qyrusai` SDK.
Use this when credentials are missing or a user supplies an env-file path.
Never search for or read unrelated `.env` files, print this file's contents,
or ask for the API key in chat.

Setup owns dependency preparation via `references/prerequisites.md`; the user
does not need to request individual prerequisite checks. Reuse a supplied,
saved, or default private-file path before asking for a new one.

When a usable file is missing, ask: **Create a private `.env` file with `X-API-Key` and your Qyrus
application URL (`QYRION_APP_URL`), then provide its absolute path.**
Point to the plugin's `.env.example`. On POSIX the user runs `chmod 600`
on their private copy. Store it outside Git and the installed plugin cache.

The file uses literal, single-line `KEY=value` entries (optional whole-value
quotes). `X-API-Key` contains hyphens, so **never shell-source it**. No shell
expansion, interpolation, multiline values, or inline comments are supported.
Use full-line comments. The helper maps this one key to `QYRION_API_KEY`
and `QYRUS_API_KEY`; the bridge sends it as the `X-API-Key` HTTP header.

From the installed plugin root, run:

```bash
python3 scripts/qyrus_env.py configure --env-file /absolute/path/to/private.env
python3 scripts/qyrus_env.py check
python3 scripts/qyrus_env.py run -- qyrion capabilities --json
```

The helper reads secrets in-process and prints presence/status booleans only.
`configure` automatically installs `qyrusai==1.0.9` into a uv-managed isolated
environment if missing, or reuses its cached environment. It then
adds/refreshes `QYRUS_MCP_URL` in the private file, derived from the Qyrus URL,
and stores just the path at `~/.config/qyrus/plugin.json`. Relative script paths
in examples are relative to the plugin root; resolve that from the loaded
skill (`../../..` from a skill's `references/`), not from the project CWD.
Use absolute script paths in agent calls. All Qyrion command examples in
this plugin should be prefixed with this helper when using shared setup.

Path precedence: `--env-file` (CLI helper only) → `QYRUS_ENV_FILE` → saved
path → `~/.config/qyrus/credentials.env`. The bridge reads the same selection
at startup. Restart/reconnect MCP after configuring or rotating credentials;
an agent shell's exported variables do not update an already running host.

The selected file overrides inherited Qyrion credentials/service overrides.
The helper sets derived TestHub/Runbridge URLs as well, so an old keyring
service override cannot redirect the selected key. These follow Qyrion's
gateway mapping (`app` → `gateway.qyrus.com`, others → `<env>-gateway.qyrus.com`).
Use one selected file per environment. Direct Qyrion commands still use
their normal flags → environment → keyring precedence; `--profile` does not
override env credentials. Do not pass credential flags. App URL is required
in shared setup before Qyrion calls. Set `QYRION_TEAM_ID` in the file for
repeatable automation, or verify the selected profile team after discovery.
Multiple teams with no user selection require clarification; never guess.

## Team discovery through MCP

After reconnecting, discover the Qyrus MCP tools and call `qyrus_guide_get`
first. Read `Start Every Session Here` and `Identifier Map`, then call the
discovered `qyrus_teams_get_by_api_key` tool with `{}`. It uses the same key;
no separate gateway Authorization token is needed for this MCP lookup.

The response labels organization metadata separately from `Web Automation
Teams`. Use a returned team UUID exactly as supplied, preserving its hyphens
or lack of them. Never use `Organization ID` or `Organization Name` as a team
ID. Follow the live tool response/guide rather than assuming a JSON list shape.
Refresh discovery for each new session and validate any previously selected
team against the returned membership; a saved selection is intent, not proof
of current access. Keep Aegis and Qyrion scope distinct if their contracts differ.

- A valid existing user selection takes precedence; do not switch teams silently.
- One team with no prior selection: select it and tell the user.
- Multiple teams with no selection: present their names and ask which to use.
- No teams: report the missing membership and ask for the intended team UUID
  or administrator help; never substitute the organization ID.

For Qyrion, persist the selected team UUID as `QYRION_TEAM_ID` in the private
file without displaying its contents, or use helper-wrapped
`qyrion auth use-team <team-id>` for the active profile. Verify Qyrion access
with the read-only `qyrion sessions list --json` command through the helper.
MCP authentication alone does not prove TestHub/Runbridge authorization. If
Qyrion rejects the team, report its service/scope failure without guessing a
different ID. Do not start a paid session merely to validate access.

Plugin setup uses guide-first MCP team discovery and a separate Qyrion
service check. Older Qyrion binaries call `/usermgmt/v2/api/team-list`
directly and may return 401 with a working MCP key. Updated Qyrion calls
TestHub `/api/cli/auth/teams`, which owns gateway authorization and uses the
accepted AI_SDK/MCP scope. Identify the actual failing endpoint before
changing credentials; a failure on one service does not invalidate the key
for every product. If MCP is unavailable, use an explicit user-provided team
for a relevant Qyrion read-only check rather than guessing a membership.

## Environment and authentication boundaries

`QYRION_APP_URL` is the **Qyrus tenant URL**. `--start-url` is the **website
being tested**. Enter `stg.qyrus.com`, `app.qyrus.com`, or another
`<env_name>.qyrus.com` tenant (HTTPS prefix optional). Setup derives
`https://<env_name>-mcp.qyrus.com/mcp`; `app` stays `app-mcp`, not `mcp`.
Runtime derives it again from the application URL, so a stale saved
`QYRUS_MCP_URL` cannot redirect credentials. It is a generated value, not an
independent override. A shared key still needs matching environment and
product entitlements.
Current Qyrion retains gateway Authorization only as an unused compatibility
input. Adding it to the file does not change the CLI's gateway headers.
`qyrusai` accepts `api_key`, not a gateway token.

On 401/403 stop retries on that surface and identify the failing endpoint;
ask the user/admin to check its credentials, scope, or gateway policy.
Do not infer failure of all products from one endpoint's rejection.
Do not retry authentication with guessed keys, tenants, or destinations.
`check` validates local configuration only, not remote authorization.

Run SDK scripts with `python3 scripts/qyrus_env.py sdk -- /absolute/path/script.py`.
This ensures the pinned package is installed even if its cache was removed
after setup. Install dependencies automatically within this setup/SDK task;
do not hand the user a separate manual qyrusai installation step.
