"""Group, browse and search the Qyrus MCP tool list so a host sees six tools, not 310.

The hosted Qyrus MCP lists 310 tools. Offering all of them costs about 15K
tokens of tool descriptions before any input schema, and a model choosing among
310 near-identical names chooses worse. The bridge (`qyrus_mcp.py`) therefore
serves a few direct tools plus three disclosure tools backed by this module:

    qyrus_tools        browse by service and capability, or search by words
    qyrus_tool_schema  read the full description and input schema of 1-5 tools
    qyrus_tool_call    call any catalogue tool, arguments checked first

This is the plugin half of the contract in `docs/plans/qyrus-mcp-progressive-tools.md`
(section 2). The Assure Box runtime implements the same contract in
`assure_runtime/qyrus_catalogue.py`; the repo has no shared Python package, so
the two are kept equal by the fixture-driven spec tests, not by an import.

Pure logic only: no network, no fastmcp, no logging. It deliberately does not
rank by semantics (keywords and a short synonym table are enough for 310 names)
and does not decide which tools are always offered; the bridge does.

Example:
    >>> catalogue = Catalogue([CatalogueTool("qyrus_web_script_get", "Get a script.", {})])
    >>> catalogue.search("get script")[0].name
    'qyrus_web_script_get'
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import re
import time
from typing import Awaitable, Callable

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for

CORE_TOOLS = (
    "qyrus_account_capabilities_get",
    "qyrus_guide_get",
    "qyrus_teams_get_by_api_key",
)
SERVICES = ("web", "api", "orchestration", "tdm")
MISC_SERVICE = "misc"
OTHER_CAPABILITY = "other"
SEARCH_LIMIT = 15
SCHEMA_LIMIT = 5
INLINE_SCHEMA_LIMIT = 5
MAX_PROBLEMS_SHOWN = 3
CATALOGUE_TTL_SECONDS = 600

SERVICE_PURPOSES = {
    "web": "Web test automation: projects, modules, scripts, steps, suites, runs, reports, schedules",
    "api": "API testing: projects, scripts, workflows, suites, assertions, runs, reports, schedules",
    "orchestration": "Test orchestration: workflows, folders, run configs, schedules, runs",
    "tdm": "Test data management: API, database and manual data sources",
    MISC_SERVICE: "Tools whose names do not follow qyrus_<service>_<capability>_<action>",
}

# "logs" is a noun, not an action, but `qyrus_web_run_live_logs` has no verb and only reads.
READ_VERBS = frozenset({"get", "list", "search", "await", "preview", "describe", "download", "logs"})
DELETE_VERBS = frozenset({"delete", "disable"})

# Names whose third word is not the capability. Order matters: first prefix wins.
CAPABILITY_OVERRIDES = (
    ("qyrus_web_test_data_table_", "data"),
    ("qyrus_web_test_lab_", "lab"),
    ("qyrus_api_import_", "import"),
    ("qyrus_api_swagger_", "import"),
    ("qyrus_api_postman_", "import"),
    ("qyrus_orchestration_execute_multiple", "run"),
)
PLURAL_EXCEPTIONS = frozenset({"analytics"})
TDM_SOURCE_KINDS = frozenset({"api", "database", "manual"})

CAPABILITY_PURPOSES = {
    ("web", "script"): "Test scripts: create, edit, clone, move, execute, dry run, restore points",
    ("web", "step"): "Steps of a script: append, replace, update, heal, parameterize, export",
    ("web", "run"): "Runs: status, await, cancel, retry, history, reports, live logs, queue",
    ("web", "suite"): "Suites: create, edit, add scripts, execute, start runs",
    ("web", "function"): "Reusable functions: create, edit, clone, steps, import, export",
    ("web", "data"): "Test data tables and data profiles",
    ("web", "project"): "Projects: create, edit, clone, capabilities",
    ("web", "report"): "Run reports: summary, steps, screenshots, artifacts, share, search",
    ("web", "schedule"): "Schedules: create, edit, pause, resume, history, delete",
    ("web", "module"): "Modules inside a project: create, edit, disable, delete",
    ("web", "sprint"): "Sprints: create, start, complete, analytics",
    ("web", "environment"): "Environments: create, edit, clone, delete",
    ("web", "database"): "Database configurations used by tests",
    ("web", "variable"): "Global variables: set, list, delete, file upload",
    ("web", "runconfig"): "Run configuration for a script or suite: defaults, set, get, delete",
    ("web", "performance"): "Performance reports",
    ("web", "lab"): "Test lab: analytics, sync preview and apply",
    ("api", "workflow"): "API workflows: create, edit, inputs, outputs, bindings, validate, execute",
    ("api", "script"): "API scripts: create (also from curl), edit, clone, move, executions",
    ("api", "schedule"): "Schedules: create, pause, resume, history, delete",
    ("api", "report"): "Run reports: summary, detailed, share, download, delete",
    ("api", "project"): "Projects: create, edit, clone, delete",
    ("api", "suite"): "Suites: create, edit, clone, delete",
    ("api", "prerequisite"): "Prerequisites run before scripts: create, edit, data handler",
    ("api", "assertion"): "Assertions on responses: create, generate, edit, delete",
    ("api", "environment"): "Environments: create, edit, clone, delete",
    ("api", "certificate"): "Client certificates: get, update, delete",
    ("api", "run"): "Runs: status, await, cancel, retry",
    ("api", "variable"): "Variables: create, edit, delete",
    ("api", "import"): "Import APIs from Swagger, Postman or WSDL",
    ("orchestration", "workflow"): "Workflows: create, edit, clone, execute, validate, run status",
    ("orchestration", "folder"): "Folders of workflows: create, execute, clone, run results",
    ("orchestration", "schedule"): "Schedules: create, pause, resume, runs, delete",
    ("orchestration", "runconfig"): "Run configurations: create, edit, get, list, delete",
    ("orchestration", "run"): "Runs: await, cancel, pause, resume, history, results",
    ("tdm", "api source"): "API data sources: create, preview, import, mapping, delete",
    ("tdm", "database source"): "Database data sources: create, edit, list, delete",
    ("tdm", "manual source"): "Manual data sources: create, list, delete",
}

STOPWORDS = frozenset({
    "a", "an", "the", "of", "for", "to", "in", "on", "my", "me", "all", "and", "or", "with",
    "this", "that", "is", "it", "i", "want", "need", "please", "how", "do", "can", "from",
})
RECENCY_WORDS = frozenset({"latest", "last", "recent", "newest"})
START_WORDS = frozenset({"start", "begin", "launch", "trigger", "execute"})
# Query word -> other words that mean the same thing in tool names. Kept short
# on purpose: each pair is one the team's own wording differs on.
SYNONYMS = {
    "start": ("execute", "begin", "launch", "trigger"),
    "begin": ("start", "execute"),
    "launch": ("start", "execute"),
    "latest": ("last", "recent", "newest", "history"),
    "last": ("latest", "recent", "history"),
    "recent": ("latest", "last", "history"),
    "make": ("create", "add", "new"),
    "add": ("create", "append"),
    "remove": ("delete",),
    "show": ("get", "list", "read"),
    "view": ("get", "list", "read"),
    "find": ("search", "list"),
    "stop": ("cancel",),
    "edit": ("update", "set"),
    "change": ("update", "set"),
    "duplicate": ("clone", "copy"),
    "copy": ("clone",),
    "rerun": ("retry", "execute"),
}


@dataclass(frozen=True)
class CatalogueTool:
    """One upstream tool as the server lists it, plus nothing derived.

    Example:
        >>> CatalogueTool("qyrus_web_script_get", "Get one script.", {"type": "object"}).name
        'qyrus_web_script_get'
    """

    name: str
    description: str
    input_schema: dict


@dataclass(frozen=True)
class ToolEntry:
    """A catalogue tool with its service, capability and access kind.

    `access` is `read`, `write` or `delete`; it is shown to the model so a
    delete is chosen deliberately, and never used to refuse a call.
    """

    tool: CatalogueTool
    service: str
    capability: str
    access: str

    @property
    def name(self) -> str:
        """Return the upstream tool name."""
        return self.tool.name


def fold_plural(word: str) -> str:
    """Fold a plural noun to its singular (`scripts` to `script`).

    Example:
        >>> [fold_plural(w) for w in ("scripts", "capabilities", "analytics", "status")]
        ['script', 'capability', 'analytics', 'status']
    """
    if word in PLURAL_EXCEPTIONS or len(word) < 4:
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("ss", "us", "is")):
        return word
    return word[:-1] if word.endswith("s") else word


def split_name(name: str) -> tuple[str, str]:
    """Return (service, capability) for a tool name; core tools are `("core", "")`.

    A name that does not match `qyrus_<service>_<capability>_<action>` gets the
    `misc` service and the `other` capability so a new naming never hides a tool.

    Example:
        >>> split_name("qyrus_web_scripts_search")
        ('web', 'script')
        >>> split_name("qyrus_tdm_api_source_create")
        ('tdm', 'api source')
        >>> split_name("qyrus_guide_get")
        ('core', '')
    """
    if name in CORE_TOOLS:
        return "core", ""
    parts = name.split("_")
    if len(parts) < 4 or parts[0] != "qyrus" or parts[1] not in SERVICES:
        return MISC_SERVICE, OTHER_CAPABILITY
    service = parts[1]
    for prefix, capability in CAPABILITY_OVERRIDES:
        if name.startswith(prefix):
            return service, capability
    capability = fold_plural(parts[2])
    if service == "tdm" and capability in TDM_SOURCE_KINDS:
        capability += " source"
    return service, capability


def classify_access(name: str) -> str:
    """Return `read`, `write` or `delete` from the first verb in the name.

    The first token (after the service) that is a read or delete verb decides;
    a name with none is `write`, the cautious default. So `..._get_full` is
    read and `..._clone_to_module` is write.

    Example:
        >>> [classify_access(n) for n in ("qyrus_web_script_get_full", "qyrus_web_script_clone_to_module",
        ...                               "qyrus_web_steps_delete", "qyrus_api_import_wsdl_url_preview")]
        ['read', 'write', 'delete', 'read']
    """
    for token in name.split("_")[2:]:
        if token in READ_VERBS:
            return "read"
        if token in DELETE_VERBS:
            return "delete"
    return "write"


def short_description(description: str, limit: int = 110) -> str:
    """Return the first sentence of a description, on one line, cut at `limit`.

    Example:
        >>> short_description("Returns one script.\\nSecond sentence.")
        'Returns one script.'
    """
    flat = " ".join(description.split())
    first = re.split(r"(?<=[.!?])\s", flat, maxsplit=1)[0]
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def starts_a_run(name: str) -> bool:
    """Say whether a tool starts a test run (execute, or run start), dry runs excluded.

    Example:
        >>> starts_a_run("qyrus_web_suite_run_start"), starts_a_run("qyrus_web_script_dry_run_start")
        (True, False)
    """
    tokens = name.split("_")
    if "dry" in tokens:
        return False
    return "execute" in tokens or any(
        a == "run" and b == "start" for a, b in zip(tokens, tokens[1:])
    )


def _words(text: str) -> list[str]:
    """Lower-case words of `text` with plurals folded, stopwords kept out."""
    return [fold_plural(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]


def _normal_capability(text: str) -> str:
    """Normalise a requested capability (`API_source`, `scripts`) for comparison."""
    words = re.sub(r"[_\-\s]+", " ", text.strip().lower()).split()
    return " ".join(fold_plural(w) for w in words)


class Catalogue:
    """The grouped, searchable view of one `tools/list` result.

    Build it once per fetch; it is immutable afterwards. Every method returns
    model-facing text, so the bridge only has to hand strings to the host.

    Example:
        >>> catalogue = Catalogue([CatalogueTool("qyrus_web_script_get", "Get a script.", {})])
        >>> catalogue.overview().splitlines()[0]
        'Qyrus tools: 1 in total, 0 always offered directly. Services:'
    """

    def __init__(self, tools: list[CatalogueTool]) -> None:
        """Group `tools` by service and capability and classify read/write/delete."""
        self.entries: dict[str, ToolEntry] = {}
        for tool in tools:
            service, capability = split_name(tool.name)
            self.entries[tool.name] = ToolEntry(tool, service, capability, classify_access(tool.name))
        self._services: dict[str, dict[str, list[ToolEntry]]] = {}
        for entry in self.entries.values():
            if entry.service == "core":
                continue
            self._services.setdefault(entry.service, {}).setdefault(entry.capability, []).append(entry)

    def has(self, name: str) -> bool:
        """Say whether `name` is a tool the server listed."""
        return name in self.entries

    def misc_names(self) -> list[str]:
        """Return the tools whose names did not fit the naming shape."""
        return sorted(e.name for e in self.entries.values() if e.service == MISC_SERVICE)

    def overview(self) -> str:
        """List the services with tool counts (`qyrus_tools` with no arguments)."""
        core = [n for n in CORE_TOOLS if n in self.entries]
        lines = [f"Qyrus tools: {len(self.entries)} in total, {len(core)} always offered directly. Services:"]
        for service in self._ordered_services():
            count = sum(len(v) for v in self._services[service].values())
            lines.append(f"- {service} ({count}): {SERVICE_PURPOSES[service]}")
        if core:
            lines.append("Always offered directly (call them by name): " + ", ".join(core))
        lines.append('Next: qyrus_tools(service="<name>") for its capabilities, or qyrus_tools(query="<words>") to search.')
        return "\n".join(lines)

    def browse_service(self, service: str) -> str:
        """List one service's capabilities with counts and purposes."""
        key = self._find_service(service)
        if key is None:
            return self._unknown_service(service)
        capabilities = self._services[key]
        singles = sorted(c for c, items in capabilities.items() if len(items) == 1 or c == OTHER_CAPABILITY)
        multi = sorted((c for c in capabilities if c not in singles),
                       key=lambda c: (-len(capabilities[c]), c))
        total = sum(len(v) for v in capabilities.values())
        lines = [f'{key} — {total} tools. Capabilities (next: qyrus_tools(service="{key}", capability="<name>")):']
        starters = self._run_starters(key)
        for capability in multi:
            line = f"- {capability} ({len(capabilities[capability])}): {self._purpose(key, capability)}"
            if capability == "run" and starters:
                line += f". Starting runs: see also {', '.join(starters)}"
            lines.append(line)
        if "run" not in capabilities and starters:
            lines.append(f"- Starting runs: see {', '.join(starters)}")
        if singles:
            tools = sum(len(capabilities[c]) for c in singles)
            lines.append(f'- {OTHER_CAPABILITY} ({tools}): single-tool capabilities, listed with '
                         f'capability="{OTHER_CAPABILITY}": {", ".join(singles)}')
        return "\n".join(lines)

    def browse_capability(self, service: str, capability: str) -> str:
        """List one capability's tools; with five or fewer, include their schemas."""
        key = self._find_service(service)
        if key is None:
            return self._unknown_service(service)
        capabilities = self._services[key]
        wanted = _normal_capability(capability)
        if wanted == OTHER_CAPABILITY:
            items = sorted((e for c, v in capabilities.items() if len(v) == 1 or c == OTHER_CAPABILITY for e in v),
                           key=lambda e: e.name)
            label = OTHER_CAPABILITY
        else:
            label = next((c for c in capabilities
                          if _normal_capability(c) in (wanted, wanted + " source")), "")
            if not label:
                known = sorted(c for c, v in capabilities.items() if len(v) > 1 and c != OTHER_CAPABILITY)
                return (f'No capability "{capability}" in {key}. Capabilities: {", ".join(known)}, '
                        f'{OTHER_CAPABILITY}. Try qyrus_tools(query="<words>").')
            items = sorted(capabilities[label], key=lambda e: e.name)
        lines = [f"{key} / {label} — {len(items)} tools:"]
        lines += [self.one_line(e) for e in items]
        if len(items) <= INLINE_SCHEMA_LIMIT:
            lines.append("Schemas:")
            lines += [self.schema_block(e) for e in items]
        return "\n".join(lines)

    def search(self, query: str, service: str | None = None, capability: str | None = None) -> list[ToolEntry]:
        """Return up to 15 best keyword matches over names and descriptions.

        Each query word is a concept (itself plus `SYNONYMS`). See `_score` for
        the weights. A query that asks to start a run ("start a run", "launch
        a test run") additionally lifts every tool that starts runs, because
        starting runs is spread over six capabilities and no single word in
        their names says so.

        Example:
            >>> catalogue = Catalogue([
            ...     CatalogueTool("qyrus_api_assertion_create", "Create an assertion.", {}),
            ...     CatalogueTool("qyrus_api_assertion_delete", "Delete an assertion.", {})])
            >>> catalogue.search("create api assertion")[0].name
            'qyrus_api_assertion_create'
        """
        words = list(dict.fromkeys(_words(query)))
        if not words:
            return []
        modifiers = [w for w in words if w in RECENCY_WORDS]
        core = [w for w in words if w not in RECENCY_WORDS] or words
        starts_runs = "run" in words and bool(START_WORDS & set(words))
        scored = []
        for entry in self._scope(service, capability):
            score, matched = self._score(entry, core, modifiers)
            if starts_runs and starts_a_run(entry.name):
                score, matched = score + 5, max(matched, 1)
            if matched:
                scored.append((score, matched, entry))
        enough = -(-len(core) // 2)
        strong = [s for s in scored if s[1] >= enough] or scored
        strong.sort(key=lambda s: (-s[0], len(s[2].name), s[2].name))
        return [entry for _, _, entry in strong[:SEARCH_LIMIT]]

    def render_search(self, query: str, service: str | None = None, capability: str | None = None) -> str:
        """Format `search` results as one line per tool (`qyrus_tools` with `query`)."""
        found = self.search(query, service, capability)
        if not found:
            return f'No tool matches "{query}". Try fewer or different words, or qyrus_tools() to browse by service.'
        lines = [f'Best matches for "{query}" ({len(found)}):']
        lines += [self.one_line(e) for e in found]
        lines.append("Next: qyrus_tool_schema(names=[...]) to read arguments, then qyrus_tool_call.")
        return "\n".join(lines)

    def one_line(self, entry: ToolEntry) -> str:
        """Format a tool as `- name [access] — short description`."""
        return f"- {entry.name} [{entry.access}] — {short_description(entry.tool.description)}"

    def schema_block(self, entry: ToolEntry) -> str:
        """Format a tool's full description and input schema exactly as the server gave them."""
        schema = json.dumps(entry.tool.input_schema, separators=(",", ":"), ensure_ascii=False)
        return f"## {entry.name} [{entry.access}]\n{entry.tool.description}\nInput schema: {schema}"

    def schemas(self, names: list[str]) -> str:
        """Format the schema blocks for `names`, naming any that are unknown."""
        blocks, missing = [], []
        for name in names:
            entry = self.entries.get(name)
            if entry:
                blocks.append(self.schema_block(entry))
            else:
                missing.append(name)
        if missing:
            blocks.append("No such tool: " + ", ".join(missing) + ". Use qyrus_tools to find the exact name.")
        return "\n\n".join(blocks)

    def check_arguments(self, name: str, arguments: dict) -> str | None:
        """Return why `arguments` do not fit the tool's input schema, or None when they fit.

        Example:
            >>> schema = {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}}
            >>> catalogue = Catalogue([CatalogueTool("qyrus_web_script_get", "Get.", schema)])
            >>> catalogue.check_arguments("qyrus_web_script_get", {}), catalogue.check_arguments("qyrus_web_script_get", {"id": "a"})
            ("'id' is a required property", None)
        """
        schema = self.entries[name].tool.input_schema or {}
        try:
            validator = validator_for(schema, default=Draft202012Validator)(schema)
            errors = sorted(validator.iter_errors(arguments), key=lambda e: (_location(e), e.message))
        except Exception:
            return None  # A schema this library cannot read must not block a call the server may accept.
        if not errors:
            return None
        return "; ".join(_describe_error(e) for e in errors[:MAX_PROBLEMS_SHOWN])

    def _scope(self, service: str | None, capability: str | None) -> list[ToolEntry]:
        """Return the entries a search may rank, narrowed by service and capability."""
        key = self._find_service(service) if service else None
        entries = [e for e in self.entries.values() if e.service != "core" and (key is None or e.service == key)]
        if capability and key:
            wanted = _normal_capability(capability)
            entries = [e for e in entries if _normal_capability(e.capability) in (wanted, wanted + " source")]
        return entries

    def _score(self, entry: ToolEntry, core: list[str], modifiers: list[str]) -> tuple[int, int]:
        """Return (score, matched core-word count) of one tool for the query words.

        A core word scores 3 in the tool's name, 2 when only a synonym is in the
        name, 1 in the description. Every core word in the name adds 2, so
        `qyrus_web_runs_report_get` beats a tool that only mentions "run" in its
        text for "web run report". A recency word ("latest") adds 1 for a hit
        anywhere and never has to match.
        """
        name_words = set(_words(entry.name.replace("qyrus_", "", 1)))
        description_words = set(_words(entry.tool.description))
        score = matched = in_name = 0
        for word in core:
            alternatives = {word, *SYNONYMS.get(word, ())}
            if word in name_words:
                hit, in_name = 3, in_name + 1
            elif alternatives & name_words:
                hit, in_name = 2, in_name + 1
            else:
                hit = 1 if alternatives & description_words else 0
            score += hit
            matched += bool(hit)
        if in_name == len(core):
            score += 2
        for word in modifiers:
            alternatives = {word, *SYNONYMS.get(word, ())}
            score += 1 if alternatives & (name_words | description_words) else 0
        return score, matched

    def _find_service(self, service: str | None) -> str | None:
        """Return the catalogue's service key for a requested name, or None."""
        wanted = (service or "").strip().lower()
        return wanted if wanted in self._services else None

    def _ordered_services(self) -> list[str]:
        """Return the services present: the four named ones first, then misc."""
        return [s for s in (*SERVICES, MISC_SERVICE) if s in self._services]

    def _unknown_service(self, service: str) -> str:
        """Explain an unknown service name with the valid ones."""
        return f'No service "{service}". Services: {", ".join(self._ordered_services())}.'

    def _purpose(self, service: str, capability: str) -> str:
        """Return a capability's one-line purpose, or the actions its tools offer."""
        known = CAPABILITY_PURPOSES.get((service, capability))
        if known:
            return known
        actions = sorted({e.name.split("_")[-1] for e in self._services[service][capability]})
        return "Tools: " + ", ".join(actions)

    def _run_starters(self, service: str) -> list[str]:
        """Return the capabilities (other than `run`) with a tool that starts a run."""
        counts = {c: sum(starts_a_run(e.name) for e in items)
                  for c, items in self._services[service].items() if c != "run"}
        return sorted((c for c, n in counts.items() if n), key=lambda c: (-counts[c], c))[:6]


def _location(error) -> str:
    """Where in the arguments an error is: `project_id`, `filters.status`, or `(arguments)` for the whole object."""
    return ".".join(str(part) for part in error.absolute_path) or "(arguments)"


def _describe(error) -> str:
    """Say what is wrong without quoting the value that was given.

    The refusal is returned to the host and lands in transcripts and traces,
    and a value can be test data or a credential, so the text is built from the
    failing keyword and the schema's own rule, never `error.message` (which
    quotes the instance). The wording matches the runtime's `qyrus_catalogue`.

    Example:
        >>> [_describe(e) for e in Draft202012Validator({"type": "integer"}).iter_errors("secret-text")]
        ['must be of type integer']
    """
    keyword, wanted = error.validator, error.validator_value
    if keyword in ("required", "additionalProperties", "unevaluatedProperties"):
        return error.message  # names the property, never its value
    if keyword == "type":
        return f"must be of type {wanted if isinstance(wanted, str) else ' or '.join(map(str, wanted))}"
    if keyword == "enum":
        return f"must be one of {json.dumps(wanted, ensure_ascii=False)[:200]}"
    return f"does not satisfy {keyword}: {json.dumps(wanted, ensure_ascii=False, default=str)[:80]}"


def _describe_error(error) -> str:
    """Format one schema violation as `location: what is wrong`, or just the text for the whole object."""
    location = _location(error)
    text = _describe(error)
    return text if location == "(arguments)" else f"{location}: {text}"


class CatalogueCache:
    """Hold one Catalogue for ten minutes and refresh it when asked.

    The fetch function is injected so the cache is testable without a server.
    One lock keeps simultaneous callers to a single `tools/list`.

    Example:
        >>> import asyncio
        >>> async def fetch(): return [CatalogueTool("qyrus_web_script_get", "Get.", {})]
        >>> asyncio.run(CatalogueCache(fetch).get()).has("qyrus_web_script_get")
        True
    """

    def __init__(self, fetch: Callable[[], Awaitable[list[CatalogueTool]]],
                 ttl_seconds: float = CATALOGUE_TTL_SECONDS,
                 clock: Callable[[], float] = time.monotonic) -> None:
        """Remember how to fetch the tool list, how long it stays fresh and the clock."""
        self._fetch, self._ttl, self._clock = fetch, ttl_seconds, clock
        self._catalogue: Catalogue | None = None
        self._fetched_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, refresh: bool = False) -> Catalogue:
        """Return the cached catalogue, fetching when empty, expired or `refresh` is set."""
        async with self._lock:
            expired = self._clock() - self._fetched_at >= self._ttl
            if refresh or self._catalogue is None or expired:
                self._catalogue = Catalogue(await self._fetch())
                self._fetched_at = self._clock()
            return self._catalogue

    async def get_with_tool(self, name: str) -> Catalogue | None:
        """Return a catalogue that has `name`, refreshing once if the cached one lacks it.

        Returns None when the name is still unknown after the refresh.
        """
        catalogue = await self.get()
        if catalogue.has(name):
            return catalogue
        catalogue = await self.get(refresh=True)
        return catalogue if catalogue.has(name) else None
