"""Original MIT-licensed regression fixtures; no network/package execution.

Fixtures honor the task TMPDIR (standard tempfile fallback on ordinary CI).
These are local filesystem tests, not a claim that real npm installations or
the bundle integration were tested.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "skills/developer-engineering/web-artifacts-builder/scripts/collect-runtime-notices.mjs"
SECRET = b"DO_NOT_READ_EXTERNAL_SECRET_7f0d"


@pytest.fixture
def sandbox():
    with tempfile.TemporaryDirectory(prefix="runtime-notices-", dir=os.environ.get("TMPDIR")) as folder:
        yield Path(folder).resolve()


def write_json(file, value):
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value), encoding="utf-8")


def project(sandbox, **fields):
    folder = sandbox / "project"
    write_json(folder / "package.json", {"name": "fixture", **fields})
    return folder


def package(folder, name="dep", version="1.0.0", notice=b"Fixture copyright and complete test terms.\n", **fields):
    write_json(folder / "package.json", {"name": name, "version": version, **fields})
    if notice is not None:
        (folder / "LICENSE").write_bytes(notice)
    return folder


def collect(folder, extra="", env=None, supplemental=None):
    # Load test-owned supplemental data before instrumentation, keeping large
    # negative fixtures out of the operating system's argv size limit.
    supplied = folder.parent / "supplemental-fixture.json"
    supplied.write_text(json.dumps(supplemental or []), encoding="utf-8")
    # Import first so instrumentation observes only the public API's IO.
    script = f"""
import fs from 'node:fs';
import {{ collectRuntimeNotices }} from {json.dumps(MODULE.as_uri())};
const project = {json.dumps(str(folder))};
const supplements = JSON.parse(fs.readFileSync({json.dumps(str(supplied))}, "utf8"));
const opened = new Map(), reads = [];
let directories = 0;
let leaked = false;
const open = fs.openSync, read = fs.readSync, close = fs.closeSync;
const opendir = fs.opendirSync;
fs.opendirSync = p => {{
  const dir = opendir(p); directories++;
  const closeDir = dir.closeSync.bind(dir);
  dir.closeSync = () => {{ try {{ return closeDir(); }} finally {{ directories--; }} }};
  return dir;
}};
fs.openSync = (p, flags, ...rest) => {{
  const fd = open(p, flags, ...rest); opened.set(fd, String(p)); return fd;
}};
fs.readSync = (fd, buffer, offset, length, position) => {{
  reads.push(opened.get(fd));
  const n = read(fd, buffer, offset, length, position);
  if (buffer.subarray(offset, offset+n).includes(Buffer.from({json.dumps(SECRET.decode())}))) leaked = true;
  return n;
}};
fs.closeSync = fd => {{ opened.delete(fd); return close(fd); }};
{extra}
try {{
  const notices = collectRuntimeNotices(project, supplements);
  console.log(JSON.stringify({{ok:true, notices, diagnostics:notices.diagnostics, reads, leaked, handles:opened.size+directories}}));
}} catch (error) {{
  console.log(JSON.stringify({{ok:false, error:error.message, reads, leaked, handles:opened.size+directories}}));
}}
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script], cwd=ROOT,
        capture_output=True, text=True, timeout=30,
        env={**os.environ, **(env or {})},
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    result["stderr"] = completed.stderr
    assert result["handles"] == 0
    assert not result["leaked"], "collector read an external secret"
    assert SECRET.decode() not in completed.stdout + completed.stderr
    return result


def rejected(result, fragment):
    assert not result["ok"], result
    assert fragment in result["error"], result


def test_import_does_no_io_and_direct_execution_does_nothing():
    script = f"""
import fs from 'node:fs';
const source = fs.readFileSync({json.dumps(str(MODULE))}, 'utf8');
for (const name of ['readSync','readFileSync','openSync','opendirSync','lstatSync']) {{
  fs[name] = () => {{ throw new Error('import performed IO'); }};
}}
const mod = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
if (typeof mod.collectRuntimeNotices !== 'function') throw new Error('missing export');
"""
    run = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    run = subprocess.run(["node", str(MODULE)], capture_output=True, text=True, timeout=10)
    assert run.returncode == 0 and run.stdout == "" and run.stderr == ""


def test_npm_closure_peer_optional_dev_and_original_bytes(sandbox):
    root = project(sandbox, dependencies={"react": "*"}, optionalDependencies={"available": "*", "absent": "*"}, devDependencies={"build-tool": "*"})
    body = b"\xff\x00Copyright\r\n</template><script>untrusted notice</script>\n"
    package(root / "node_modules/react", "react", notice=body, dependencies={"scheduler": "*"}, peerDependencies={"peer": "*", "missing-peer": "*"}, devDependencies={"private-dev": "*"})
    package(root / "node_modules/scheduler", "scheduler")
    package(root / "node_modules/peer", "peer")
    package(root / "node_modules/available", "available")
    package(root / "node_modules/build-tool", "build-tool", notice=SECRET)
    package(root / "node_modules/private-dev", "private-dev", notice=SECRET)
    (root / "node_modules/react/NOTICE.md").write_bytes(b"Additional complete attribution\n")
    result = collect(root)
    assert result["ok"], result
    assert [item["package"] for item in result["notices"]] == ["available", "react", "react", "peer", "scheduler"]
    item = next(item for item in result["notices"] if item["package"] == "react" and item["name"] == "LICENSE")
    assert item == {"name": "LICENSE", "package": "react", "version": "1.0.0", "encoding": "base64", "content": base64.b64encode(body).decode()}
    assert {item["code"] for item in result["diagnostics"]} == {"RUNTIME_NOTICE_OPTIONAL_MISSING", "RUNTIME_NOTICE_PEER_MISSING"}
    assert "RUNTIME_NOTICE_OPTIONAL_MISSING" in result["stderr"]
    assert "RUNTIME_NOTICE_PEER_MISSING" in result["stderr"]
    assert collect(root)["notices"] == result["notices"]


def test_dev_only_needs_no_node_modules_and_does_not_inspect_dev_fields(sandbox):
    root = project(sandbox, devDependencies=["intentionally ignored"])
    result = collect(root)
    assert result["ok"] and result["notices"] == [] and set(result["reads"]) == {str(root / "package.json")}


def test_optional_override_and_all_optional_missing(sandbox):
    root = project(sandbox, dependencies={"absent": "*"}, optionalDependencies={"absent": "*"})
    result = collect(root)
    assert result["ok"] and result["notices"] == []
    assert result["diagnostics"] == [{"code": "RUNTIME_NOTICE_OPTIONAL_MISSING", "package": "absent", "from": "project"}]


def test_pnpm_scoped_symlinks_aliases_cycles_and_peer_lookup(sandbox):
    root = project(sandbox, dependencies={"alias": "npm:@scope/a@1", "@scope/a": "1"})
    nm = root / "node_modules"
    a = package(nm / ".pnpm/@scope+a@1.0.0/node_modules/@scope/a", "@scope/a", dependencies={"b": "*"}, peerDependencies={"peer": "*"})
    b = package(nm / ".pnpm/b@2.0.0/node_modules/b", "b", "2.0.0", dependencies={"@scope/a": "*"})
    peer = package(nm / ".pnpm/peer@1.0.0/node_modules/peer", "peer")
    (nm / "@scope").mkdir()
    (nm / "@scope/a").symlink_to(os.path.relpath(a, nm / "@scope"))
    (nm / "alias").symlink_to(a)
    (a.parent.parent / "b").symlink_to(os.path.relpath(b, a.parent.parent))
    (a.parent.parent / "peer").symlink_to(os.path.relpath(peer, a.parent.parent))
    (b.parent / "@scope").mkdir()
    (b.parent / "@scope/a").symlink_to(a)
    # A dependency beside the virtual package must precede a root hoisted copy.
    package(nm / "b", "b", "9.0.0")
    result = collect(root)
    assert result["ok"], result
    assert [(item["package"], item["version"]) for item in result["notices"]] == [("@scope/a", "1.0.0"), ("b", "2.0.0"), ("peer", "1.0.0")]


def test_nearest_npm_copy_and_distinct_versions(sandbox):
    root = project(sandbox, dependencies={"a": "*", "b": "*"})
    a = package(root / "node_modules/a", "a", dependencies={"b": "*"})
    package(a / "node_modules/b", "b", "2.0.0")
    package(root / "node_modules/b", "b", "1.0.0")
    result = collect(root)
    assert result["ok"], result
    assert [(n["package"], n["version"]) for n in result["notices"]] == [("a", "1.0.0"), ("b", "2.0.0"), ("b", "1.0.0")]


def test_package_exports_main_plugins_and_scripts_are_never_executed(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    marker = sandbox / "executed"
    executable = f"require('fs').writeFileSync({json.dumps(str(marker))}, 'executed'); throw Error('executed package code');"
    dep = package(root / "node_modules/dep", main="index.cjs", exports="./index.cjs", plugins=["./index.cjs"], scripts={"postinstall": "node index.cjs"})
    (dep / "index.cjs").write_text(executable)
    result = collect(root)
    assert result["ok"], result
    assert not marker.exists()
    assert all(not item.endswith("index.cjs") for item in result["reads"])


def test_missing_transitive_required_dependency_names_importer(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    package(root / "node_modules/dep", dependencies={"missing": "*"})
    rejected(collect(root), "missing (from dep@1.0.0): missing required")


def test_missing_child_in_valid_internal_scope_link_is_optional(sandbox):
    root = project(sandbox, optionalDependencies={"@scope/absent": "*"})
    nm = root / "node_modules"
    (nm / "scope-content").mkdir(parents=True)
    (nm / "@scope").symlink_to("scope-content")
    result = collect(root)
    assert result["ok"] and result["notices"] == []
    assert result["diagnostics"][0]["code"] == "RUNTIME_NOTICE_OPTIONAL_MISSING"


def test_symlink_before_dotdot_uses_actual_filesystem_semantics(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    nm = root / "node_modules"
    package(nm / "target", "target", "1.0.0")
    actual = package(nm / "sub/target", "target", "2.0.0")
    (nm / "sub/tree").mkdir()
    (nm / "bridge").symlink_to("sub/tree")
    (nm / "dep").symlink_to("bridge/../target")
    assert (nm / "dep").resolve() == actual
    result = collect(root)
    assert result["ok"], result
    assert [(item["package"], item["version"]) for item in result["notices"]] == [("target", "2.0.0")]


def test_outside_symlink_before_dotdot_cannot_be_lexically_erased(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    nm = root / "node_modules"
    package(nm / "target", "target")
    outside = package(sandbox / "outside/target", "target", notice=SECRET)
    (sandbox / "outside/tree").mkdir()
    (nm / "bridge").symlink_to(sandbox / "outside/tree")
    (nm / "dep").symlink_to("bridge/../target")
    assert (nm / "dep").resolve() == outside
    rejected(collect(root), "symlink escapes")


def test_missing_required_does_not_search_parent_or_node_path(sandbox):
    root = project(sandbox, dependencies={"missing": "*"})
    package(sandbox / "node_modules/missing", "missing", notice=SECRET)
    global_nm = sandbox / "global"
    package(global_nm / "missing", "missing", notice=SECRET)
    result = collect(root, env={"NODE_PATH": str(global_nm)})
    rejected(result, "missing (from project): missing required")
    assert set(result["reads"]) == {str(root / "package.json")}


@pytest.mark.parametrize("raw", [b"{not-json", b"[]", b"null", b'"text"', b"\xff"])
def test_malformed_project_json_without_content_in_errors(sandbox, raw):
    root = project(sandbox)
    (root / "package.json").write_bytes(raw + (SECRET if raw == b"{not-json" else b""))
    # This sentinel is intentionally inside the selected manifest: suppress the
    # external-secret read assertion while still requiring a redacted error.
    result = collect(root, "fs.readSync = read;")
    rejected(result, "package.json")
    assert "not-json" not in result["error"]


@pytest.mark.parametrize("field", ["dependencies", "optionalDependencies", "peerDependencies"])
@pytest.mark.parametrize("value", [None, [], "dep", 1, True])
def test_dependency_fields_must_be_objects(sandbox, field, value):
    result = collect(project(sandbox, **{field: value}))
    rejected(result, f"{field} must be an object")


@pytest.mark.parametrize("name", ["../secret", "@scope/../../secret", "/absolute", "a\\secret", "a%2fsecret", "@s/a/b", ".env", "_private", "a\x00b", "a\nb", "dep\n", "@scope/dep\n", "C:secret", "node_modules", "@scope/node_modules", "x" * 215])
def test_malicious_dependency_names_rejected_before_lookup(sandbox, name):
    root = project(sandbox, dependencies={name: "*"})
    result = collect(root)
    rejected(result, "invalid package name")
    assert set(result["reads"]) == {str(root / "package.json")}


@pytest.mark.parametrize("spec", [None, 3, {}, [], "", " " , "x" * 4097])
def test_bad_dependency_spec(sandbox, spec):
    rejected(collect(project(sandbox, dependencies={"dep": spec})), "invalid dependency spec for dep")


@pytest.mark.parametrize("metadata", [{"name": "../escape"}, {"name": None}, {"version": None}, {"version": "not-a-version"}, {"version": "1.0.0\nsecret"}, {"version": "1.0.0\n"}])
def test_bad_installed_identity(sandbox, metadata):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    write_json(dep / "package.json", {"name": "dep", "version": "1.0.0", **metadata})
    rejected(collect(root), "invalid installed package")


def test_installed_malformed_json_and_nonobject_deps(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    (dep / "package.json").write_bytes(b"{broken")
    rejected(collect(root), "dep (from project): invalid package.json")
    write_json(dep / "package.json", {"name": "dep", "version": "1.0.0", "dependencies": []})
    rejected(collect(root), "dependencies must be an object")


def test_no_license_string_or_arbitrary_field_paths(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep", notice=None, license="SEE LICENSE IN ../../.env", licenses=[{"file": "../../.env", "type": "MIT"}])
    (root / ".env").write_bytes(SECRET)
    (dep / "license.json").write_bytes(SECRET)
    (dep / "LICENSE\n").write_bytes(SECRET)
    (dep / ".env").write_bytes(SECRET)
    rejected(collect(root), "dep@1.0.0 (requested as dep): missing license/notice body")


def test_fixed_names_copy_complete_mit_apache_bsd_and_ignore_nested_files(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep", notice=None)
    fixtures = {"LICENSE-MIT": b"MIT fixture\ncomplete terms\n", "LICENCE.txt": b"BSD fixture\nall conditions\n", "NOTICE.md": b"Apache fixture attribution\n", "COPYING": b"Complete copying terms\n", "license-apache-2.0.md": b"Apache fixture\ncomplete terms\n"}
    for name, body in fixtures.items():
        (dep / name).write_bytes(body)
    (dep / "nested").mkdir()
    (dep / "nested/LICENSE").write_bytes(SECRET)
    result = collect(root)
    assert result["ok"], result
    assert [item["name"] for item in result["notices"]] == sorted(fixtures)
    assert {item["name"]: base64.b64decode(item["content"]) for item in result["notices"]} == fixtures


def test_complete_real_license_texts_are_preserved_without_reclassification(sandbox):
    root = project(sandbox, dependencies={"mit": "*", "apache": "*", "bsd": "*"})
    # Existing complete repository notices supply MIT/Apache fixture text. No
    # shortened boilerplate or inferred/generated license replaces these bytes.
    mit = (ROOT / "LICENSE").read_bytes()
    apache = (MODULE.parent.parent / "LICENSE.txt").read_bytes()
    bsd = b"""BSD 3-Clause License

Copyright (c) 2026 seaworld008
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
    bodies = {"mit": mit, "apache": apache, "bsd": bsd}
    for name, body in bodies.items():
        package(root / "node_modules" / name, name, notice=body)
    result = collect(root)
    assert result["ok"], result
    assert {item["package"]: base64.b64decode(item["content"]) for item in result["notices"]} == bodies


@pytest.mark.parametrize("where", ["package", "scope", "nested-node-modules", "root-node-modules", "workspace-inside-project", "outside-and-back"])
def test_package_ancestor_symlinks_cannot_escape_node_modules(sandbox, where):
    root = project(sandbox, dependencies={"@scope/dep" if where == "scope" else "dep": "*"})
    outside = package(sandbox / "outside", notice=SECRET)
    nm = root / "node_modules"
    nm.mkdir(exist_ok=True)
    if where == "package":
        (nm / "dep").symlink_to(outside)
    elif where == "scope":
        (nm / "@scope").symlink_to(outside)
    elif where == "root-node-modules":
        nm.rmdir()
        nm.symlink_to(outside)
    elif where == "workspace-inside-project":
        internal = package(root / "workspace", notice=SECRET)
        (nm / "dep").symlink_to(internal)
    elif where == "outside-and-back":
        actual = package(nm / "actual")
        (outside / "return").symlink_to(actual)
        (nm / "dep").symlink_to(outside / "return")
    else:
        dep = package(nm / "dep", dependencies={"child": "*"})
        (dep / "node_modules").symlink_to(outside)
    result = collect(root)
    rejected(result, "symlink" if where != "root-node-modules" else "root must be")
    assert all(str(outside) not in item for item in result["reads"])


@pytest.mark.parametrize("name", ["LICENSE", "package.json"])
@pytest.mark.parametrize("kind", ["symlink", "fifo", "directory", "oversize", "empty"])
def test_candidate_files_must_be_safe_regular_bounded_files(sandbox, name, kind):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    target = dep / name
    target.unlink()
    if kind == "symlink":
        outside = sandbox / "secret"
        outside.write_bytes(SECRET)
        target.symlink_to(outside)
    elif kind == "fifo":
        os.mkfifo(target)
    elif kind == "directory":
        target.mkdir()
    else:
        target.write_bytes(b"x" * (1024 * 1024 + 1) if kind == "oversize" else b"")
    result = collect(root)
    assert not result["ok"], result
    assert str(target) not in result["reads"]


def test_package_directory_fifo_and_dangling_symlink_are_not_absent_optionals(sandbox):
    root = project(sandbox, optionalDependencies={"dep": "*"})
    nm = root / "node_modules"
    nm.mkdir()
    os.mkfifo(nm / "dep")
    rejected(collect(root), "not a directory")
    (nm / "dep").unlink()
    (nm / "dep").symlink_to(nm / "absent")
    rejected(collect(root), "dangling")


def test_file_symlink_to_another_internal_notice_is_still_rejected(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    (dep / "NOTICE").write_bytes(b"Complete fixture attribution")
    (dep / "LICENSE").unlink()
    (dep / "LICENSE").symlink_to("NOTICE")
    rejected(collect(root), "symlink in file path")


@pytest.mark.parametrize("kind", ["fifo", "directory", "oversize"])
def test_project_manifest_has_the_same_safe_read_requirements(sandbox, kind):
    root = project(sandbox)
    file = root / "package.json"
    file.unlink()
    if kind == "fifo":
        os.mkfifo(file)
    elif kind == "directory":
        file.mkdir()
    else:
        file.write_bytes(b"x" * (1024 * 1024 + 1))
    result = collect(root)
    assert not result["ok"] and result["reads"] == []


def test_installed_optional_without_notice_is_fatal(sandbox):
    root = project(sandbox, optionalDependencies={"dep": "*"})
    package(root / "node_modules/dep", notice=None)
    rejected(collect(root), "missing license/notice body")


def test_flags_short_reads_and_permission_error(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    package(root / "node_modules/dep")
    extra = """
const observedOpen = fs.openSync;
fs.openSync = (p, flags, ...rest) => {
  if (!(flags & fs.constants.O_NOFOLLOW) || !(flags & fs.constants.O_NONBLOCK)) throw new Error('unsafe open');
  return observedOpen(p, flags, ...rest);
};
const observedRead = fs.readSync;
fs.readSync = (fd,b,o,l,p) => observedRead(fd,b,o,Math.min(l,3),p);
"""
    assert collect(root, extra)["ok"]
    extra = """
const observedOpen = fs.openSync;
fs.openSync = (p, flags, ...rest) => {
  if (String(p).endsWith('/LICENSE')) { const e = new Error('sensitive path omitted'); e.code = 'EACCES'; throw e; }
  return observedOpen(p, flags, ...rest);
};
"""
    rejected(collect(root, extra), "dep@1.0.0/LICENSE: filesystem operation failed (EACCES)")


def test_actual_permission_denial(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    file = dep / "LICENSE"
    file.chmod(0)
    try:
        if os.access(file, os.R_OK):
            pytest.skip("current OS identity bypasses mode-bit read denial")
        rejected(collect(root), "EACCES")
    finally:
        file.chmod(0o600)


@pytest.mark.parametrize("kind", ["grow", "shrink", "io-error"])
def test_read_mutation_and_io_failure_abort_and_close_descriptor(sandbox, kind):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    extra = f"""
const observedRead = fs.readSync;
let modified = false;
fs.readSync = (fd, ...args) => {{
  if (!modified && opened.get(fd) === {json.dumps(str(dep / 'LICENSE'))}) {{
    modified = true;
    const kind = {json.dumps(kind)};
    if (kind === 'grow') fs.appendFileSync({json.dumps(str(dep / 'LICENSE'))}, 'extra');
    else if (kind === 'shrink') fs.truncateSync({json.dumps(str(dep / 'LICENSE'))}, 1);
    else {{ const e = new Error('private contents omitted'); e.code = 'EIO'; throw e; }}
  }}
  return observedRead(fd, ...args);
}};
"""
    result = collect(root, extra)
    rejected(result, "EIO" if kind == "io-error" else "file changed during read")


@pytest.mark.parametrize("race", ["leaf", "ancestor"])
def test_open_time_symlink_replacement_does_not_read_external_payload(sandbox, race):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    outside = package(sandbox / "outside", notice=SECRET)
    extra = f"""
const observedOpen = fs.openSync;
fs.openSync = (p, flags, ...rest) => {{
  if (String(p).endsWith('/LICENSE')) {{
    if ({json.dumps(race)} === 'leaf') {{ fs.unlinkSync(p); fs.symlinkSync({json.dumps(str(outside / 'LICENSE'))}, p); }}
    else {{ fs.renameSync({json.dumps(str(dep))}, {json.dumps(str(dep) + '-old')}); fs.symlinkSync({json.dumps(str(outside))}, {json.dumps(str(dep))}); }}
  }}
  return observedOpen(p, flags, ...rest);
}};
"""
    result = collect(root, extra)
    assert not result["ok"], result
    assert not any(item.endswith("/LICENSE") for item in result["reads"])


def test_manifest_symlink_project_is_rejected_without_payload_read(sandbox):
    root = project(sandbox)
    (root / "package.json").unlink()
    outside = sandbox / "secret"
    outside.write_bytes(SECRET)
    (root / "package.json").symlink_to(outside)
    result = collect(root)
    rejected(result, "symlink")
    assert result["reads"] == []


def test_depth_limit_and_cycle_without_unbounded_recursion(sandbox):
    root = project(sandbox, dependencies={"p0": "*"})
    for n in range(65):
        package(root / f"node_modules/p{n}", f"p{n}", dependencies={f"p{n+1}": "*"})
    rejected(collect(root), "depth limit")
    shutil.rmtree(root / "node_modules")
    package(root / "node_modules/p0", "p0", dependencies={"p0": "*"})
    result = collect(root)
    assert result["ok"] and len(result["notices"]) == 1


def test_symlink_cycle_is_bounded(sandbox):
    root = project(sandbox, dependencies={"a": "*"})
    nm = root / "node_modules"
    nm.mkdir()
    (nm / "a").symlink_to("b")
    (nm / "b").symlink_to("a")
    rejected(collect(root), "symlink limit")


def test_package_count_limit(sandbox):
    root = project(sandbox, dependencies={f"p{n}": "*" for n in range(1025)})
    for n in range(1025):
        package(root / f"node_modules/p{n}", f"p{n}")
    rejected(collect(root), "package count limit")


def test_dependency_edge_limit(sandbox):
    root = project(sandbox, optionalDependencies={f"p{n}": "*" for n in range(8193)})
    rejected(collect(root), "edge limit")


def test_directory_entry_limit(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    for n in range(4095):
        (dep / f"unused-{n}").touch()
    rejected(collect(root), "directory entry limit")


def case_variants(text):
    for mask in range(1 << len(text)):
        yield "".join(c.upper() if mask & (1 << i) else c.lower() for i, c in enumerate(text))


def test_notice_file_count_limit_portably_without_case_sensitive_fs(sandbox):
    root = project(sandbox, dependencies={"dep": "*"})
    dep = package(root / "node_modules/dep")
    # Mock directory entries, not file reads: macOS volumes may fold filename case.
    extra = f"""
const observedDir = fs.opendirSync;
fs.opendirSync = p => {{
  if (String(p) !== {json.dumps(str(dep))}) return observedDir(p);
  const names = {json.dumps(list(case_variants('license'))[:65])};
  return {{readSync:()=>names.length ? {{name:names.shift()}} : null, closeSync:()=>{{}}}};
}};
"""
    rejected(collect(root, extra), "notice file count per package")


def test_total_byte_limit_includes_manifests(sandbox):
    root = project(sandbox, dependencies={f"p{n}": "*" for n in range(33)})
    body = b"Complete test license terms\n" + b"x" * (1024 * 1024 - 28)
    assert len(body) <= 1024 * 1024
    for n in range(33):
        package(root / f"node_modules/p{n}", f"p{n}", notice=body)
    rejected(collect(root), "total byte limit")


def test_global_file_count_limit(sandbox):
    root = project(sandbox, dependencies={f"p{n}": "*" for n in range(900)})
    for n in range(900):
        dep = package(root / f"node_modules/p{n}", f"p{n}")
        for filename in ["NOTICE", "COPYING", "LICENCE"]:
            (dep / filename).write_bytes(b"Complete fixture attribution and terms")
    rejected(collect(root), "file count limit")


def reviewed_notice(name="dep", version="1.0.0"):
    raw = b"Original synthetic notice for fallback contract testing.\n"
    return {"package": name, "version": version, "name": "LICENSE", "encoding": "base64",
            "content": base64.b64encode(raw).decode(), "sha256": hashlib.sha256(raw).hexdigest(),
            "source": {"repo": "example/publisher", "commit": "a" * 40, "path": "LICENSE"}}


def test_exact_version_reviewed_notice_fills_missing_body_only(sandbox):
    root = project(sandbox, dependencies={"dep": "1"})
    package(root / "node_modules/dep", notice=None)
    source = reviewed_notice()
    result = collect(root, supplemental=[source])
    assert result["ok"], result
    assert result["notices"][0]["content"] == source["content"]
    assert result["notices"][0]["source"] == source["source"]
    wrong = reviewed_notice(version="2.0.0")
    rejected(collect(root, supplemental=[wrong]), "missing license/notice body")
    rejected(collect(root, supplemental=[reviewed_notice(name="another")]), "missing license/notice body")
    # Actual installed attribution and the reviewed full grant are both retained.
    (root / "node_modules/dep/LICENSE").write_bytes(b"Actual installed publisher notice")
    result = collect(root, supplemental=[source])
    assert base64.b64decode(result["notices"][0]["content"]) == b"Actual installed publisher notice"
    assert any(item["content"] == source["content"] for item in result["notices"])


@pytest.mark.parametrize("change", ["digest", "base64", "duplicate", "name", "version", "filename", "size", "count"])
def test_reviewed_notice_integrity_and_bounds_fail_closed(sandbox, change):
    root = project(sandbox, dependencies={"dep": "1"})
    package(root / "node_modules/dep", notice=None)
    source = reviewed_notice()
    records = [source]
    if change == "digest": source["sha256"] = "0" * 64
    if change == "base64": source["content"] = "!!!"
    if change == "duplicate": records.append(dict(source))
    if change == "name": source["package"] = "../secret"
    if change == "version": source["version"] = "not-a-version"
    if change == "filename": source["name"] = "../../private.env"
    if change == "size": source["content"] = "a" * (2 * 1024 * 1024)
    if change == "count": records = [source] * 1025
    result = collect(root, supplemental=records)
    rejected(result, "supplements:")
    assert not result["leaked"]


def test_added_notice_preserves_real_exact_version_publisher_grant(sandbox):
    publisher = json.loads((MODULE.parent / "runtime-license-notices.json").read_text())
    source = next(item for item in publisher["notices"] if item["package"] == "@radix-ui/react-accordion" and item["version"] == "1.2.2")
    root = project(sandbox, dependencies={source["package"]:source["version"]})
    folder = package(root / "node_modules" / source["package"], source["package"], source["version"], notice=None)
    (folder / "NOTICE").write_bytes(b"Additional integration attribution.\n")
    result = collect(root, supplemental=[source])
    assert result["ok"], result
    assert any(item["content"] == source["content"] for item in result["notices"])
    assert any(item["name"] == "NOTICE" and base64.b64decode(item["content"]) == b"Additional integration attribution.\n" for item in result["notices"])
    # Byte-identical full terms can be retained once without losing content.
    (folder / "NOTICE").write_bytes(base64.b64decode(source["content"]))
    result = collect(root, supplemental=[source])
    assert len(result["notices"]) == 1 and result["notices"][0]["content"] == source["content"]
