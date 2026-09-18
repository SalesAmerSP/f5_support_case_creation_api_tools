"""Backward-compatibility shim for legacy python/wizard.py invocations."""
import os
import sys

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import qkviewmgr.wizard as _orig

sys.modules[__name__] = _orig

if __name__ == "__main__":
    _orig.main_menu()
