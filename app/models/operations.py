from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    message: str
    archive_path: Path
    import_name: str
    root_prefix: str


@dataclass(slots=True)
class ReplaceResult:
    success: bool
    message: str
    target_name: str
    import_name: str
    backup_path: Path | None
    error: str | None = None


@dataclass(slots=True)
class RollbackResult:
    success: bool
    message: str
    backup_path: Path | None
    error: str | None = None
