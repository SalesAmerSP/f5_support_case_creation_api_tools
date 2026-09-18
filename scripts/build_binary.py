#!/usr/bin/env python3
"""Build script for compiling qkviewmgr into a standalone, single-file binary.

Zero Python or runtime dependencies required by end users running the binary.
"""

import os
import subprocess
import sys


def main():
    print("=" * 65)
    print("       qkviewmgr Standalone Binary Compilation Script")
    print("=" * 65)

    # 1. Verify PyInstaller presence
    try:
        import PyInstaller
        print(f"✓ Found PyInstaller version {PyInstaller.__version__}")
    except ImportError:
        print("\nPyInstaller is not installed in the active environment.")
        print("To install PyInstaller:")
        print("    pip install pyinstaller")
        print("Or run in a virtual environment:")
        print("    python3 -m venv .venv && source .venv/bin/activate && pip install pyinstaller")
        sys.exit(1)

    spec_file = os.path.abspath("qkviewmgr.spec")
    if not os.path.isfile(spec_file):
        print(f"Error: Spec file not found at {spec_file}")
        sys.exit(1)

    print(f"\nBuilding binary using {spec_file}...")
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec_file]
    proc = subprocess.run(cmd)

    if proc.returncode != 0:
        print(f"\nBuild failed with exit code {proc.returncode}")
        sys.exit(proc.returncode)

    dist_bin = os.path.join("dist", "qkviewmgr")
    if sys.platform == "win32":
        dist_bin += ".exe"

    if os.path.isfile(dist_bin):
        size_mb = os.path.getsize(dist_bin) / (1024 * 1024)
        print("\n" + "=" * 65)
        print(f"✓ Binary successfully compiled: {dist_bin} ({size_mb:.2f} MB)")
        print("=" * 65)

        # Run post-build smoke test
        print("\nRunning smoke test: ./dist/qkviewmgr --help")
        subprocess.run([dist_bin, "--help"])
    else:
        print(f"Error: Expected binary at {dist_bin} was not found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
