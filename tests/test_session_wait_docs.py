"""The plugin tells agents to watch several sessions with one `qyrion sessions wait --any`, gated on its feature flag.

Why: an agent that waits on its sessions one at a time leaves a question another session asks unseen until its
current wait ends (Assure Box `cnv_444d7ec7038a4d21`, 2026-10-22). The CLI gained `sessions wait --any` with the
`session_wait_any` capability; these checks keep the skill, the shared contract and every skill's embedded copy saying
so, so an agent never relies on the command without the gate or falls back to waiting on one session while another asks.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_DOCS = ("cli-contract.md", "parallel-orchestration.md")


def text(path: Path) -> str:
    """A doc's text with Windows line endings normalised, so the checks pass on any checkout."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def flat(value: str) -> str:
    """The text on one line, so a check does not depend on where the Markdown wraps."""
    return " ".join(value.split())


def test_the_cli_skill_waits_on_several_sessions_with_one_wait_behind_its_feature_flag():
    skill = flat(text(ROOT / "skills" / "qyrion-cli" / "SKILL.md"))

    assert "qyrion sessions wait --any <run_a> <run_b> --timeout 240 --json" in skill
    assert "gated on `session_wait_any`" in skill
    assert "Never block on one session while another may be asking." in skill


def test_the_contract_gates_the_wait_and_says_what_wakes_it_and_what_to_watch_next():
    contract = flat(text(ROOT / "shared" / "cli-contract.md"))

    assert "| `session_wait_any` | `sessions wait --any <run_id> <run_id> ... --timeout N --json`" in contract
    for kind in ("`question`", "`finished`", "`failed_to_start`", "`timeout`"):
        assert kind in contract, f"the contract names the wake kind {kind}"
    assert "give the next wait only the ids in `watch_next`" in contract


def test_parallel_orchestration_monitors_every_session_with_one_wait_and_keeps_a_fallback():
    orchestration = flat(text(ROOT / "shared" / "parallel-orchestration.md"))

    assert "Monitor **all** active run IDs with one wait over all of them" in orchestration
    assert "Without the feature, use bounded `sessions stream` calls or result polls" in orchestration


def test_every_skill_carries_the_same_copy_of_the_shared_docs():
    """`scripts/build-packages.sh` embeds `shared/*.md` into each skill; a hand edit to one copy would drift."""
    for name in SHARED_DOCS:
        shared = text(ROOT / "shared" / name)
        for skill in sorted((ROOT / "skills").iterdir()):
            copy = skill / "references" / name
            if copy.exists():
                assert text(copy) == shared, f"{copy.relative_to(ROOT)} differs from shared/{name}: run build-packages.sh"
