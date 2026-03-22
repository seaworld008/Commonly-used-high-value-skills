#!/usr/bin/env python3
"""Backward-compatible wrapper.

Deprecated: use scripts/validate_skill_sources.py
"""
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).with_name("validate_skill_sources.py")
    runpy.run_path(str(target), run_name="__main__")
