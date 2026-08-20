import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RETIRED = {
    "hermes-graphify-gsd-nonintrusive-workflow",
    "hermes-graphify-gsd-runtime-operator",
    "hermes-graphify-gsd-project-integration",
    "gsd-graphify-brownfield-bootstrap",
}
ROUTER = "hermes-open-gsd-workflow"
MIGRATION = "open-gsd-core-migration"
REMOVED = RETIRED | {MIGRATION}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RetiredHermesOpenGsdCompositeTests(unittest.TestCase):
    def test_retired_and_migration_source_directories_are_absent(self):
        discovered = {
            path.parent.name for path in REPO_ROOT.glob("skills/*/*/SKILL.md")
        }

        self.assertTrue(REMOVED.isdisjoint(discovered))
        self.assertIn(ROUTER, discovered)

    def test_openclaw_export_cannot_rediscover_retired_aliases(self):
        exporter = load_module(
            "retired_composite_exporter",
            REPO_ROOT / "scripts" / "export_openclaw_skills.py",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "openclaw-skills"
            exported = exporter.export_openclaw_skills(
                REPO_ROOT / "skills",
                output_root,
            )
            names = {path.name for path in exported}

        self.assertTrue(REMOVED.isdisjoint(names))
        self.assertIn(ROUTER, names)

    def test_portfolio_policy_keeps_only_a_non_routing_denylist(self):
        policy = json.loads(
            (REPO_ROOT / "docs" / "sources" / "portfolio-policy.json").read_text(
                encoding="utf-8"
            )
        )
        retired = {
            entry["name"]: entry
            for entry in policy["retired_skills"]
            if entry.get("name") in REMOVED
        }
        self.assertEqual(REMOVED, set(retired))
        for entry in retired.values():
            self.assertTrue(
                {"replacement", "migration", "tombstone"}.isdisjoint(entry)
            )

        self.assertNotIn(
            ROUTER,
            {
                group.get("canonical")
                for group in policy["canonical_groups"]
            },
        )

    def test_provenance_locks_router_and_removes_migration(self):
        payload = json.loads(
            (REPO_ROOT / "docs" / "sources" / "in-house.skills.json").read_text(
                encoding="utf-8"
            )
        )
        entries = {
            entry["normalized_slug"]: entry
            for entry in payload["skills"]
            if entry.get("normalized_slug") in {ROUTER, MIGRATION}
        }
        self.assertEqual({ROUTER}, set(entries))

        router = entries[ROUTER]
        self.assertEqual("composite", router["kind"])
        router_dependencies = {
            dependency.get("skill") or dependency.get("source_package")
            for dependency in router["composition"]["depends_on"]
        }
        self.assertEqual(
            {
                "hermes-agent",
                "graphify",
                "open-gsd/gsd-core",
                "open-gsd/gsd-pi",
            },
            router_dependencies,
        )
        self.assertEqual(
            router_dependencies,
            set(router["composition"]["dependency_lock"]),
        )

        router_text = (
            REPO_ROOT
            / "skills"
            / "ai-agent-platform"
            / ROUTER
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        for removed in REMOVED:
            self.assertNotIn(removed, router_text)

    def test_active_docs_and_generated_views_have_no_removed_routes(self):
        active_surfaces = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "README.en.md",
            REPO_ROOT / "docs" / "client-install-guides.md",
            REPO_ROOT / "docs" / "catalog.json",
            REPO_ROOT / "docs" / "TAGS-INDEX.md",
            REPO_ROOT
            / "skills"
            / "engineering-workflow-automation"
            / "README.md",
            REPO_ROOT
            / "openclaw-skills"
            / ROUTER
            / "SKILL.md",
        ]
        for path in active_surfaces:
            text = path.read_text(encoding="utf-8")
            for removed in REMOVED:
                self.assertNotIn(removed, text, path)

    def test_category_readme_generator_has_no_retired_usage_state_machine(self):
        generator = (
            REPO_ROOT / "scripts" / "generate_category_readmes.py"
        ).read_text(encoding="utf-8")
        for retired in RETIRED:
            self.assertNotIn(retired, generator)
        for obsolete_state in (
            "writer lease",
            "auto-continue",
            "task-board",
            "install-hermes-auto-continue-cron",
            "gsd-sdk init",
        ):
            self.assertNotIn(obsolete_state, generator)


if __name__ == "__main__":
    unittest.main()
