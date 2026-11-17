"""Offline CLI coverage: OFL is confined to reviewed, packaged font assets."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from scripts.audit_licenses import PERMISSIVE_LICENSES


REPO = Path(__file__).resolve().parents[1]
SKILL = "skills/category/example"
COMMIT = "a" * 40


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def font_tables():
    """One empty glyph, a family name and a valid format-0 character map."""
    head = bytearray(54)
    struct.pack_into(">I", head, 0, 0x10000)
    struct.pack_into(">I", head, 12, 0x5F0F3CF5)
    struct.pack_into(">H", head, 18, 1000)
    family = "Fixture".encode("utf-16-be")
    return {
        b"head": bytes(head),
        b"maxp": struct.pack(">IH", 0x10000, 1) + bytes(26),
        b"name": struct.pack(">3H6H", 0, 1, 18, 3, 1, 0x409, 1, len(family), 0) + family,
        b"cmap": struct.pack(">HHHHIHHH", 0, 1, 3, 1, 12, 0, 262, 0) + bytes(256),
        b"glyf": bytes(12), b"loca": struct.pack(">HH", 0, 6),
        b"hhea": struct.pack(">I", 0x10000) + bytes(30) + struct.pack(">H", 1),
        b"hmtx": struct.pack(">Hh", 500, 0),
    }


def synthetic_font(suffix=".ttf"):
    tables = font_tables()
    flavor = b"\0\1\0\0"
    if suffix == ".otf":
        flavor = b"OTTO"
        tables.pop(b"glyf")
        tables.pop(b"loca")
        tables[b"maxp"] = struct.pack(">IH", 0x5000, 1)
        # Name INDEX, Top DICT (CharStrings at byte 27), empty String and
        # Global Subr INDEXes, then a single endchar .notdef CharString.
        tables[b"CFF "] = (b"\x01\x00\x04\x04\x00\x01\x01\x01\x08Fixture"
                           b"\x00\x01\x01\x01\x03\xa6\x11\x00\x00\x00\x00"
                           b"\x00\x01\x01\x01\x02\x0e")
    count = len(tables)
    offset = (44 + 20 * count) if suffix == ".woff" else (12 + 16 * count)
    directory, payload = b"", b""
    original_size = 12 + 16 * count
    for tag, raw in sorted(tables.items()):
        original_size += (len(raw) + 3) & ~3
        if suffix == ".woff":
            encoded = zlib.compress(raw)
            if len(encoded) >= len(raw):
                encoded = raw
            directory += struct.pack(">4sIIII", tag, offset, len(encoded), len(raw), 0)
        else:
            encoded = raw
            directory += struct.pack(">4sIII", tag, 0, offset, len(raw))
        encoded += bytes((-len(encoded)) % 4)
        payload += encoded
        offset += len(encoded)
    if suffix == ".woff":
        header = struct.pack(">4s4sIHHIHHIIIII", b"wOFF", flavor, offset, count, 0,
                             original_size, 1, 0, 0, 0, 0, 0, 0)
    else:
        power = 1 << (count.bit_length() - 1)
        header = struct.pack(">4s4H", flavor, count, 16 * power,
                             power.bit_length() - 1, 16 * (count - power))
    return header + directory + payload


class ScopedFontLicenseTests(unittest.TestCase):
    def setUp(self):
        # Never fall back to a shared system temp directory in task runners.
        temp = tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"])
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.mapping = self.root / "docs/sources/fixture.skills.json"
        self.mapping.parent.mkdir(parents=True)
        self.notice = (REPO / "skills/product-design/canvas-design/canvas-fonts/WorkSans-OFL.txt").read_bytes()
        self.apache = (REPO / "skills/developer-engineering/mcp-builder/LICENSE.txt").read_bytes()
        self.put("SKILL.md", b"---\nname: example\nsource: https://github.com/fixture/upstream\nlicense: Apache-2.0\n---\n# Example\n")
        self.put("LICENSE.txt", self.apache)
        self.put("fonts/Fixture.ttf", synthetic_font())
        self.put("fonts/Fixture-OFL.txt", self.notice)
        self.code = self.origin("Apache-2.0", "LICENSE", self.apache, [
            ("skills/example/SKILL.md", "SKILL.md"), ("LICENSE", "LICENSE.txt"),
        ])
        self.font = self.origin("OFL-1.1", "fonts/Fixture-OFL.txt", self.notice, [
            ("fonts/Fixture.ttf", "fonts/Fixture.ttf"),
            ("fonts/Fixture-OFL.txt", "fonts/Fixture-OFL.txt"),
        ])
        self.entry = {
            "video_name": "Example", "normalized_slug": "example",
            "status": "verified_in_repo", "repo_skill": f"{SKILL}/SKILL.md",
            "source": "https://github.com/fixture/upstream", "notes": "Offline fixture",
            "kind": "overlay", "sync_mode": "monitor",
            "upstream": {"repo": "fixture/upstream", "path": "skills/example/SKILL.md",
                         "ref": "main", "sync_mode": "monitor", "last_checked_at": "2026-11-18",
                         "last_synced_at": "2026-11-18", "last_synced_commit": COMMIT},
            "origins": [self.code, self.font], "managed_files": [],
        }
        self.refresh_managed()

    def put(self, relative, raw):
        path = self.root / SKILL / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def origin(self, license_id, notice_path, raw, artifacts):
        return {
            "repo": "fixture/upstream", "path": "fonts" if license_id == "OFL-1.1" else "skills/example",
            "license": license_id, "sync_mode": "monitor",
            "artifacts": [{"type": "file", "source": source, "target": f"{SKILL}/{target}"}
                          for source, target in artifacts],
            "tracking": {
                "channel": "default_branch", "ref": "main", "resolved_commit": COMMIT,
                "path_commit": COMMIT, "content_sha256": digest(raw),
                "last_checked_at": "2026-11-18", "last_synced_at": "2026-11-18",
                "license_checkpoint": {
                    "path": notice_path, "spdx": license_id, "resolved_commit": COMMIT,
                    "content_sha256": digest(raw),
                    "blob_sha": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
                },
            },
        }

    def refresh_managed(self):
        self.entry["managed_files"] = [
            {"path": p.relative_to(self.root).as_posix(), "sha256": digest(p.read_bytes()),
             "owner": "example", "mode": "100644"}
            for p in sorted((self.root / SKILL).rglob("*")) if p.is_file() and not p.is_symlink()
        ]

    def run_gates(self, expected=0, contains=None):
        self.mapping.write_text(json.dumps({
            "schema_version": 2, "video": {}, "official_references": [], "skills": [self.entry],
        }))
        for script, flags in (("audit_licenses.py", ["--json"]), ("validate_skill_sources.py", [])):
            with self.subTest(gate=script):
                result = subprocess.run(
                    [sys.executable, "-B", str(REPO / "scripts" / script),
                     "--repo-root", str(self.root), "--mapping", "docs/sources/fixture.skills.json", *flags],
                    capture_output=True, text=True, cwd=self.root,
                )
                output = result.stdout + result.stderr
                self.assertEqual(expected, result.returncode, output)
                if contains:
                    self.assertIn(contains, output)

    def test_complete_ofl_with_synthetic_ttf_passes_both_clis(self):
        self.assertNotIn("OFL-1.1", PERMISSIVE_LICENSES)
        self.run_gates()

    def test_synthetic_otf_and_compressed_woff_pass(self):
        for suffix in (".otf", ".woff"):
            with self.subTest(suffix=suffix):
                old = self.root / self.font["artifacts"][0]["target"]
                old.unlink()
                self.put(f"fonts/Fixture{suffix}", synthetic_font(suffix))
                self.font["artifacts"][0].update(source=f"fonts/Fixture{suffix}", target=f"{SKILL}/fonts/Fixture{suffix}")
                self.refresh_managed()
                self.run_gates()

    def test_missing_font_and_missing_notice_fail(self):
        for relative in ("fonts/Fixture.ttf", "fonts/Fixture-OFL.txt"):
            with self.subTest(relative=relative):
                path = self.root / SKILL / relative
                raw = path.read_bytes()
                path.unlink()
                self.run_gates(1, "missing")
                path.write_bytes(raw)

    def test_unmapped_font_or_notice_and_missing_explicit_type_fail(self):
        artifacts = copy.deepcopy(self.font["artifacts"])
        for bad in ([artifacts[0]], [artifacts[1]], []):
            self.font["artifacts"] = bad
            self.run_gates(1, "OFL")
        self.font["artifacts"] = copy.deepcopy(artifacts)
        self.font["artifacts"][0].pop("type")
        self.run_gates(1, "explicit type=file")

    def test_unlisted_installed_font_is_not_hidden_by_a_valid_origin(self):
        self.put("fonts/Unmapped.ttf", synthetic_font())
        self.run_gates(1, "requires an explicit file artifact")

    def test_unlisted_symlink_and_directory_font_paths_fail(self):
        path = self.root / SKILL / "fonts/Unmapped.ttf"
        path.symlink_to(self.root / SKILL / "fonts/Fixture.ttf")
        self.run_gates(1, "regular file")
        path.unlink()
        path.mkdir()
        self.run_gates(1, "regular file")

    def test_mixed_directory_code_and_skill_entry_are_rejected(self):
        original = copy.deepcopy(self.font["artifacts"])
        for artifact in (
            {"type": "directory", "source": "fonts", "target": f"{SKILL}/fonts"},
            {"type": "file", "source": "run.py", "target": f"{SKILL}/run.py"},
            {"type": "file", "source": "SKILL.md", "target": f"{SKILL}/SKILL.md"},
        ):
            self.put("run.py", b"print(123)\n")
            self.font["artifacts"] = [*original, artifact]
            self.refresh_managed()
            self.run_gates(1, "OFL")

    def test_code_renamed_to_font_and_malformed_font_fail_after_rehash(self):
        for raw in (b"print(123)\n", b"\0\1\0\0" + bytes(80),
                    synthetic_font()[:100], b"wOFF" + bytes(80)):
            self.put("fonts/Fixture.ttf", raw)
            self.refresh_managed()
            self.run_gates(1, "OFL artifact")

    def test_font_table_bounds_and_glyph_locations_fail_after_rehash(self):
        good = synthetic_font()
        loca_index = sorted(font_tables()).index(b"loca")
        loca_offset = struct.unpack_from(">I", good, 12 + 16 * loca_index + 8)[0]
        for offset, raw in ((20, struct.pack(">I", len(good) + 4)), (6, b"\0\0"),
                            (loca_offset + 2, b"\xff\xff")):
            bad = bytearray(good)
            bad[offset:offset + len(raw)] = raw
            self.put("fonts/Fixture.ttf", bytes(bad))
            self.refresh_managed()
            self.run_gates(1, "OFL artifact")

    def test_changed_font_bytes_without_reviewed_checkpoint_fail(self):
        self.put("fonts/Fixture.ttf", synthetic_font() + b"changed")
        self.run_gates(1, "managed_files SHA-256")

    def test_wrong_or_truncated_ofl_body_fails_even_with_new_hashes(self):
        for body in (b"SPDX-License-Identifier: OFL-1.1\n", self.notice[:200],
                     self.notice.replace(b"may be sold by itself", b"may be sold freely"),
                     b"#!/usr/bin/python\nprint(123)\n" + self.notice, self.apache):
            self.put("fonts/Fixture-OFL.txt", body)
            self.font["tracking"]["license_checkpoint"] = self.origin(
                "OFL-1.1", "fonts/Fixture-OFL.txt", body, []) ["tracking"]["license_checkpoint"]
            self.refresh_managed()
            self.run_gates(1, "no upstream license body")

    def test_original_copyright_and_reserved_names_are_preserved_by_hash(self):
        renamed = self.notice.replace(b"Work Sans Project Authors", b"Replacement Font Authors")
        self.put("fonts/Fixture-OFL.txt", renamed)
        self.refresh_managed()
        self.run_gates(1, "license_checkpoint SHA-256")

    def test_reserved_font_name_notice_cannot_be_edited(self):
        body = (REPO / "skills/product-design/canvas-design/canvas-fonts/Italiana-OFL.txt").read_bytes()
        self.font["tracking"]["license_checkpoint"] = self.origin(
            "OFL-1.1", "fonts/Fixture-OFL.txt", body, [])["tracking"]["license_checkpoint"]
        self.put("fonts/Fixture-OFL.txt", body)
        self.refresh_managed()
        self.run_gates()
        self.put("fonts/Fixture-OFL.txt", body.replace(b'"Italiana"', b'"Renamed"'))
        self.refresh_managed()
        self.run_gates(1, "license_checkpoint SHA-256")

    def test_missing_copyright_cannot_pass_even_with_reviewed_full_body(self):
        body = self.notice[self.notice.index(b"SIL OPEN FONT LICENSE Version"):]
        self.put("fonts/Fixture-OFL.txt", body)
        self.font["tracking"]["license_checkpoint"] = self.origin(
            "OFL-1.1", "fonts/Fixture-OFL.txt", body, []) ["tracking"]["license_checkpoint"]
        self.refresh_managed()
        self.run_gates(1, "no upstream license body")

    def test_missing_cross_commit_and_wrong_blob_checkpoint_fail(self):
        checkpoint = self.font["tracking"].pop("license_checkpoint")
        self.run_gates(1, "missing license_checkpoint")
        self.font["tracking"]["license_checkpoint"] = checkpoint
        for field, value in (("resolved_commit", "b" * 40), ("blob_sha", "b" * 40), ("spdx", "Apache-2.0")):
            self.font["tracking"]["license_checkpoint"] = {**checkpoint, field: value}
            self.run_gates(1, "license_checkpoint")

    def test_unsafe_targets_symlink_fifo_and_cache_files_fail(self):
        artifact = self.font["artifacts"][0]
        original = artifact["target"]
        for target in ("../font.ttf", "LICENSE", f"{SKILL}/.data/Fixture.ttf", f"{SKILL}/__pycache__/Fixture.ttf"):
            artifact["target"] = target
            self.run_gates(1, "OFL")
        artifact["target"] = original
        font = self.root / original
        font.unlink()
        font.symlink_to(self.root / SKILL / "LICENSE.txt")
        self.run_gates(1, "regular file")
        font.unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(font)
            self.run_gates(1, "regular file")

    def test_shared_origin_ownership_and_unmapped_license_fail(self):
        self.code["artifacts"].append({"type": "directory", "source": "fonts", "target": f"{SKILL}/fonts"})
        self.run_gates(1, "exactly one origin owner")
        self.code["artifacts"].pop()
        self.font["artifacts"][1]["source"] = "other/OFL.txt"
        self.run_gates(1, "checkpointed license/notice")

    def test_ofl_cannot_replace_software_license_or_inhouse_exemption(self):
        self.code["license"] = "OFL-1.1"
        self.code["tracking"] = copy.deepcopy(self.font["tracking"])
        self.run_gates(1, "OFL")
        self.entry["origins"] = [self.font]
        self.font["repo"] = "local-repo/in-house"
        self.run_gates(1, "OFL requires an external reviewed font origin")

    def test_woffs_with_unsupported_or_malformed_containers_fail_closed(self):
        old = self.root / self.font["artifacts"][0]["target"]
        old.unlink()
        for suffix, raw in ((".woff2", b"wOF2" + bytes(80)), (".woff", b"wOFF" + bytes(80))):
            path = self.put(f"fonts/Fixture{suffix}", raw)
            self.font["artifacts"][0].update(source=f"fonts/Fixture{suffix}", target=f"{SKILL}/fonts/Fixture{suffix}")
            self.refresh_managed()
            self.run_gates(1, "OFL artifact")
            path.unlink()
    def test_each_family_needs_its_own_checkpointed_notice(self):
        second = copy.deepcopy(self.font)
        second["artifacts"][0].update(source="fonts/Second.ttf", target=f"{SKILL}/fonts/Second.ttf")
        second["artifacts"][1].update(source="fonts/Second-OFL.txt", target=f"{SKILL}/fonts/Second-OFL.txt")
        second["tracking"]["license_checkpoint"]["path"] = "fonts/Second-OFL.txt"
        self.put("fonts/Second.ttf", synthetic_font())
        other = self.notice.replace(b"Work Sans Project Authors", b"Second Fixture Authors")
        second["tracking"]["license_checkpoint"] = self.origin(
            "OFL-1.1", "fonts/Second-OFL.txt", other, []) ["tracking"]["license_checkpoint"]
        self.entry["origins"].append(second)
        self.refresh_managed()
        self.run_gates(1, "missing")
        self.put("fonts/Second-OFL.txt", other)
        self.refresh_managed()
        self.run_gates()


if __name__ == "__main__":
    unittest.main()
