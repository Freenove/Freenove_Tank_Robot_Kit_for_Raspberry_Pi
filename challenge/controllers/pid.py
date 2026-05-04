"""Re-export `Code/Client/PID.py:Incremental_PID` so we can use it without
adding `Code/Client` to sys.path everywhere. The implementation is
unchanged.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLIENT_DIR = _REPO_ROOT / "Code" / "Client"


def _load_incremental_pid_class():
    if str(_CLIENT_DIR) not in sys.path:
        sys.path.insert(0, str(_CLIENT_DIR))
    pid_path = _CLIENT_DIR / "PID.py"
    spec = importlib.util.spec_from_file_location("vendor_pid", pid_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load vendor PID from {pid_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Incremental_PID


Incremental_PID = _load_incremental_pid_class()


__all__ = ["Incremental_PID"]
