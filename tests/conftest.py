"""Provide a private test workspace on hosts that do not set TMPDIR.

Task runners already supply a sandbox-owned TMPDIR; preserve it exactly.
Ordinary Linux/CI pytest sessions use pytest's private session directory instead
of requiring a macOS environment variable or modifying global configuration.
"""
import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def private_skill_test_workspace(tmp_path_factory):
    original = os.environ.get("TMPDIR")
    if original:
        yield
        return
    workspace = tmp_path_factory.mktemp("skill-runtime")
    cached_tempdir = tempfile.tempdir
    os.environ["TMPDIR"] = str(workspace)
    tempfile.tempdir = None
    try:
        yield
    finally:
        tempfile.tempdir = cached_tempdir
        if original is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = original
