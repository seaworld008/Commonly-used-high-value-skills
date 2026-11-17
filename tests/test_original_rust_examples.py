"""Compile the original SKILL.md examples, including deliberate type errors.

No copied fixtures, Cargo dependencies, toolchain installation, or network access.
Temporary source files and binaries follow TMPDIR when the host supplies it.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest


SKILL = (Path(__file__).resolve().parents[1]
         / "skills/developer-engineering/rust-engineer/SKILL.md")
RUNNABLE = {
    "borrowed_record": 4,
    "scoped_cancellation": 3,
    "foreign_snapshot": 2,
}
REJECTED = {
    "overlapping_borrows": "E0502",
    "non_send_thread": "E0277",
}


@pytest.fixture(scope="module")
def examples():
    blocks = re.findall(r"^```(rust(?:,compile_fail)?)\n(.*?)^```\s*$",
                        SKILL.read_text(encoding="utf-8"), re.M | re.S)
    found = {}
    for mode, source in blocks:
        marker = re.match(r"// example: ([a-z_]+)\n", source)
        assert marker, "Every Rust example needs an extraction marker"
        name = marker.group(1)
        assert name not in found, f"Duplicate example: {name}"
        found[name] = (mode, source)
    assert set(found) == set(RUNNABLE) | set(REJECTED)
    return found


@pytest.fixture(scope="module")
def rustc():
    compiler = shutil.which("rustc")
    if compiler is None:
        pytest.skip("rustc unavailable; Rust examples were not compiled or run")
    version = subprocess.run([compiler, "--version"], capture_output=True,
                             text=True, timeout=30, check=False,
                             env=dict(os.environ, RUSTUP_AUTO_INSTALL="0"))
    if version.returncode:
        pytest.skip("rustc cannot run; examples unverified: " + version.stderr.strip())
    return compiler


@pytest.fixture
def workdir():
    # Explicit dir avoids macOS tools silently choosing a shared temp directory.
    with tempfile.TemporaryDirectory(prefix="original-rust-",
                                     dir=os.environ.get("TMPDIR")) as directory:
        yield Path(directory)


def invoke(arguments, workdir):
    env = dict(os.environ, TMPDIR=str(workdir), RUSTUP_AUTO_INSTALL="0")
    return subprocess.run(arguments, cwd=workdir, env=env, capture_output=True,
                          text=True, timeout=60, check=False)


@pytest.mark.parametrize("name", RUNNABLE)
def test_original_examples_compile_and_run(name, examples, rustc, workdir):
    mode, source = examples[name]
    assert mode == "rust"
    path = workdir / f"{name}.rs"
    path.write_text(source, encoding="utf-8")
    binary = workdir / name
    # Edition-neutral examples: do not change a project's edition or toolchain.
    compiled = invoke([rustc, "--test", "-Dwarnings", str(path), "-o", str(binary)],
                      workdir)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    tested = invoke([str(binary)], workdir)
    assert tested.returncode == 0, tested.stdout + tested.stderr
    assert f"{RUNNABLE[name]} passed; 0 failed" in tested.stdout


@pytest.mark.parametrize("name", REJECTED)
def test_original_counterexamples_fail_for_expected_reason(name, examples, rustc, workdir):
    mode, source = examples[name]
    assert mode == "rust,compile_fail"
    path = workdir / f"{name}.rs"
    path.write_text(source, encoding="utf-8")
    compiled = invoke([rustc, str(path), "-o", str(workdir / name)], workdir)
    assert compiled.returncode != 0, "Compiler accepted a documented invalid program"
    assert f"error[{REJECTED[name]}]" in compiled.stderr, compiled.stderr
