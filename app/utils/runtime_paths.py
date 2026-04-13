from __future__ import annotations

import sys
from pathlib import Path


def get_runtime_base_dir() -> Path:
    """Return base dir that works for source and PyInstaller runtime."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_resource_path(*parts: str) -> Path:
    return get_runtime_base_dir().joinpath(*parts)
