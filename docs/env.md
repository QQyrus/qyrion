# Plugin environment contract

These are plugin-local settings, not new Qyrion deployable settings. There is
no Dockerfile, service setting class, Jenkins job, or deployment override.
Wiring is `.env.example` → `scripts/qyrus_env.py` → the CLI/SDK child process
or `scripts/qyrus_mcp.py`. No real credential belongs in the distributed plugin.

| Variable | Purpose / classification | Safe example or default | Wiring |
|---|---|---|---|
| `X-API-Key` | Shared authentication; secret, static until rotation | `<your-xapi-key>` placeholder (rejected until replaced) | Required in private file; maps to CLI/SDK aliases and MCP header |
| `QYRION_APP_URL` | Qyrus tenant; generic, static per environment | `stg.qyrus.com` or `https://app.qyrus.com` | Required in private file; normalized to HTTPS for Qyrion and derives MCP URL |
| `QYRUS_MCP_URL` | Generated endpoint; generic, derived from tenant | `https://stg-mcp.qyrus.com/mcp` | `configure` adds/updates private file; runtime re-derives it, never trusts an override |
| `QYRION_TEAM_ID` | Selected team UUID; generic, static per workflow | Empty until discovered | Select through MCP `qyrus_teams_get_by_api_key`, preserving UUID exactly; Qyrion team-scoped calls need it or a verified profile selection; never use the organization ID |
| `QYRION_USER_EMAIL` | Optional actor attribution; personal, static per user | Omit | Optional file entry passed to Qyrion |
| `QYRUS_ENV_FILE` | Private file selector; generic local path, static per host | Omit to use saved path or `~/.config/qyrus/credentials.env` | Process env for loader/bridge; explicit helper `--env-file` wins |
| `QYRION_CLI` | Explicit executable path; generic, static per host | Omit to use `qyrion` on PATH | Inherited by loader; replaces only the executable named `qyrion` |
| `QYRION_LOG_DIR` | Private-helper child override; generic path, dynamic per command | Temporary private directory; not a user setting for this helper | `qyrus_private.py` replaces inherited CLI log location for credential-bearing operations, then removes these temporary logs on completion |
| `QYRION_API_KEY` / `QYRUS_API_KEY` | Generated child-process aliases; secret, static until rotation | Never store duplicate values | Derived from the private `X-API-Key`; replaces inherited aliases |
| `QYRION_TESTHUB_URL` / `QYRION_RUNBRIDGE_URL` | Generated service URLs; generic, derived from tenant | `https://stg-gateway.qyrus.com/df-ai-sessions-testhub-cli/v1` (Runbridge uses its corresponding context) | Set in the child environment to prevent old keyring service overrides from redirecting the selected key; `app` uses `gateway.qyrus.com` |

The private file wins over inherited Qyrion credentials and service overrides.
Unrecognized file keys are not exported. Gateway Authorization aliases are not
copied; the plugin uses MCP for team discovery instead of the separately
authenticated CLI gateway team-list route. Direct Qyrion calls retain flags/env/keyring precedence;
use the helper consistently to share credentials. Never shell-source the file.

Parsing accepts optional `export`, literal single-line values, whole-value
quotes, and full-line comments. It rejects duplicate keys, malformed lines,
unclosed quotes and missing/placeholder keys. It does not expand `${VAR}`,
`$(command)`, or backticks. POSIX files must have no group/other permissions.
Endpoints accept only `<env_name>.qyrus.com` with optional HTTPS and trailing
slash; no custom port, path, embedded credentials, query, or fragment.

`configure` first prepares the pinned qyrusai SDK in uv's isolated cache
(installing if missing), then preserves other file entries/comments, atomically writes the
inferred MCP endpoint with private permissions, then saves only the selected
absolute path in `~/.config/qyrus/plugin.json`. Restart MCP after changes.
`check` is offline presence/format validation, never proof of authentication.

The CLI/SDK wrapper and MCP bootstrap share `scripts/qyrus_process.py`.
On Windows it resolves the executable and uses `subprocess.run` with inherited
stdio, a private child environment, no shell, and no automatic retry. It waits
for completion and preserves the command's exit status, including native
Windows failure bits. POSIX retains process replacement. This avoids the
Windows CRT environment-building path used by `os.execvpe`, which has a
[reported access-violation issue](https://github.com/python/cpython/issues/143327).
The launch change neither alters credential precedence nor proves a particular
reported crash was in that CRT path without a native trace.

Antigravity registration (`scripts/qyrus_antigravity.py`) adds no environment
variables or credential copies. It writes absolute uv/script/cwd paths into
the selected host `mcp_config.json`; the same bridge then uses the existing
saved/default `QYRUS_ENV_FILE` contract. Registration does not read the private
file, authenticate, or grant tool permissions. It preserves unrelated servers,
rejects malformed/duplicate-key JSON, and requires explicit replacement of a
different existing `qyrus` entry. Qyrus disabled status/tool choices survive
replacement. New configuration files are written atomically with private
permissions on POSIX; Windows access control remains host-owned.

Local records and update checks add no environment variables. Both reuse
`resolve_env_file()` (explicit `--env-file`, process selection, saved path,
default) and store private state in the adjacent `qyrusai-assure/` directory.
`qyrus_state.py` reads only the selected file to scope IDs by normalized
application URL and team; it never exports its contents. An optional target
origin further isolates result records. `qyrus_updates.py` contacts only the
public Qyrion release API without an API key or Authorization header and
keeps release-check/installation timestamps separately from the credentials.
See `shared/local-state.md` and `shared/update-checks.md` for allowed fields,
concurrency, retention, and approval behavior. POSIX state directories/files
are private; Windows protection depends on the user's filesystem ACLs.

Credential-bearing objectives and history use `scripts/qyrus_private.py`
instead of the ordinary process wrapper. It loads the same private Qyrus
environment, passes objective text through stdin, filters known sensitive
values from JSON stdout/stderr, suppresses unstructured child output, and
isolates the CLI's `QYRION_LOG_DIR` in a temporary private directory. Its
redaction file contains target-app sensitive values and is an ephemeral
private input, not part of `.env.example`, reusable state, or host memory.
Server history and binary artifacts remain outside this text-filter boundary.
See `shared/private-execution.md`; do not assume stdin alone prevents echoes.
