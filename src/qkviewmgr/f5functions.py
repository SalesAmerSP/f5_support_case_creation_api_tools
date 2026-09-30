"""Backward-compatibility module re-exporting shared f5functions.

f5functions.py has been moved to the common source location (src/f5functions.py)
to be shared across qkviewmgr, download_browser, and standalone scripts.
"""

import importlib.util
import os
import sys

_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TARGET_PATH = os.path.join(_SRC_DIR, "f5functions.py")

if "f5functions" in sys.modules and getattr(sys.modules["f5functions"], "__file__", "").endswith("src/f5functions.py"):
    _shared_mod = sys.modules["f5functions"]
else:
    _spec = importlib.util.spec_from_file_location("f5functions", _TARGET_PATH)
    _shared_mod = importlib.util.module_from_spec(_spec)
    sys.modules["f5functions"] = _shared_mod
    _spec.loader.exec_module(_shared_mod)

sys.modules[__name__] = _shared_mod

for _k, _v in list(_shared_mod.__dict__.items()):
    globals()[_k] = _v
