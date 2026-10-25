#!/usr/bin/env python3
"""Runner script in sample_data directory."""

from pathlib import Path
import sys

# Delegate to root run_sample.py
root_run_sample = Path(__file__).resolve().parent.parent / "run_sample.py"
if root_run_sample.exists():
    with open(root_run_sample, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, str(root_run_sample), "exec"))
