import hashlib

from tests.test_bundled_license_evidence import (
    BundledLicenseFixture, SKILL, origin, tracking_for_notice,
)


class LicenseLineageTests(BundledLicenseFixture):
    def test_directory_and_file_artifacts_both_require_origin_checkpoint(self):
        self.file.write_bytes(self.notice)
        upstream = self.entry["origins"][0]
        for artifact in (
            {"type": "file", "source": "LICENSE", "target": self.file.relative_to(self.root).as_posix()},
            {"type": "directory", "source": "packages/example", "target": SKILL.as_posix()},
        ):
            with self.subTest(artifact=artifact["type"]):
                upstream["artifacts"] = [artifact]
                upstream["tracking"] = tracking_for_notice(self.notice)
                checkpoint = upstream["tracking"].pop("license_checkpoint")
                self.assertIn("missing license_checkpoint", self.audit(1)["note"])
                upstream["tracking"]["license_checkpoint"] = checkpoint
                row = self.audit(0)
                self.assertEqual("OK", row["status"])
                self.assertEqual(self.file.relative_to(self.root).as_posix(),
                                 row["origins"][0]["bundled_license"])

    def test_other_commit_of_same_repo_cannot_supply_checkpoint_or_notice(self):
        upstream = self.entry["origins"][0]
        upstream["path"] = "skills/example"
        other_notice = self.notice.replace(b"Fixture Author", b"Other Author")
        peer_origin = origin(upstream["repo"], other_notice)
        peer_origin["path"] = "skills/sibling"
        peer_origin["tracking"] = tracking_for_notice(other_notice, commit="b" * 40)
        peer = {"kind": "reference_only", "origins": [peer_origin]}
        self.file.write_bytes(other_notice)
        self.entry["managed_files"][0]["sha256"] = hashlib.sha256(other_notice).hexdigest()
        tracking = upstream["tracking"]
        checkpoint = tracking.pop("license_checkpoint")
        self.assertIn("missing license_checkpoint", self.audit(1, extra_entries=[peer])["note"])
        tracking["license_checkpoint"] = peer_origin["tracking"]["license_checkpoint"]
        self.assertIn("resolved_commit inconsistent", self.audit(1, extra_entries=[peer])["note"])
        tracking["license_checkpoint"] = checkpoint
        self.assertIn("no installed file matches", self.audit(1, extra_entries=[peer])["note"])
        self.file.write_bytes(self.notice)
        self.entry["managed_files"][0]["sha256"] = hashlib.sha256(self.notice).hexdigest()
        self.assertEqual("OK", self.audit(0, extra_entries=[peer])["status"])

    def test_checkpoint_fields_are_required_even_for_noncanonical_entries(self):
        self.entry.pop("repo_skill")
        upstream = self.entry["origins"][0]
        checkpoint = upstream["tracking"]["license_checkpoint"]
        for field in ("spdx", "resolved_commit", "path", "blob_sha", "content_sha256"):
            with self.subTest(field=field):
                saved = checkpoint.pop(field)
                row = self.audit(1)
                self.assertFalse(row["canonical"])
                self.assertIn(f"license_checkpoint.{field}", row["note"])
                checkpoint[field] = saved
        self.assertEqual("OK", self.audit(0)["status"])

    def test_malformed_or_conflicting_checkpoint_fails_even_with_matching_text(self):
        self.file.write_bytes(self.notice)
        checkpoint = self.entry["origins"][0]["tracking"]["license_checkpoint"]
        for field, value in (
            ("path", "../LICENSE"), ("path", "LICENSE\0"), ("blob_sha", "abcd"),
            ("blob_sha", "b" * 40),
            ("content_sha256", "abcd"), ("api_spdx", "GPL-3.0-only"),
        ):
            with self.subTest(field=field, value=value):
                self.entry["origins"][0]["tracking"]["license_checkpoint"] = {**checkpoint, field: value}
                row = self.audit(1)
                self.assertEqual("MISSING", row["status"])
                self.assertIn(f"license_checkpoint.{field}", row["note"])

    def test_git_sha256_blob_for_reviewed_notice(self):
        self.file.write_bytes(self.notice)
        tracking = tracking_for_notice(self.notice, commit="d" * 64)
        header = f"blob {len(self.notice)}\0".encode("ascii")
        tracking["license_checkpoint"]["blob_sha"] = hashlib.sha256(header + self.notice).hexdigest()
        self.entry["origins"][0]["tracking"] = tracking
        self.assertEqual("OK", self.audit(0)["status"])

    def test_prohibited_nonempty_text_cannot_become_a_license_grant(self):
        prohibited = b"All rights reserved. Redistribution is prohibited.\n"
        self.file.write_bytes(prohibited)
        self.entry["origins"][0]["tracking"] = tracking_for_notice(prohibited)
        self.entry["managed_files"][0]["sha256"] = hashlib.sha256(prohibited).hexdigest()
        self.assertIn("no upstream license body", self.audit(1)["note"])

    def test_only_asset_free_retired_metadata_can_omit_checkpoint(self):
        self.entry.pop("repo_skill")
        self.entry["status"] = "retired"
        self.entry["managed_files"] = []
        upstream = self.entry["origins"][0]
        upstream["artifacts"] = []
        upstream["tracking"].pop("license_checkpoint")
        self.assertIn("retired metadata only", self.audit(0)["note"])
        upstream["artifacts"] = [{"source": "LICENSE", "target": "licenses/copy.txt"}]
        self.assertIn("missing license_checkpoint", self.audit(1)["note"])
