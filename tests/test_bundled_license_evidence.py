import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SKILL = Path("skills/category/example")
NOTICE = Path("references/upstream-terms.txt")
COMMIT = "a" * 40


def origin(repo, notice):
    return {
        "repo": repo,
        "license": "MIT",
        "artifacts": [{"source": "LICENSE", "target": (SKILL / NOTICE).as_posix()}],
        "tracking": {
            "resolved_commit": COMMIT,
            "license_checkpoint": {
                "path": "LICENSE", "spdx": "MIT", "resolved_commit": COMMIT,
                "blob_sha": hashlib.sha1(f"blob {len(notice)}\0".encode() + notice).hexdigest(),
                "content_sha256": hashlib.sha256(notice).hexdigest(),
            },
        },
    }


class BundledLicenseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.notice = (REPO / "LICENSE").read_bytes().replace(b"seaworld008", b"Fixture Author")
        self.file = self.root / SKILL / NOTICE
        self.file.parent.mkdir(parents=True)
        (self.root / SKILL / "SKILL.md").write_text("---\nsource: in-house\nlicense: MIT\n---\n")
        self.mapping = self.root / "docs/sources/fixture.skills.json"
        self.mapping.parent.mkdir(parents=True)
        self.entry = {
            "repo_skill": (SKILL / "SKILL.md").as_posix(),
            "normalized_slug": "example",
            "status": "verified_in_repo",
            "kind": "overlay",
            "origins": [origin("fixture/upstream", self.notice)],
            "managed_files": [{
                "path": (SKILL / NOTICE).as_posix(),
                "sha256": hashlib.sha256(self.notice).hexdigest(),
            }],
        }

    def audit(self, expected_exit, *flags, extra_entries=()):
        self.mapping.write_text(json.dumps({
            "schema_version": 2, "skills": [self.entry, *extra_entries],
        }))
        result = subprocess.run(
            [sys.executable, "-B", str(REPO / "scripts/audit_licenses.py"),
             "--repo-root", str(self.root), "--json", *flags],
            capture_output=True, text=True,
        )
        self.assertEqual(expected_exit, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)["rows"][0]

    def test_reviewed_bytes_survive_single_skill_install(self):
        self.file.write_bytes(self.notice)
        # The upstream checkpoint is sufficient even for a renamed, unlisted file.
        self.entry["origins"][0]["artifacts"] = []
        self.entry["managed_files"] = []
        row = self.audit(0)
        self.assertEqual("OK", row["status"])
        self.assertEqual((SKILL / NOTICE).as_posix(), row["origins"][0]["bundled_license"])
        dest = self.root / "installed"
        subprocess.run(
            ["node", str(REPO / "bin/install-skills.js"), "install", "--target", "custom",
             "--source-root", str(self.root / "skills"), "--skill", "example", "--dir", str(dest)],
            check=True, capture_output=True, text=True, cwd=self.root,
        )
        self.assertEqual(self.notice, (dest / "example" / NOTICE).read_bytes())
        manifest = json.loads((dest / ".high-value-skills-manifest.json").read_text())
        self.assertEqual({"example"}, set(manifest["skills"]))
        installed = {f["path"]: f["sha256"] for f in manifest["skills"]["example"]["files"]}
        self.assertEqual(hashlib.sha256(self.notice).hexdigest(), installed[NOTICE.as_posix()])

    def test_missing_spdx_only_changed_holder_and_stale_checkpoint_fail(self):
        self.assertEqual("MISSING", self.audit(1)["status"])
        for body in (b"SPDX-License-Identifier: MIT\n", self.notice.replace(b"Fixture", b"Other")):
            with self.subTest(body=body[:20]):
                self.file.write_bytes(body)
                self.entry["managed_files"][0]["sha256"] = hashlib.sha256(body).hexdigest()
                self.assertIn("license_checkpoint", self.audit(1, "--strict")["note"])
        self.file.write_bytes(self.notice)
        self.entry["origins"][0]["tracking"]["resolved_commit"] = "b" * 40
        self.assertIn("inconsistent", self.audit(1)["note"])

    def test_checkpoint_cannot_turn_a_bare_spdx_label_into_a_notice(self):
        stub = b"MIT License\nSPDX-License-Identifier: MIT\n"
        self.entry["origins"] = [origin("fixture/upstream", stub)]
        self.file.write_bytes(stub)
        self.assertIn("no upstream license body", self.audit(1)["note"])

    def test_external_targets_symlinks_and_uninstalled_cache_cannot_supply_evidence(self):
        for rel in ("LICENSE", "skills/category/sibling/LICENSE", str(SKILL / "__pycache__/LICENSE")):
            outside = self.root / rel
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_bytes(self.notice)
            self.entry["origins"][0]["artifacts"][0]["target"] = rel
            self.assertEqual("MISSING", self.audit(1)["status"])
        self.file.symlink_to(self.root / "LICENSE")
        (self.root / SKILL / "borrowed").symlink_to(self.root / SKILL.parent / "sibling",
                                                     target_is_directory=True)
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.file.parent / "COPYING")
        self.assertEqual("MISSING", self.audit(1)["status"])

    def test_each_external_origin_needs_its_own_notice(self):
        self.file.write_bytes(self.notice)
        other = self.notice.replace(b"Fixture Author", b"Second Author")
        self.entry["origins"].append(origin("second/upstream", other))
        self.assertEqual(["OK", "MISSING"], [o["status"] for o in self.audit(1)["origins"]])
        (self.file.parent / "second.txt").write_bytes(other)
        self.assertEqual("OK", self.audit(0, "--strict")["status"])

    def test_standalone_legacy_license_must_match_the_full_declared_license(self):
        apache = (REPO / "skills/developer-engineering/mcp-builder/LICENSE.txt").read_bytes()
        self.file.write_bytes(apache)
        upstream = self.entry["origins"][0]
        del upstream["tracking"]["license_checkpoint"]
        self.entry["managed_files"][0]["sha256"] = hashlib.sha256(apache).hexdigest()
        self.assertEqual("MISSING", self.audit(1)["status"])  # still declares MIT
        upstream["license"] = "Apache-2.0"
        self.assertEqual("OK", self.audit(0)["status"])
        excerpt = apache[:200]
        self.file.write_bytes(excerpt)
        self.entry["managed_files"][0]["sha256"] = hashlib.sha256(excerpt).hexdigest()
        self.assertEqual("MISSING", self.audit(1)["status"])

    def test_legacy_snapshot_requires_origin_mapped_locked_notice(self):
        self.file.write_bytes(self.notice)
        self.entry["kind"] = "snapshot"
        peer = {"kind": "reference_only", "origins": [origin("fixture/upstream", self.notice)]}
        del self.entry["origins"][0]["tracking"]["license_checkpoint"]
        self.assertEqual("OK", self.audit(0, extra_entries=[peer])["status"])
        self.file.write_bytes(b"MIT")
        self.assertEqual("MISSING", self.audit(1, extra_entries=[peer])["status"])
        self.entry["managed_files"][0]["sha256"] = hashlib.sha256(b"MIT").hexdigest()
        self.assertEqual("MISSING", self.audit(1, extra_entries=[peer])["status"])
        self.file.write_bytes(self.notice)
        self.entry["managed_files"][0]["sha256"] = hashlib.sha256(self.notice).hexdigest()
        self.entry["origins"][0]["artifacts"][0]["target"] = "skills/category/sibling/LICENSE"
        self.assertEqual("MISSING", self.audit(1, extra_entries=[peer])["status"])

    def test_reference_only_checks_metadata_without_requiring_a_bundled_file(self):
        self.entry["kind"] = "reference_only"
        self.assertEqual("OK", self.audit(0)["status"])
        self.entry["origins"][0]["license"] = "GPL-3.0-only"
        self.assertEqual("UNKNOWN", self.audit(1)["status"])

    def test_remote_locator_with_unknown_license_cannot_become_local(self):
        self.entry["kind"] = "in_house"
        self.entry["origins"] = [{"url": "https://example.invalid/source", "license": "NOASSERTION"}]
        self.assertEqual("UNKNOWN", self.audit(1)["status"])
