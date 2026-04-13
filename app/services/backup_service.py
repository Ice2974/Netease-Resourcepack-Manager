from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil


class BackupService:
    def __init__(self, backups_dir: Path) -> None:
        self.backups_dir = backups_dir
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, target_dir: Path, target_folder_name: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backups_dir / f"{target_folder_name}__{timestamp}"
        shutil.copytree(target_dir, backup_path)
        return backup_path

    def find_latest_backup(self, target_folder_name: str) -> Path | None:
        pattern = f"{target_folder_name}__*"
        candidates = sorted(self.backups_dir.glob(pattern), key=lambda p: p.name, reverse=True)
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return None

    def restore_backup(self, backup_path: Path, target_dir: Path) -> None:
        self._clear_directory(target_dir)
        for child in backup_path.iterdir():
            dst = target_dir / child.name
            if child.is_dir():
                shutil.copytree(child, dst)
            else:
                shutil.copy2(child, dst)

    def _clear_directory(self, target_dir: Path) -> None:
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            return
        for child in target_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
