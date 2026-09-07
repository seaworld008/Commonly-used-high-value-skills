import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "bin" / "install-skills.js"
PACKAGE_JSON = REPO_ROOT / "package.json"


class NpxInstallerTests(unittest.TestCase):
    def _make_bundle_fixture(self, root, *, valid_digest=True):
        repo = root / "repo"
        (repo / "bin").mkdir(parents=True)
        (repo / "docs" / "sources").mkdir(parents=True)
        shutil.copy2(INSTALLER, repo / "bin" / INSTALLER.name)
        (repo / "package.json").write_text(
            json.dumps({"name": "bundle-gate-test", "version": "1.0.0"}),
            encoding="utf-8",
        )

        payload = b"verified local bundle fixture\n"
        package = "@opengsd/gsd-core"
        version = "1.11.0"
        spec = f"{package}@{version}"
        filename = f"opengsd-gsd-core-{version}.tgz"
        integrity = "sha512-" + base64.b64encode(
            hashlib.sha512(payload).digest()
        ).decode("ascii")
        shasum = hashlib.sha1(payload).hexdigest()
        digest = hashlib.sha256(payload).hexdigest()
        manifest = {
            "bundle": {"id": "gsd-core"},
            "install_policy": {"mode": "explicit_only", "default_install": False},
            "bundle_inventory": {
                "package_files": 1,
                "skills": 71,
                "agents": 34,
                "commands": 71,
                "runtime_files": 12,
            },
            "installer": {
                "registry": "npm",
                "package": package,
                "version": version,
                "spec": spec,
                "tarball_sha256": digest if valid_digest else "0" * 64,
                "integrity": integrity,
                "npm_shasum": shasum,
                "package_files": 1,
                "unpacked_size": len(payload),
            },
        }
        (repo / "docs" / "sources" / "open-gsd-core-2026-08.bundle.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        record = {
            "id": spec,
            "name": package,
            "version": version,
            "size": len(payload),
            "unpackedSize": len(payload),
            "shasum": shasum,
            "integrity": integrity,
            "filename": filename,
            "files": [{"path": "package.json"}],
        }
        return repo, payload, record

    def _write_fake_node_command(self, directory, name, source):
        if os.name == "nt":
            self.skipTest("fake npm/npx shims in this test are POSIX-only")
        command = directory / name
        command.write_text(
            f"#!{shutil.which('node')}\n{source}", encoding="utf-8"
        )
        command.chmod(0o755)

    def _bundle_env(self, fake_bin, temp_root, payload, record, log_path):
        return {
            **os.environ,
            "PATH": os.pathsep.join([str(fake_bin), os.environ.get("PATH", "")]),
            "TMPDIR": str(temp_root),
            "TMP": str(temp_root),
            "TEMP": str(temp_root),
            "FAKE_TARBALL_BASE64": base64.b64encode(payload).decode("ascii"),
            "FAKE_PACK_RECORD": json.dumps(record),
            "FAKE_NPX_LOG": str(log_path),
        }

    def _write_fake_bundle_commands(self, fake_bin):
        fake_bin.mkdir()
        self._write_fake_node_command(
            fake_bin,
            "npm",
            """
"use strict";
const fs = require("fs");
const path = require("path");
const record = JSON.parse(process.env.FAKE_PACK_RECORD);
const payload = Buffer.from(process.env.FAKE_TARBALL_BASE64, "base64");
fs.writeFileSync(path.join(process.cwd(), record.filename), payload);
process.stdout.write(JSON.stringify([record]));
""",
        )
        self._write_fake_node_command(
            fake_bin,
            "npx",
            """
"use strict";
const fs = require("fs");
const path = require("path");
const args = process.argv.slice(2);
const tarball = args[1];
const stat = fs.lstatSync(tarball);
if (args[0] !== "--yes" || !path.isAbsolute(tarball) ||
    stat.isSymbolicLink() || !stat.isFile()) process.exit(23);
fs.writeFileSync(process.env.FAKE_NPX_LOG, JSON.stringify(args));
""",
        )

    def test_package_exposes_installer_bin_and_skill_files(self):
        data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

        self.assertEqual("common-high-value-skills", data["name"])
        self.assertEqual("2.1.0", data["version"])
        self.assertEqual("bin/install-skills.js", data["bin"]["high-value-skills"])
        self.assertIn("skills/", data["files"])
        self.assertIn(
            "docs/sources/open-gsd-core-2026-08.bundle.json", data["files"]
        )
        self.assertNotIn("openclaw-skills/", data["files"])

    def test_installer_help_and_target_listing_work(self):
        help_result = subprocess.run(
            ["node", str(INSTALLER), "--help"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("high-value-skills install", help_result.stdout)

        targets_result = subprocess.run(
            ["node", str(INSTALLER), "list-targets"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("agents-project", targets_result.stdout)
        self.assertIn("codex", targets_result.stdout)
        self.assertIn("openclaw", targets_result.stdout)

        bundles_result = subprocess.run(
            ["node", str(INSTALLER), "list-bundles"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("gsd-core", bundles_result.stdout)
        self.assertIn("gsd-pi", bundles_result.stdout)
        self.assertIn("optional/list-only", bundles_result.stdout)

    def test_installer_flattens_categorized_skills_to_custom_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source" / "developer-engineering" / "sample-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: test skill\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            (source / "references").mkdir()
            (source / "references" / "note.md").write_text("reference\n", encoding="utf-8")
            dest = root / "installed"

            result = subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "install",
                    "--target",
                    "custom",
                    "--source-root",
                    str(root / "source"),
                    "--dir",
                    str(dest),
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("Installed 1 skills", result.stdout)
            self.assertTrue((dest / "sample-skill" / "SKILL.md").exists())
            self.assertTrue((dest / "sample-skill" / "references" / "note.md").exists())
            manifest = json.loads(
                (dest / ".high-value-skills-manifest.json").read_text(encoding="utf-8")
            )
            entry = manifest["skills"]["sample-skill"]
            self.assertEqual("sample-skill", entry["owner"])
            self.assertRegex(entry["source_digest"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                {"path", "sha256", "mode", "owner"}, set(entry["files"][0])
            )

    def test_installer_filters_by_category_and_skill_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for category, name in [
                ("developer-engineering", "api-helper"),
                ("developer-engineering", "db-helper"),
                ("security-and-reliability", "security-helper"),
            ]:
                skill = root / "source" / category / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: test skill\n---\n\n# Test\n",
                    encoding="utf-8",
                )

            dest = root / "installed"
            result = subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "install",
                    "--target",
                    "custom",
                    "--source-root",
                    str(root / "source"),
                    "--dir",
                    str(dest),
                    "--category",
                    "developer-engineering",
                    "--skill",
                    "db-helper",
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("Installed 1 skills", result.stdout)
            self.assertTrue((dest / "db-helper" / "SKILL.md").exists())
            self.assertFalse((dest / "api-helper").exists())
            self.assertFalse((dest / "security-helper").exists())

            listed = subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "list-skills",
                    "--source-root",
                    str(root / "source"),
                    "--category",
                    "security-and-reliability",
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn("security-helper", listed.stdout)
            self.assertNotIn("api-helper", listed.stdout)

    def test_dry_run_is_zero_write_and_reports_idempotent_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source" / "developer-engineering" / "mode-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("# mode\n", encoding="utf-8")
            script = source / "run.sh"
            script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            dest = root / "installed"
            command = [
                "node",
                str(INSTALLER),
                "install",
                "--target",
                "custom",
                "--source-root",
                str(root / "source"),
                "--dir",
                str(dest),
            ]
            subprocess.run(command, cwd=REPO_ROOT, check=True, capture_output=True)
            manifest_path = dest / ".high-value-skills-manifest.json"
            before = {
                path.relative_to(root).as_posix(): (
                    path.read_bytes(),
                    path.stat().st_mode & 0o777,
                    path.stat().st_mtime_ns,
                )
                for path in root.rglob("*")
                if path.is_file()
            }

            result = subprocess.run(
                [*command, "--dry-run"],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            after = {
                path.relative_to(root).as_posix(): (
                    path.read_bytes(),
                    path.stat().st_mode & 0o777,
                    path.stat().st_mtime_ns,
                )
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertIn("Updated: 0, Unchanged: 1", result.stdout)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            modes = {
                item["path"]: item["mode"]
                for item in manifest["skills"]["mode-skill"]["files"]
            }
            self.assertEqual("755", modes["run.sh"])

            missing_dest = root / "never-created"
            subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "install",
                    "--target",
                    "custom",
                    "--source-root",
                    str(root / "source"),
                    "--dir",
                    str(missing_dest),
                    "--dry-run",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
            )
            self.assertFalse(missing_dest.exists())

    def test_prune_deletes_unchanged_owned_and_archives_modified_or_unowned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source"
            for name in ("keeper", "retired-clean", "retired-modified"):
                skill = source_root / "operations-general" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
            dest = root / "installed"
            base = [
                "node",
                str(INSTALLER),
                "install",
                "--target",
                "custom",
                "--source-root",
                str(source_root),
                "--dir",
                str(dest),
            ]
            subprocess.run(base, cwd=REPO_ROOT, check=True, capture_output=True)
            (dest / "retired-modified" / "SKILL.md").write_text(
                "# user edit\n", encoding="utf-8"
            )
            unowned = dest / "retired-unowned"
            unowned.mkdir()
            (unowned / "SKILL.md").write_text("# local\n", encoding="utf-8")
            broken_link = dest / "retired-link"
            broken_link.symlink_to(root / "missing-local-target", target_is_directory=True)
            policy = root / "policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "retired_skills": [
                            {"name": "retired-clean"},
                            {"name": "retired-modified"},
                            {"name": "retired-unowned"},
                            {"name": "retired-link"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    *base,
                    "--skill",
                    "keeper",
                    "--prune-retired",
                    "--portfolio-policy",
                    str(policy),
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn("delete 1, archive 3", result.stdout)
            for name in (
                "retired-clean",
                "retired-modified",
                "retired-unowned",
                "retired-link",
            ):
                self.assertFalse((dest / name).exists())
            backups = root / ".high-value-skills-backups"
            self.assertEqual(
                "# user edit\n",
                next(backups.glob("*/installed/retired-modified/SKILL.md")).read_text(
                    encoding="utf-8"
                ),
            )
            self.assertTrue(
                next(backups.glob("*/installed/retired-unowned/SKILL.md")).exists()
            )
            self.assertTrue(
                next(backups.glob("*/installed/retired-link")).is_symlink()
            )

    def test_bundle_dry_run_is_pinned_and_never_writes_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {**os.environ, "HOME": str(home)}
            before = list(home.rglob("*"))
            result = subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "install",
                    "--bundle",
                    "gsd-core",
                    "--target",
                    "codex",
                    "--dry-run",
                ],
                cwd=REPO_ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertEqual(before, list(home.rglob("*")))
            self.assertIn("@opengsd/gsd-core@1.11.0", result.stdout)
            self.assertIn("71 skills, 34 agents, 71 commands", result.stdout)

            rejected = subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "install",
                    "--bundle",
                    "gsd-pi",
                    "--target",
                    "codex",
                    "--dry-run",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("optional/list-only", rejected.stderr)

    def test_bundle_install_verifies_tarball_then_executes_local_copy_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, payload, record = self._make_bundle_fixture(root)
            fake_bin = root / "fake-bin"
            self._write_fake_bundle_commands(fake_bin)
            temp_root = root / "bundle-temp"
            temp_root.mkdir()
            log_path = root / "npx.json"
            env = self._bundle_env(
                fake_bin, temp_root, payload, record, log_path
            )

            result = subprocess.run(
                [
                    shutil.which("node"),
                    str(repo / "bin" / INSTALLER.name),
                    "install",
                    "--bundle",
                    "gsd-core",
                    "--target",
                    "codex",
                ],
                cwd=repo,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )

            args = json.loads(log_path.read_text(encoding="utf-8"))
            self.assertEqual("--yes", args[0])
            self.assertEqual(["--codex", "--global"], args[2:])
            self.assertTrue(Path(args[1]).is_absolute())
            self.assertFalse(Path(args[1]).exists())
            self.assertEqual([], list(temp_root.iterdir()))
            self.assertIn("Installed governed bundle gsd-core", result.stdout)

    def test_bundle_install_rejects_digest_drift_before_execution_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, payload, record = self._make_bundle_fixture(
                root, valid_digest=False
            )
            fake_bin = root / "fake-bin"
            self._write_fake_bundle_commands(fake_bin)
            temp_root = root / "bundle-temp"
            temp_root.mkdir()
            log_path = root / "npx.json"
            env = self._bundle_env(
                fake_bin, temp_root, payload, record, log_path
            )

            result = subprocess.run(
                [
                    shutil.which("node"),
                    str(repo / "bin" / INSTALLER.name),
                    "install",
                    "--bundle",
                    "gsd-core",
                    "--target",
                    "codex",
                ],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("SHA-256 does not match", result.stderr)
            self.assertFalse(log_path.exists())
            self.assertEqual([], list(temp_root.iterdir()))

    def test_bundle_install_fails_closed_and_cleans_temp_when_npm_cannot_spawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, _ = self._make_bundle_fixture(root)
            temp_root = root / "bundle-temp"
            temp_root.mkdir()
            empty_path = root / "empty-path"
            empty_path.mkdir()
            env = {
                **os.environ,
                "PATH": str(empty_path),
                "TMPDIR": str(temp_root),
                "TMP": str(temp_root),
                "TEMP": str(temp_root),
            }

            result = subprocess.run(
                [
                    shutil.which("node"),
                    str(repo / "bin" / INSTALLER.name),
                    "install",
                    "--bundle",
                    "gsd-core",
                    "--target",
                    "codex",
                ],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("Unable to download pinned bundle", result.stderr)
            self.assertEqual([], list(temp_root.iterdir()))

    def test_conflict_audit_reports_cross_root_digest_and_ownership_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source" / "operations-general" / "shared-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("# shared\n", encoding="utf-8")
            roots = [root / "one", root / "two"]
            for dest in roots:
                subprocess.run(
                    [
                        "node",
                        str(INSTALLER),
                        "install",
                        "--target",
                        "custom",
                        "--source-root",
                        str(root / "source"),
                        "--dir",
                        str(dest),
                    ],
                    cwd=REPO_ROOT,
                    check=True,
                    capture_output=True,
                )
            (roots[1] / "shared-skill" / "SKILL.md").write_text(
                "# drift\n", encoding="utf-8"
            )
            result = subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "audit-conflicts",
                    "--roots",
                    ",".join(map(str, roots)),
                    "--json",
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            data = json.loads(result.stdout)
            self.assertEqual(1, data["duplicate_names"])
            self.assertEqual(1, data["content_conflicts"])
            ownership = {entry["ownership"] for entry in data["matrix"][0]["entries"]}
            self.assertEqual(
                {"common-high-value-skills", "unowned-or-modified"}, ownership
            )


if __name__ == "__main__":
    unittest.main()


def test_npm_package_excludes_interpreter_caches_without_dropping_resources(tmp_path):
    """Exercise npm's nested ignore rules; root files whitelists override .gitignore."""
    import shutil
    import pytest
    if shutil.which("npm") is None:
        pytest.skip("npm is required for the real pack boundary check")
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "skill-pack-fixture", "version": "1.0.0", "files": ["skills/"]
    }))
    skill = tmp_path / "skills" / "category" / "example"
    (skill / "scripts" / "__pycache__").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Example\n")
    (skill / "scripts" / "helper.py").write_text("print('example')\n")
    (skill / "scripts" / "__pycache__" / "helper.pyc").write_bytes(b"cache fixture")
    (skill / "scripts" / "loose.pyc").write_bytes(b"cache fixture")
    (skill / "scripts" / "loose.pyo").write_bytes(b"cache fixture")
    shutil.copy2(REPO_ROOT / "skills" / ".npmignore", tmp_path / "skills" / ".npmignore")
    result = subprocess.run(
        ["npm", "pack", "--dry-run", "--json", "--ignore-scripts"],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    )
    paths = {item["path"] for item in json.loads(result.stdout)[0]["files"]}
    assert "skills/category/example/SKILL.md" in paths
    assert "skills/category/example/scripts/helper.py" in paths
    assert not any("__pycache__" in p or p.endswith((".pyc", ".pyo")) for p in paths)
