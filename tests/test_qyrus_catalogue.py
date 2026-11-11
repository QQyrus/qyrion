"""Spec for the Qyrus tool catalogue, driven by the recorded 310-tool list.

The fixture (`tests/fixtures/qyrus-mcp/tools-2026-10-21.json` at the repository
root) is the live `tools/list` of 2026-10-21 with descriptions cut to 200
characters and no input schemas, so the few schemas these tests need are
written inline. The Assure Box runtime implements the same contract
(`docs/plans/qyrus-mcp-progressive-tools.md`, section 2) against the same
fixture; if a case here changes, change it there too.
"""

import asyncio
from collections import Counter
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from qyrus_catalogue import (  # noqa: E402
    CORE_TOOLS, Catalogue, CatalogueCache, CatalogueTool, classify_access, split_name,
)

FIXTURE = Path(__file__).resolve().parents[3] / "tests/fixtures/qyrus-mcp/tools-2026-10-21.json"
pytestmark = pytest.mark.skipif(
    not FIXTURE.exists(), reason="the recorded tool list lives in the development repository, not the public mirror")


@pytest.fixture(scope="module")
def recorded():
    """Return the recorded tools as `CatalogueTool`s with empty input schemas."""
    listed = json.loads(FIXTURE.read_text(encoding="utf-8"))["tools"]
    return [CatalogueTool(t["name"], t["description"], {}) for t in listed]


@pytest.fixture(scope="module")
def catalogue(recorded):
    """Return the catalogue built from the recorded tools."""
    return Catalogue(recorded)


def names_of(entries):
    """Return the tool names of search results, in rank order."""
    return [entry.name for entry in entries]


def test_the_recording_has_310_tools(recorded):
    assert len(recorded) == 310


def test_every_name_is_grouped_into_a_service_and_nothing_lands_in_misc(catalogue):
    services = Counter(entry.service for entry in catalogue.entries.values())
    assert services == {"web": 147, "api": 101, "orchestration": 46, "tdm": 13, "core": 3}
    assert catalogue.misc_names() == []


@pytest.mark.parametrize("service,expected", [
    ("web", {"script": 19, "step": 15, "run": 14, "suite": 11, "function": 10, "data": 13, "project": 8,
             "report": 8, "schedule": 7, "module": 6, "sprint": 6, "environment": 5, "database": 4,
             "variable": 4, "runconfig": 4, "lab": 3, "performance": 2}),
    ("api", {"workflow": 23, "script": 13, "schedule": 8, "report": 7, "project": 6, "suite": 6,
             "prerequisite": 6, "assertion": 5, "environment": 5, "certificate": 4, "run": 4, "variable": 3,
             "import": 5}),
    ("orchestration", {"workflow": 17, "folder": 8, "schedule": 7, "runconfig": 5, "run": 4}),
    ("tdm", {"api source": 6, "database source": 4, "manual source": 3}),
])
def test_capability_counts_match_the_plan_with_plurals_folded_and_overrides_applied(recorded, service, expected):
    counts = Counter(split_name(t.name)[1] for t in recorded if split_name(t.name)[0] == service)
    assert {capability: n for capability, n in counts.items() if capability in expected} == expected


def test_core_tools_are_never_grouped(catalogue):
    assert [n for n, e in catalogue.entries.items() if e.service == "core"] == list(CORE_TOOLS)
    assert "qyrus_guide_get" not in catalogue.browse_service("web")


@pytest.mark.parametrize("name,service,capability", [
    ("qyrus_web_test_data_table_get", "web", "data"),
    ("qyrus_web_test_data_table_import", "web", "data"),
    ("qyrus_web_data_profile_create", "web", "data"),
    ("qyrus_web_test_lab_sync_apply", "web", "lab"),
    ("qyrus_web_lab_analytics_get", "web", "lab"),
    ("qyrus_api_import_selected_apis", "api", "import"),
    ("qyrus_api_import_wsdl_url_preview", "api", "import"),
    ("qyrus_api_swagger_import_file", "api", "import"),
    ("qyrus_api_postman_import_url", "api", "import"),
    ("qyrus_orchestration_execute_multiple", "orchestration", "run"),
    ("qyrus_tdm_api_source_create", "tdm", "api source"),
    ("qyrus_tdm_api_mapping_save", "tdm", "api source"),
    ("qyrus_tdm_database_sources_list", "tdm", "database source"),
    ("qyrus_tdm_manual_source_delete", "tdm", "manual source"),
    ("qyrus_web_scripts_search", "web", "script"),
    ("qyrus_web_runs_history_list", "web", "run"),
    ("qyrus_api_analytics_summary_get", "api", "analytics"),
    ("qyrus_api_workspace_statistics_get", "api", "workspace"),
])
def test_each_override_and_plural_fold_lands_in_the_documented_capability(name, service, capability):
    assert split_name(name) == (service, capability)


ODD_NAMES = {
    # Core tools, no service.
    "qyrus_account_capabilities_get": ("core", "", "read"),
    "qyrus_guide_get": ("core", "", "read"),
    "qyrus_teams_get_by_api_key": ("core", "", "read"),
    # A verb where the capability goes.
    "qyrus_api_import_selected_apis": ("api", "import", "write"),
    "qyrus_api_import_wsdl_url_preview": ("api", "import", "read"),
    "qyrus_orchestration_execute_multiple": ("orchestration", "run", "write"),
    # Words after the action: the first verb decides read, write or delete.
    "qyrus_api_script_get_full": ("api", "script", "read"),
    "qyrus_api_workflow_get_full": ("api", "workflow", "read"),
    "qyrus_orchestration_workflow_get_full": ("orchestration", "workflow", "read"),
    "qyrus_api_script_set_full": ("api", "script", "write"),
    "qyrus_api_postman_import_url": ("api", "import", "write"),
    "qyrus_api_swagger_import_url": ("api", "import", "write"),
    "qyrus_api_swagger_import_file": ("api", "import", "write"),
    "qyrus_api_script_create_from_curl": ("api", "script", "write"),
    "qyrus_api_report_download_html": ("api", "report", "read"),
    "qyrus_orchestration_run_report_generate_pdf": ("orchestration", "run", "write"),
    "qyrus_web_run_artifact_generate_pdf": ("web", "run", "write"),
    "qyrus_web_scripts_clone_to_module": ("web", "script", "write"),
    "qyrus_web_scripts_move_to_module": ("web", "script", "write"),
}


def test_the_19_names_that_do_not_fit_the_shape_are_grouped_and_classified_as_documented(catalogue):
    assert len(ODD_NAMES) == 19
    for name, (service, capability, access) in ODD_NAMES.items():
        entry = catalogue.entries[name]
        assert (entry.service, entry.capability, entry.access) == (service, capability, access), name


@pytest.mark.parametrize("name,access", [
    ("qyrus_web_script_get", "read"), ("qyrus_web_scripts_search", "read"), ("qyrus_web_run_await", "read"),
    ("qyrus_web_script_describe", "read"), ("qyrus_web_test_lab_sync_preview", "read"),
    ("qyrus_web_report_download_html", "read"), ("qyrus_web_project_clone_status_get", "read"),
    ("qyrus_web_steps_delete", "delete"), ("qyrus_web_module_disable", "delete"),
    ("qyrus_web_script_restore_point_delete", "delete"),
    ("qyrus_web_script_create", "write"), ("qyrus_web_run_cancel", "write"),
    ("qyrus_web_script_clone", "write"), ("qyrus_web_run_live_logs", "read"),
])
def test_read_write_delete_comes_from_the_first_verb_and_defaults_to_write(name, access):
    assert classify_access(name) == access


def test_read_write_delete_totals_over_the_recording(catalogue):
    counts = Counter(entry.access for entry in catalogue.entries.values())
    assert counts == {"read": 128, "write": 141, "delete": 41}


def test_a_name_outside_the_shape_goes_under_misc_other_and_is_still_found():
    catalogue = Catalogue([CatalogueTool("qyrus_web_script_get", "Get a script.", {}),
                           CatalogueTool("qyrus_brand_new_thing", "Does a new thing.", {})])
    assert catalogue.misc_names() == ["qyrus_brand_new_thing"]
    assert "- misc (1):" in catalogue.overview()
    assert "qyrus_brand_new_thing [write]" in catalogue.browse_capability("misc", "other")
    assert names_of(catalogue.search("new thing")) == ["qyrus_brand_new_thing"]


def test_overview_lists_the_four_services_with_counts_and_the_direct_tools(catalogue):
    lines = catalogue.overview().splitlines()
    assert lines[0] == "Qyrus tools: 310 in total, 3 always offered directly. Services:"
    assert [line.split(":")[0] for line in lines[1:5]] == ["- web (147)", "- api (101)", "- orchestration (46)", "- tdm (13)"]
    assert "qyrus_guide_get" in lines[5]


def test_service_view_lists_capabilities_largest_first_with_one_tool_capabilities_under_other(catalogue):
    view = catalogue.browse_service("web")
    capability_lines = [line for line in view.splitlines() if line.startswith("- ")]
    assert capability_lines[0].startswith("- script (19):")
    assert capability_lines[-1].startswith("- other (8):")
    assert "assertion, auth, batch, browser" in capability_lines[-1]
    assert not any(line.startswith("- batch") for line in capability_lines)


def test_run_line_points_at_the_other_capabilities_that_start_runs(catalogue):
    run_line = next(l for l in catalogue.browse_service("web").splitlines() if l.startswith("- run "))
    assert "Starting runs: see also" in run_line and all(c in run_line for c in ("script", "suite", "batch"))
    api_run = next(l for l in catalogue.browse_service("api").splitlines() if l.startswith("- run "))
    assert "test" in api_run.split("see also")[1] and "workflow" in api_run.split("see also")[1]


def test_capability_view_lists_every_tool_with_access_and_gives_schemas_only_for_five_or_fewer(catalogue):
    big = catalogue.browse_capability("web", "script")
    assert big.splitlines()[0] == "web / script — 19 tools:"
    assert "- qyrus_web_script_get [read] — " in big and "Input schema:" not in big
    small = catalogue.browse_capability("web", "lab")
    assert "Schemas:" in small and small.count("Input schema:") == 3


def test_capability_names_accept_plural_and_the_tdm_short_form(catalogue):
    assert catalogue.browse_capability("web", "scripts").startswith("web / script — 19 tools:")
    assert catalogue.browse_capability("tdm", "api").startswith("tdm / api source — 6 tools:")
    assert catalogue.browse_capability("tdm", "database_source").startswith("tdm / database source — 4 tools:")


def test_other_lists_the_single_tool_capabilities(catalogue):
    view = catalogue.browse_capability("orchestration", "other")
    assert view.splitlines()[0] == "orchestration / other — 5 tools:"
    assert "qyrus_orchestration_tags_list" in view and "qyrus_orchestration_items_move" in view


def test_unknown_service_and_capability_say_what_is_valid(catalogue):
    assert catalogue.browse_service("mobile") == 'No service "mobile". Services: web, api, orchestration, tdm.'
    message = catalogue.browse_capability("web", "teleport")
    assert 'No capability "teleport" in web.' in message and "script" in message and "other" in message


def test_query_latest_web_run_report_finds_the_report_tools_first(catalogue):
    found = names_of(catalogue.search("latest web run report"))
    assert found[0] == "qyrus_web_runs_report_get"
    assert {"qyrus_web_report_summary_get", "qyrus_web_reports_search", "qyrus_web_runs_history_list"} <= set(found)
    assert not [n for n in found if n.startswith(("qyrus_api_", "qyrus_orchestration_"))]


def test_query_create_api_assertion_ranks_the_exact_tool_first(catalogue):
    assert names_of(catalogue.search("create api assertion"))[0] == "qyrus_api_assertion_create"


def test_query_pause_schedule_finds_all_three_services_pause_tools_first(catalogue):
    assert set(names_of(catalogue.search("pause schedule"))[:3]) == {
        "qyrus_api_schedule_pause", "qyrus_web_schedule_pause", "qyrus_orchestration_schedule_pause"}


def test_query_start_a_run_finds_every_tool_that_starts_a_run(catalogue):
    found = set(names_of(catalogue.search("start a run")))
    assert {"qyrus_api_test_execute", "qyrus_web_batch_execute", "qyrus_web_script_execute",
            "qyrus_web_suite_run_start", "qyrus_orchestration_execute_multiple",
            "qyrus_orchestration_workflow_execute"} <= found


def test_query_returns_at_most_fifteen_and_nothing_for_gibberish_or_stopwords(catalogue):
    assert len(catalogue.search("run")) == 15
    assert catalogue.search("the a of") == []
    assert "No tool matches" in catalogue.render_search("zzzzqq xxyyzz")


def test_query_can_be_narrowed_to_a_service_and_capability(catalogue):
    found = catalogue.search("pause", service="orchestration", capability="schedule")
    assert names_of(found) == ["qyrus_orchestration_schedule_pause"] or all(
        n.startswith("qyrus_orchestration_schedule_") for n in names_of(found))


SCHEMA = {
    "type": "object",
    "required": ["script_id"],
    "properties": {"script_id": {"type": "string"}, "limit": {"type": "integer", "minimum": 1}},
}


def one_tool_catalogue():
    """Return a catalogue with a single tool that has a real input schema."""
    return Catalogue([CatalogueTool("qyrus_web_script_get", "Returns one script.", SCHEMA)])


def test_matching_arguments_pass_the_schema_check():
    assert one_tool_catalogue().check_arguments("qyrus_web_script_get", {"script_id": "s", "limit": 2}) is None


@pytest.mark.parametrize("arguments,expected", [
    ({}, "'script_id' is a required property"),
    ({"script_id": 5}, "script_id: must be of type string"),
    ({"script_id": "s", "limit": 0}, "limit: does not satisfy minimum: 1"),
])
def test_a_schema_mismatch_names_the_field_and_the_problem(arguments, expected):
    assert expected in one_tool_catalogue().check_arguments("qyrus_web_script_get", arguments)


SECRET = "sk-live-4f9a-secret-value"
GUARDED_SCHEMA = {
    "type": "object",
    "required": ["amount"],
    "additionalProperties": False,
    "properties": {
        "amount": {"type": "integer"},
        "mode": {"enum": ["fast", "slow"]},
        "code": {"type": "string", "pattern": "^[0-9]+$", "minLength": 2, "maxLength": 4},
        "tags": {"type": "array", "items": {"type": "integer"}},
        "nested": {"type": "object", "properties": {"limit": {"type": "integer", "maximum": 5}}},
    },
}


@pytest.mark.parametrize("arguments,expected", [
    ({"amount": SECRET}, "amount: must be of type integer"),
    ({"amount": 1, "mode": SECRET}, 'mode: must be one of ["fast", "slow"]'),
    ({"amount": 1, "code": SECRET}, "code: does not satisfy pattern: \"^[0-9]+$\""),
    ({"amount": 1, "code": "1"}, "code: does not satisfy minLength: 2"),
    ({"amount": 1, "tags": [1, SECRET]}, "tags.1: must be of type integer"),
    ({"amount": 1, "nested": {"limit": 99999}}, "nested.limit: does not satisfy maximum: 5"),
    ({"amount": 1, SECRET: "x"}, "Additional properties are not allowed"),
    ({SECRET: 1}, "'amount' is a required property"),
])
def test_a_mismatch_is_worded_from_the_path_and_the_rule_and_never_quotes_the_value(arguments, expected):
    problem = Catalogue([CatalogueTool("qyrus_web_pay", "Pays.", GUARDED_SCHEMA)]).check_arguments(
        "qyrus_web_pay", arguments)
    assert expected in problem
    assert "99999" not in problem
    if SECRET not in arguments:  # an unexpected property's NAME is reported; a value never is
        assert SECRET not in problem


def test_a_schema_the_validator_cannot_read_never_blocks_a_call():
    catalogue = Catalogue([CatalogueTool("qyrus_web_script_get", "x", {"type": "nonsense"})])
    assert catalogue.check_arguments("qyrus_web_script_get", {"anything": 1}) is None


def test_schema_text_carries_the_full_description_and_schema_exactly():
    text = one_tool_catalogue().schemas(["qyrus_web_script_get", "qyrus_web_script_gett"])
    assert text.startswith("## qyrus_web_script_get [read]\nReturns one script.\nInput schema: ")
    assert json.loads(text.split("Input schema: ")[1].splitlines()[0]) == SCHEMA
    assert text.endswith("No such tool: qyrus_web_script_gett. Use qyrus_tools to find the exact name.")


class FakeUpstream:
    """A tool list the test can change between fetches, counting how often it is read."""

    def __init__(self, names):
        """Start with the tools called `names`."""
        self.names, self.fetches = names, 0

    async def fetch(self):
        """Return the current tools, as one `tools/list` would."""
        self.fetches += 1
        return [CatalogueTool(name, "Does it.", {}) for name in self.names]


class FakeClock:
    """A clock the test moves by hand."""

    def __init__(self):
        """Start at zero seconds."""
        self.now = 0.0

    def __call__(self):
        """Return the current fake time."""
        return self.now


def test_the_catalogue_is_fetched_once_and_cached_for_ten_minutes():
    upstream, clock = FakeUpstream(["qyrus_web_script_get"]), FakeClock()
    cache = CatalogueCache(upstream.fetch, clock=clock)

    async def body():
        await cache.get()
        clock.now = 599
        await cache.get()
        assert upstream.fetches == 1
        clock.now = 600
        await cache.get()
        assert upstream.fetches == 2

    asyncio.run(body())


def test_an_unknown_name_refreshes_exactly_once_before_failing():
    upstream = FakeUpstream(["qyrus_web_script_get"])
    cache = CatalogueCache(upstream.fetch)

    async def body():
        assert await cache.get_with_tool("qyrus_web_script_gett") is None
        assert upstream.fetches == 2  # the first load, then one refresh
        assert await cache.get_with_tool("qyrus_web_script_get") is not None
        assert upstream.fetches == 2  # a known name never refreshes

    asyncio.run(body())


def test_a_renamed_tool_is_found_after_the_refresh_and_the_old_name_stops_working():
    upstream = FakeUpstream(["qyrus_web_script_get"])
    cache = CatalogueCache(upstream.fetch)

    async def body():
        assert await cache.get_with_tool("qyrus_web_script_get") is not None
        upstream.names = ["qyrus_web_script_read"]  # the server renamed it inside the cache window
        renamed = await cache.get_with_tool("qyrus_web_script_read")
        assert renamed is not None and not renamed.has("qyrus_web_script_get")
        assert await cache.get_with_tool("qyrus_web_script_get") is None

    asyncio.run(body())
