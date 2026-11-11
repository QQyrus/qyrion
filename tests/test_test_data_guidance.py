"""Keep packaged test-data guidance consistent with its canonical shared source."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_test_data_workflow_is_embedded_in_every_skill():
    """Each distributed skill can read the workflow without cross-skill paths."""
    canonical = (ROOT / "shared" / "test-data-workflows.md").read_text(encoding="utf-8")
    for skill in (ROOT / "skills").iterdir():
        if skill.is_dir():
            assert (skill / "references" / "test-data-workflows.md").read_text(encoding="utf-8") == canonical


def test_workflow_requires_capabilities_and_explicit_replacements():
    """The plugin cannot assume support or substitute recreated identities silently."""
    guidance = (ROOT / "shared" / "test-data-workflows.md").read_text(encoding="utf-8")
    for feature in ("project_references", "project_variable_management", "test_dataset_management", "rerun_test_data_preflight"):
        assert feature in guidance
    for tool in ("qyrion_capabilities", "qyrion_export_test_dataset", "qyrion_project_test_data_preview", "qyrion_save_test_data_preference"):
        assert tool in guidance
    assert "explicit user confirmation" in guidance
    assert "never resolve them in the plugin" in guidance
    assert "Ask the user to choose" in guidance


def test_host_manifest_patch_versions_match():
    """All host packages advertise the same source version."""
    versions = {json.loads((ROOT / host / "plugin.json").read_text(encoding="utf-8"))["version"]
                for host in (".claude-plugin", ".codex-plugin", ".cursor-plugin")}
    assert versions == {"0.4.0"}


def test_distributed_event_contract_preserves_advisory_evidence():
    """JSONL consumers must not equate completed execution with passed checks."""
    contract = (ROOT / "shared" / "event-contract.md").read_text(encoding="utf-8")
    for field in ("payload.replay_status", "payload.output.advisory", "unverifiable", '"is_error": false'):
        assert field in contract
    assert "passed, failed and unverified counts separately" in contract
    assert "completed status or a zero exit code" in contract
    for name in ("test-data-workflows.md", "session-workflows.md"):
        guidance = (ROOT / "shared" / name).read_text(encoding="utf-8")
        assert "event-contract.md" in guidance and "unverified" in guidance
    for skill in (ROOT / "skills").iterdir():
        if skill.is_dir():
            assert (skill / "references" / "event-contract.md").read_text(encoding="utf-8") == contract


def test_legacy_dataset_guidance_keeps_json_transport_separate():
    """The plugin must not send legacy datasets through the reference-only selector."""
    guidance = (ROOT / "shared" / "test-data-workflows.md").read_text(encoding="utf-8")
    assert "legacy arbitrary-JSON execution variables" in guidance
    assert "separate from the reference-based `--test-dataset`" in guidance
    assert "compatibility alias for `--test-dataset`" not in guidance
