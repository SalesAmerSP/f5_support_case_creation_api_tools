"""Shared f5functions module imported from common location (src/f5functions.py).

This shim ensures scripts running from within the scripts/ directory
or importing f5functions seamlessly use the shared common module.
"""

import os
import sys

_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
_TARGET_PATH = os.path.join(_SRC_DIR, "f5functions.py")

if "f5functions" in sys.modules and getattr(sys.modules["f5functions"], "__file__", "").endswith("src/f5functions.py"):
    _shared_f5functions = sys.modules["f5functions"]
else:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("f5functions", _TARGET_PATH)
    _shared_f5functions = importlib.util.module_from_spec(_spec)
    sys.modules["f5functions"] = _shared_f5functions
    _spec.loader.exec_module(_shared_f5functions)

sys.modules[__name__] = _shared_f5functions

for _k, _v in list(_shared_f5functions.__dict__.items()):
    globals()[_k] = _v
