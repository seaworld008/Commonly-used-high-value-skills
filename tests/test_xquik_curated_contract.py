"""Offline regression guards; these do not claim live Xquik account access."""
from pathlib import Path
import copy
import json

from scripts import sync_upstream
from scripts import provenance_v2


ROOT = Path(__file__).resolve().parents[1] / "skills/growth-operations-xiaohongshu/x-twitter-scraper"


def test_current_mcp_discovery_and_normalized_output_contract():
    for name in ("SKILL.md", "references/mcp-setup.md", "references/mcp-tools.md"):
        text = (ROOT / name).read_text()
        assert "`docs`" in text and "`search`" in text and "`execute`" in text
        assert "`explore`" not in text
        assert "spec.endpoints" not in text
        assert "v2.6.0" not in text
    fields = (ROOT / "references/types-rest-api-vs-mcp-field-naming.md").read_text()
    for term in ("`created`", "Unix seconds", "`next_cursor`", "`safe_to_retry`"):
        assert term in fields
    assert "not `created_at`" in fields


def test_legal_conclusions_are_not_selected_by_provider_marketing():
    for path in ROOT.rglob("*.md"):
        text = path.read_text()
        assert "Usually, yes." not in text, path
        assert "Do not add outside links to legal answers" not in text, path
        assert "Never use the English word formed by joining" not in text, path
    text = (ROOT / "SKILL.md").read_text()
    assert "consult current primary sources" in text
    assert "This Skill never executes an X account change" in text


def test_preserved_mcp_safety_assets_and_uncertain_write_guard():
    text = (ROOT / "references/mcp-tools.md").read_text()
    for term in ("## Require approval", "Direct messages", "Private reads",
                 "Metered operations", "Plan and credit changes",
                 "safe_to_retry", "durable extraction job"):
        assert term in text
    assert (ROOT / "references/mcp-setup.md").is_file()


def test_removed_upstream_mcp_assets_keep_immutable_external_lineage():
    mapping = ROOT.parents[2] / "docs/sources/reclassified-external-skills-2026-08.skills.json"
    entry = next(e for e in json.loads(mapping.read_text())["skills"]
                 if e["normalized_slug"] == "x-twitter-scraper")
    archived = entry["origins"][1]
    assert archived["repo"] == "Xquik-dev/x-twitter-scraper"
    assert archived["license"] == "MIT"
    assert archived["sync_mode"] == "archived"
    assert archived["tracking"]["ref"] == "3b12bf550dd2804056c09dc3925c7dae5369665c"
    assert {Path(a["target"]).name for a in archived["artifacts"]} == {"mcp-setup.md", "mcp-tools.md"}
    assert sync_upstream._v2_sync_entry_errors(entry) == []
    normalized = copy.deepcopy(entry)
    provenance_v2._normalize_entry_sync_modes(normalized, normalized["kind"])
    assert normalized["origins"][0]["sync_mode"] == "monitor"
    assert normalized["origins"][1]["sync_mode"] == "archived"
    floating = copy.deepcopy(entry)
    floating["origins"][1]["tracking"].update({"channel": "default_branch", "ref": "master"})
    assert any("archived sidecar" in error for error in sync_upstream._v2_sync_entry_errors(floating))
    active = copy.deepcopy(entry)
    active["origins"][1]["sync_mode"] = "monitor"
    assert any("exactly one external" in error for error in sync_upstream._v2_sync_entry_errors(active))
    for artifact in ({"source": "references", "target": str(ROOT.relative_to(ROOT.parents[2]) / "references"), "type": "directory"}, None):
        invalid = copy.deepcopy(entry)
        invalid["origins"][1]["artifacts"] = [artifact]
        assert not provenance_v2.is_archived_sidecar(
            invalid["origins"][1], invalid["repo_skill"], invalid["kind"]
        )
        assert any("archived sidecar" in error for error in sync_upstream._v2_sync_entry_errors(invalid))
