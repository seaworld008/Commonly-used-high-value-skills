import hashlib
import json
import stat
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPING = (
    REPO_ROOT
    / "docs"
    / "sources"
    / "simota-agent-skills-2026-04.skills.json"
)
CURRENT_COMMIT = "9f7d77adc30fd39f039871081d26aaf7bf60f54d"
WEEKLY_REVIEW_COMMIT = "9f7d77adc30fd39f039871081d26aaf7bf60f54d"
# The complete retry succeeded for every active monitor entry; archived
# snapshots below retain their immutable historical checkpoints.
WEEKLY_REVIEWED = {
    "pulse", "stage", "lore", "tome", "grove", "voice", "trace", "breach",
    "cloak", "scaffold", "cast", "omen", "lens", "scout", "ripple",
}
ARCHIVE_COMMIT = "6502f44cfcd8f456951a7bfdce14d0ed76d724ef"
MONITOR_REVIEWED = {
    "gateway",
    "sherpa",
    "rally",
    "oracle",
    "sigil",
    "beacon",
    "triage",
    "gear",
    "ledger",
    "grove",
    "voice",
    "trace",
    "breach",
    "cloak",
    "cast",
    "lens",
    "ripple",
}
ARCHIVED_SNAPSHOTS = {
    "harvest",
    "latch",
    "helm",
    "morph",
    "crest",
    "hearth",
    "sketch",
    "pipe",
    "shard",
}
PREEXISTING_SNAPSHOTS = {
    "arena",
    "levy",
    "prism",
    "dawn",
    "researcher",
    "comply",
    "clay",
    "tone",
    "warden",
}


class SimotaUpstreamGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(MAPPING.read_text(encoding="utf-8"))
        cls.entries = {
            entry["normalized_slug"]: entry
            for entry in cls.payload["skills"]
        }

    def test_portfolio_decisions_and_lore_move_are_locked(self):
        self.assertEqual(48, len(self.entries))
        snapshots = {
            slug
            for slug, entry in self.entries.items()
            if entry["kind"] == "snapshot"
        }
        self.assertEqual(
            PREEXISTING_SNAPSHOTS | ARCHIVED_SNAPSHOTS,
            snapshots,
        )
        lore = self.entries["lore"]
        self.assertEqual(
            ".agents/skills/lore/SKILL.md",
            lore["origins"][0]["path"],
        )
        self.assertEqual(
            ".agents/skills/lore/SKILL.md",
            lore["upstream"]["path"],
        )

    def test_reviewed_monitor_entries_advance_to_current_commit(self):
        for slug in MONITOR_REVIEWED | WEEKLY_REVIEWED:
            with self.subTest(slug=slug):
                entry = self.entries[slug]
                origin = entry["origins"][0]
                tracking = origin["tracking"]
                self.assertEqual("monitor", entry["sync_mode"])
                expected_commit = (
                    WEEKLY_REVIEW_COMMIT if slug in WEEKLY_REVIEWED else CURRENT_COMMIT
                )
                self.assertEqual(expected_commit, tracking["resolved_commit"])
                self.assertEqual(
                    expected_commit,
                    tracking["license_checkpoint"]["resolved_commit"],
                )
                self.assertEqual("MIT", tracking["license_checkpoint"]["spdx"])
                self.assertRegex(tracking["path_commit"], r"^[0-9a-f]{40}$")
                if slug in WEEKLY_REVIEWED:
                    self.assertEqual("2026-09-06", tracking["last_checked_at"])
                    self.assertTrue(any(
                        attempt.get("method") == "commit-aware-manual-monitor-review"
                        and attempt.get("target") == (
                            f"simota/agent-skills@{WEEKLY_REVIEW_COMMIT}"
                        )
                        and attempt.get("result") == "success"
                        for attempt in self.payload["verification_attempts"]
                    ))

    def test_archived_skills_are_licensed_immutable_snapshots(self):
        for slug in ARCHIVED_SNAPSHOTS:
            with self.subTest(slug=slug):
                entry = self.entries[slug]
                origin = entry["origins"][0]
                tracking = origin["tracking"]
                self.assertEqual("snapshot", entry["kind"])
                self.assertEqual("local-only", entry["sync_mode"])
                self.assertEqual("fixed_ref", tracking["channel"])
                self.assertEqual(ARCHIVE_COMMIT, tracking["ref"])
                self.assertEqual(ARCHIVE_COMMIT, tracking["resolved_commit"])
                self.assertEqual("MIT", origin["license"])
                self.assertEqual(
                    f".archive/{slug}/SKILL.md",
                    origin["path"],
                )

    def test_every_file_has_one_owner_and_exact_hash_and_mode(self):
        for slug, entry in self.entries.items():
            with self.subTest(slug=slug):
                managed = {
                    item["path"]: item for item in entry["managed_files"]
                }
                artifact_owners: dict[str, int] = {}
                for origin in entry["origins"]:
                    for artifact in origin["artifacts"]:
                        artifact_owners[artifact["target"]] = (
                            artifact_owners.get(artifact["target"], 0) + 1
                        )
                self.assertEqual(set(managed), set(artifact_owners))
                self.assertTrue(
                    all(count == 1 for count in artifact_owners.values())
                )
                for relative, item in managed.items():
                    path = REPO_ROOT / relative
                    self.assertTrue(path.is_file(), relative)
                    self.assertFalse(path.is_symlink(), relative)
                    self.assertEqual(
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                        item["sha256"],
                    )
                    actual_mode = (
                        "100755"
                        if stat.S_IMODE(path.stat().st_mode) & 0o111
                        else "100644"
                    )
                    self.assertEqual(actual_mode, item["mode"])

    def test_duplicate_local_sidecars_are_not_retained(self):
        for slug, entry in self.entries.items():
            external_targets = {
                artifact["target"]
                for artifact in entry["origins"][0]["artifacts"]
            }
            external_signatures = {
                (
                    Path(target).name,
                    hashlib.sha256((REPO_ROOT / target).read_bytes()).hexdigest(),
                )
                for target in external_targets
            }
            for origin in entry["origins"][1:]:
                for artifact in origin["artifacts"]:
                    target = artifact["target"]
                    signature = (
                        Path(target).name,
                        hashlib.sha256(
                            (REPO_ROOT / target).read_bytes()
                        ).hexdigest(),
                    )
                    self.assertNotIn(
                        signature,
                        external_signatures,
                        f"{slug}: redundant local copy {target}",
                    )


if __name__ == "__main__":
    unittest.main()
