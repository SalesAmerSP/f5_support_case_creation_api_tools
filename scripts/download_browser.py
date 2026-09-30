#!/usr/bin/env python3
"""Standalone script runner for F5 MyF5 Software Download Browser."""

import os
import sys

_SCRIPTS_DIR = os.path.abspath(os.path.dirname(__file__))
_SRC_DIR = os.path.abspath(os.path.join(_SCRIPTS_DIR, "..", "src"))

# Avoid self-importing scripts/download_browser.py
while _SCRIPTS_DIR in sys.path:
    sys.path.remove(_SCRIPTS_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from download_browser import main

if __name__ == "__main__":
    sys.exit(main() or 0)
