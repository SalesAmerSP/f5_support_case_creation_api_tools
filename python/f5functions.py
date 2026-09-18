"""Backward-compatibility shim for legacy f5functions imports."""
import os
import sys

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import qkviewmgr.f5functions as _orig

# Alias this module to qkviewmgr.f5functions so both names reference the exact same module object
sys.modules[__name__] = _orig
