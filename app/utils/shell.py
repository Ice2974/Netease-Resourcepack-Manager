from __future__ import annotations

import os
import subprocess
from pathlib import Path


def open_path(path: Path) -> None:
    target = str(path)
    if os.name == "nt":
        os.startfile(target)  # type: ignore[attr-defined]
        return
    subprocess.Popen(["xdg-open", target])


def reveal_file(path: Path) -> None:
    if os.name == "nt":
        subprocess.Popen(["explorer", f"/select,{path}"])
        return
    open_path(path.parent)
