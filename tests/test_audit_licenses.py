import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_licenses.py"


class AuditLicensesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("audit_licenses", SCRIPT_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module

    def make_v2_repo(
        self,
        root: Path,
        *,
        origins: list[dict],
        frontmatter_source: str = "in-house",
        frontmatter_license: str = "MIT",
        kind: str = "mirror",
        repo_skill: str | None = "skills/ai-workflow/fixture-skill/SKILL.md",
    ) -> Path:
        if repo_skill:
            skill_path = root / repo_skill
            skill_path.parent.mkdir(parents=True)
            license_line = (
                f"license: {frontmatter_license}\n" if frontmatter_license else ""
            )
            skill_path.write_text(
                "---\n"
                "name: fixture-skill\n"
                "description: Fixture skill for provenance license tests.\n"
                f"source: {frontmatter_source}\n"
                f"{license_line}"
                "---\n"
                "# Fixture\n",
                encoding="utf-8",
            )
        mapping = root / "docs" / "sources" / "fixture.skills.json"
        mapping.parent.mkdir(parents=True)
        entry = {
            "video_name": "fixture-skill",
            "normalized_slug": "fixture-skill",
            "status": "verified_in_repo",
            "kind": kind,
            "origins": origins,
        }
        if repo_skill:
            entry["repo_skill"] = repo_skill
        mapping.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "skills": [entry],
                }
            ),
            encoding="utf-8",
        )
        return mapping

    def test_summary_matches_current_audit_shape(self):
        rows = self.module.audit()
        payload = self.module.summarize(rows)
        self.assertEqual(len(rows), payload["total"])
        self.assertEqual(payload["missing"], sum(1 for row in rows if row["status"] == "MISSING"))
        self.assertEqual(payload["unknown"], sum(1 for row in rows if row["status"] == "UNKNOWN"))
        self.assertEqual(payload["ok"], sum(1 for row in rows if row["status"] == "OK"))
        self.assertEqual(
            payload["tracked_origins"],
            sum(row.get("tracked_origin_count", 0) for row in rows),
        )

    def test_report_writers_emit_expected_files(self):
        rows = self.module.audit()
        payload = self.module.summarize(rows)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            rel_dir = Path(tmp).relative_to(REPO_ROOT)
            json_path = rel_dir / "license-audit.json"
            md_path = rel_dir / "license-audit.md"
            self.module.write_json_report(payload, str(json_path))
            self.module.write_markdown_report(payload, str(md_path))

            written_json = json.loads((REPO_ROOT / json_path).read_text(encoding="utf-8"))
            written_md = (REPO_ROOT / md_path).read_text(encoding="utf-8")

            self.assertEqual(payload["total"], written_json["total"])
            self.assertIn("# License Audit Report", written_md)
            self.assertIn("Total skills", written_md)

    def test_v2_external_origin_license_is_source_of_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/upstream",
                        "path": "skills/fixture/SKILL.md",
                        "license": "MIT",
                        "tracking": {"channel": "release", "ref": "v1.0.0"},
                    }
                ],
                frontmatter_source="in-house",
                frontmatter_license="",
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("OK", row["status"])
            self.assertEqual("provenance_v2_origins", row["evidence"])
            self.assertEqual("MIT", row["origins"][0]["license"])

    def test_v2_external_origin_missing_license_fails_despite_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/upstream",
                        "path": "skills/fixture/SKILL.md",
                        "tracking": {"channel": "release", "ref": "v1.0.0"},
                    }
                ],
                frontmatter_source="github:example/upstream",
                frontmatter_license="MIT",
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("MISSING", row["status"])
            self.assertIn("lacks an SPDX license", row["note"])

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--repo-root",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)

    def test_v2_disallowed_license_fails_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/upstream",
                        "path": "skills/fixture/SKILL.md",
                        "license": "GPL-3.0-only",
                    }
                ],
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("UNKNOWN", row["status"])
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--repo-root",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)

    def test_v2_local_origin_is_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "local-repo/in-house",
                        "path": "skills/ai-workflow/fixture-skill",
                    }
                ],
                frontmatter_license="",
                kind="in_house",
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("EXEMPT", row["status"])
            self.assertEqual([], row["origins"])

    def test_v2_external_kind_cannot_claim_exemption_without_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[],
                frontmatter_source="in-house",
                frontmatter_license="MIT",
                kind="mirror",
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("MISSING", row["status"])
            self.assertIn("no auditable external origin", row["note"])

    def test_v2_composite_without_origin_is_locally_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[],
                frontmatter_source="in-house",
                frontmatter_license="",
                kind="composite",
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("EXEMPT", row["status"])
            self.assertEqual([], row["origins"])

    def test_v2_noncanonical_mit_bundle_is_audited_and_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/bundle",
                        "path": "packages/runtime",
                        "license": "MIT",
                    }
                ],
                kind="bundle",
                repo_skill=None,
            )

            [row] = self.module.audit(repo_root=root)
            payload = self.module.summarize([row])

            self.assertEqual("OK", row["status"])
            self.assertFalse(row["canonical"])
            self.assertEqual(1, payload["total"])
            self.assertEqual(1, payload["noncanonical_v2_entries"])
            self.assertEqual(1, payload["tracked_origins"])
            self.assertEqual(1, payload["external_origins"])

    def test_v2_noncanonical_gpl_bundle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/bundle",
                        "path": "packages/runtime",
                        "license": "GPL-3.0-only",
                    }
                ],
                kind="bundle",
                repo_skill=None,
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("UNKNOWN", row["status"])
            self.assertEqual("GPL-3.0-only", row["license"])
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--repo-root",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)

    def test_v2_noncanonical_bundle_missing_license_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/bundle",
                        "path": "packages/runtime",
                    }
                ],
                kind="bundle",
                repo_skill=None,
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("MISSING", row["status"])
            self.assertIn("lacks an SPDX license", row["note"])
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--repo-root",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)

    def test_v2_noncanonical_snapshot_and_reference_origins_are_audited(self):
        for kind in ("snapshot", "reference_only"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make_v2_repo(
                    root,
                    origins=[
                        {
                            "repo": "example/archive",
                            "path": "skills/retired/SKILL.md",
                        }
                    ],
                    kind=kind,
                    repo_skill=None,
                )

                [row] = self.module.audit(repo_root=root)

                self.assertEqual("MISSING", row["status"])
                self.assertEqual(1, row["external_origin_count"])

    def test_v2_mapping_argument_does_not_double_count_an_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/bundle",
                        "path": "packages/runtime",
                        "license": "MIT",
                    }
                ],
                kind="bundle",
                repo_skill=None,
            )

            rows = self.module.audit(
                repo_root=root,
                mapping_paths=[mapping, mapping],
            )

            self.assertEqual(1, len(rows))
            self.assertEqual(1, self.module.summarize(rows)["tracked_origins"])

    def test_v2_external_false_does_not_hide_remote_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_v2_repo(
                root,
                origins=[
                    {
                        "repo": "example/upstream",
                        "path": "skills/fixture/SKILL.md",
                        "external": False,
                    }
                ],
                frontmatter_license="MIT",
            )

            [row] = self.module.audit(repo_root=root)

            self.assertEqual("MISSING", row["status"])


if __name__ == "__main__":
    unittest.main()
