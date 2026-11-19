# QyrusAI Assure for Claude

QyrusAI Assure connects Claude to Qyrus for web, mobile, and API testing.
Use the bundled skills to turn a requirement or bug into a test, run it on
Qyrus, and collect evidence. The plugin includes the Qyrus MCP bridge,
Qyrion session workflows, and guidance for the Qyrus Python SDK.

## Install and connect

- For a Claude organization marketplace, upload the release ZIP under
  **Organization settings → Plugins & skills → Add → Upload a plugin**.
- For a local Claude Code session, run
  `claude --plugin-dir /absolute/path/to/the/extracted/plugin`.
- For installation from the GitHub marketplace, see the
  [QyrusAI Assure setup guide](https://github.com/QQyrus/qyrion#claude-code).

Once installed, ask Claude to **Set up QyrusAI Assure**. You need the Qyrus
application URL for your tenant and a Qyrus API key. Copy the bundled
`.env.example` to a private file outside the plugin directory, replace
the placeholders, and give Claude the path to that file. The local MCP bridge
uses Python and uv. It sends the API key to the Qyrus MCP endpoint derived
from the tenant URL.

See the [installation page and API-key tutorial](https://qqyrus.github.io/qyrion/),
the [source repository](https://github.com/QQyrus/qyrion), and
[Qyrus support](https://www.qyrus.com/contact-us/).
