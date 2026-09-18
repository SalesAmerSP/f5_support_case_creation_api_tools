"""qkviewmgr package - F5 support case creation and QKView automation toolset."""

__version__ = "1.1.0"

from . import f5functions
from . import gui
from . import wizard
from .qkviewmgr import main

__all__ = ["f5functions", "gui", "wizard", "main", "__version__"]
