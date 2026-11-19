# Claude Code registration and activation

For normal installation, use the public repository's bundled marketplace:

```bash
claude plugin marketplace add QQyrus/qyrion
claude plugin install qyrusai-assure@qyrusai-assure --scope user
claude plugin list --json
claude plugin details qyrusai-assure
```

First inspect existing registrations with `claude plugin marketplace list`
and `claude plugin list --json`. Reuse a verified matching installation;
do not duplicate it or change unrelated marketplaces. Both the plugin ID and
marketplace name are `qyrusai-assure`. Codex's
personal marketplace uses a different schema and is not a Claude catalog.

The catalog lives at `<plugin-root>/.claude-plugin/marketplace.json` and its
plugin source is `./`. The public mirror copies this entire plugin root.
If the public revision does not contain the catalog yet, report that publication
is pending. When the user supplied a local package or requested development
setup, validate its bundled catalog with `claude plugin validate`, then use
`claude plugin marketplace add /absolute/real/plugin-root` instead. Resolve
symlinks first (for example, `Path(path).expanduser().resolve()` in Python).
Never create a parent/project marketplace to work around an escaping symlink,
modify Git excludes, or replace an existing symlink/checkout to force an install.
Local sources load development files in place; make that explicit. A one-session
`claude --plugin-dir /absolute/real/plugin-root` is also a development option.

The bundled catalog's `renames` map changes `qyrion-agent-plugin` to
`qyrusai-assure` within the `qyrusai-assure` marketplace. Refresh the catalog,
then run `claude plugin install qyrusai-assure@qyrusai-assure --scope user`
to populate the new cache (use the original scope when different). This map
does not migrate a different marketplace such as `personal` or another host.
If the installed Claude version does not support rename maps, install and
verify the new ID before disabling the old entry through the host tooling.

For an existing `qyrion-agent-plugin@personal`, preserve it until a replacement
is installed and verified. If the user requests migration to the bundled
marketplace, validate the replacement and its nine skills plus `qyrus` MCP
definition, then disable only the old Qyrion entry in its original scope so
two copies do not load. Preserve unrelated personal entries, the shared
credentials and working Qyrion installation. Do not remove the whole personal
marketplace or its files as incidental cleanup. If details are ambiguous
while both copies are installed, inspect the exact replacement path reported
by `plugin list --json` before disabling the old copy.

Read this setup skill and its dependency/credential references directly from
the verified installed package during the original request, even before
Claude auto-discovers the skills. Complete available checks through the helper
and launcher. A launcher connection proves that process can reach Qyrus;
it does not prove the current Claude session has reloaded its MCP tools.
Report any pending host activation separately. If needed, tell the user to
run `/reload-plugins` or open a new session, then continue with their task;
do not instruct them to repeat completed setup. Never claim tests ran merely
because MCP discovery and the session list succeeded.

For updates, refresh the marketplace, then the installed plugin:

```bash
claude plugin marketplace update qyrusai-assure
claude plugin update qyrusai-assure@qyrusai-assure
```

Follow Claude's activation message. Preserve a working user-selected source
CLI even if its version differs from a release binary; `capabilities --json`
and the requested read-only service check determine readiness.

Sources: [Claude marketplace creation](https://code.claude.com/docs/en/plugin-marketplaces)
and [hosting and updates](https://code.claude.com/docs/en/plugins/host-marketplace).
