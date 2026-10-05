# SDK calls and boundaries

Scope: public `qyrusai` Python package, verified against 1.0.9 from
[PyPI](https://pypi.org/project/qyrusai/). The published wheel is the source
for signatures; some longer PyPI examples mix sync/async calls.

Run scripts with the shared loader so the same private `X-API-Key` reaches
`QYRUS_API_KEY`. The helper automatically installs the pinned SDK if missing and reuses its
uv-managed isolated environment when available. From the plugin root:

```bash
python3 scripts/qyrus_env.py sdk -- /absolute/path/generate.py
```

Example `generate.py` (input is an authorized, sanitized local text file):

```python
"""Generate candidate scenarios; execution and persistence are separate steps."""
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from qyrusai import SyncQyrusAI

def main():
    """Generate from work-item text using the shared key and Qyrus tenant URL."""
    client = SyncQyrusAI(api_key=os.environ["QYRUS_API_KEY"])
    result = client.nova.generate_scenarios.from_description(
        Path("requirements.txt").read_text(),
        app_url=os.environ["QYRION_APP_URL"],
    )
    Path("scenarios.json").write_text(json.dumps(result.scenarios, indent=2))

if __name__ == "__main__":
    try:
        with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
            main()
    except Exception:
        raise SystemExit("QyrusAI generation failed; inspect configuration and service availability.") from None
```

Both `SyncQyrusAI(api_key=...)` and `AsyncQyrusAI(api_key=...)` take the key
only. Do not pass `base_url`, `application_url`, or gateway Authorization to
the constructor. Version 1.0.9 derives the gateway from the key's environment
segment internally. Use an admin-issued key and confirm it belongs to the
same Qyrus environment as the selected MCP endpoint and Qyrion app URL.
Never print or parse that key in agent-visible commands.

Nova's `generate_scenarios.from_description(user_description, *, app_url,
module_id, module_name, project_name)` accepts optional context values;
resolve real identifiers before supplying them. `app_url` is Qyrus tenant
context, not the website under test. The compatibility alias
`nova.from_description.create(...)` exists. The result exposes `.scenarios`;
an empty result is not successful test coverage. Async methods need `await`.

| Need | SDK surface; inspect signature before building payload |
|---|---|
| Scenario generation | `nova.generate_scenarios.from_description(...)` |
| Steps for scenarios | `nova.generate_steps.create(...)` |
| Synthetic data | `data_amplifier.amplify(data, data_count)` |
| API spec proposal | `api_builder.build(email=..., user_description=...)` |
| Response assertions | `api_assertions.headers/jsonbody/jsonpath/jsonschema.create(...)` |
| Tests from an image | `vision_nova.generate_test.generate(image_url)` |
| Image accessibility | `vision_nova.verify_accessibility.verify(image_url)` |
| Explicit RAG/MCP evaluation request | `llm_evaluator.evaluator.evaluate_rag/evaluate_mcp/evaluate_batch(...)` |

The SDK cannot establish work-management access by itself. Its direct Jira,
Rally, and Azure methods accept separate credentials; prefer already-connected
agent tools plus `from_description` to avoid copying those credentials.
SDK generation does not create durable Aegis assets: use the live MCP guide
to translate, validate, save, run, and verify when requested.

Version 1.0.9's HTTP helper prints raw exception details in some failure
paths. Suppress SDK stdout/stderr around calls as above and emit only your
sanitized application result. Catching the final exception alone does not
prevent those earlier prints. Bound the command with the host's subprocess
timeout; on timeout, treat any remotely queued generation as unconfirmed and
reconcile before starting another request.
