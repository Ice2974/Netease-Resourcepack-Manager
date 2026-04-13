from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ResourcePack:
    folder_name: str
    path: Path
    manifest_path: Path
    display_name: str
    icon_path: Path | None
