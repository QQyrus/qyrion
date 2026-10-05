# Agent-owned setup

Scope: first use and dependency repair for QyrusAI Assure. A request such as
“Set up QyrusAI Assure” includes preparing its local dependencies; users do
not need to name Python, uv, Qyrion, or the SDK. This is the agent's runbook,
not a checklist to hand back to the user.

Reuse working installations and explicit executable overrides. Briefly state
what needs installing, then carry out user-local installation within the setup
request. Do not add packages to the user's project or replace system Python.
Ask only when a required credential/path, team choice, repository access, or
actual host permission is missing. Respect explicit no-install constraints.

## Python and uv

1. Resolve and execute `uv --version` and `python3 --version` (use the host's
   equivalent executable lookup on Windows). Inspect versions, not secrets.
2. If uv is missing, install it through an existing user package manager or
   Astral's [official standalone installer](https://docs.astral.sh/uv/getting-started/installation/).
   The standalone installer needs no existing Python. Download the installer
   to a temporary file, inspect it, and run it for the current OS; use the
   official HTTPS source, never a guessed package or mirror. Do not bypass
   organization installation restrictions or require sudo for a user install.
3. Prepare Python 3.12 with `uv python install 3.12`. If the plugin launcher's
   `python3` command is absent or unusable, use `uv python install 3.12 --default`
   to expose the user-managed executable. Do not use `--force` to replace an
   unrelated executable. See [uv Python installation](https://docs.astral.sh/uv/guides/install-python/).
4. Resolve the installed bin directories, update the agent process PATH, and
   verify both commands. The desktop host may need reopening to inherit a
   changed PATH; a working shell alone does not prove MCP can launch. Resolve
   this before declaring setup complete rather than reinstalling repeatedly.

A working newer `python3` can run the bootstrap; installing managed Python
3.12 for the SDK does not require replacing that interpreter. The bundled
Windows launcher uses subprocesses to avoid CRT `exec*e` crashes; changing
the default Python version alone is not a fix for that launch path.

## Qyrion

For full plugin setup, prepare Qyrion as well. For an explicitly MCP-only or
SDK-only task, defer Qyrion until a session workflow needs it.

- Resolve `QYRION_CLI` first, then `qyrion` on PATH. Run `capabilities --json`
  and check the features needed for the task. Preserve a working installation;
  an invalid explicit override is a configuration problem, not permission to
  silently substitute another executable.
- If missing, install the platform binary from the newest published
  [Qyrus release](https://github.com/QQyrus/qyrion/releases), including a
  prerelease/beta when it is newest. Use the public release list at
  `https://api.github.com/repos/QQyrus/qyrion/releases?per_page=100`, following
  pagination when present. Select the `qyrion/v*` release with the most recent
  `published_at`, excluding drafts and unpublished entries; report its version
  and beta status. Do not prefer an older stable release over a newer beta.
  Do not use `/releases/latest`: GitHub excludes prereleases there, and its
  404 does not mean no downloadable release exists.
- Match the host OS/architecture to an uploaded binary in that release's
  `assets` and download its returned `browser_download_url`. Do not construct
  a versioned URL or pin the example version from an earlier setup report.
  Download only the binary/archive; do not fetch `SHA256SUMS.txt`, calculate
  hashes, or require a separate signature check during plugin setup.
  Current release targets are macOS arm64, Linux x64, and Windows x64.
  Extract/install to a user-owned bin directory on PATH; inspect archives
  before extraction and respect any actual OS execution block.
- On Windows x64, select `qyrion-<version>-windows-x64.exe` and save it as
  `qyrion.exe`, for example under `%LOCALAPPDATA%\Programs\Qyrion`. Add that
  directory to the current process and user PATH without replacing existing
  entries, then run the installed executable's `--version` and
  `capabilities --json`. No checksum file or private repository access is
  needed for this public-binary installation.
- Use a bounded download timeout and at most one retry of the binary download.
  If it still fails, report the actual binary download error and release/asset
  name; continue independent MCP/SDK setup. Do not try checksum URLs or probe
  private source access to diagnose a public asset timeout. If the user obtains
  that official binary separately, continue installation from its local path.
- For an unsupported binary platform or an explicitly selected source
  checkout, use the verified `apps/qyrion` package from `QQyrus/df-ai-session`:
  `uv tool install --python 3.12 /absolute/checkout/apps/qyrion`.
  That source requires repository access. A plugin-only folder does not
  contain the CLI source; never invent a relative `apps/qyrion` path or install
  an unrelated PyPI package named `qyrion`.
- Upgrade an obsolete CLI through its existing trusted installation source
  (public-binary installs use the newest published release selection above),
  then repeat the capabilities handshake once. Preserve profiles and keys.
  A required feature still absent after upgrade is a compatibility blocker;
  do not loop on upgrades or fabricate a replacement command.
- The private `@qqyrus/qyrion` npm wrapper remains an alternative for users
  who already use it. Missing npm/GitHub access is not a reason to block a
  supported public-binary installation. Never request tokens in chat.

The release asset contract comes from
`apps/qyrion/dev-docs/release-process.md`; source installation requirements
come from `apps/qyrion/pyproject.toml`. uv tool installations use isolated
environments ([tool documentation](https://docs.astral.sh/uv/concepts/tools/)).
Release-list behavior is documented in
[GitHub's release API](https://docs.github.com/en/rest/releases/releases#list-releases).

## Credentials and completion

After dependencies are ready, use `references/credentials.md` (or the adjacent
`credentials.md` when reading this reference). Reuse the supplied/saved/default
private-file path. Ask for creation and a path only when no usable file exists;
never ask again for a path already provided and never read secrets into chat.
Run the bundled `qyrus_env.py configure` helper, which installs the pinned SDK,
derives the MCP endpoint, and remembers only the private-file path.

Then reconnect MCP, retrieve its guide and teams, resolve the user's team,
and verify Qyrion with helper-wrapped `sessions list --json` when in scope.
Do not create a session or test merely to verify setup. Report local dependency
readiness separately from each authenticated surface and any concrete blocker.
If the user requested another task, continue it after setup succeeds.
