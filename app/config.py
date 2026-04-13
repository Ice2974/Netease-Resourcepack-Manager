from __future__ import annotations

from pathlib import Path
import os
import shutil

APP_NAME = "NeteaseResourcepackManager"
VERSION = "0.1.0"


def get_appdata_root() -> Path:
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("无法读取 APPDATA 环境变量。")
    return Path(appdata)


def get_packcache_dir() -> Path:
    return get_appdata_root() / "MinecraftPE_Netease" / "packcache"


def get_data_root() -> Path:
    return get_appdata_root() / APP_NAME


def ensure_data_dirs() -> dict[str, Path]:
    root = get_data_root()
    backups = root / "backups"
    logs = root / "logs"
    temp = root / "temp"

    for folder in (root, backups, logs, temp):
        folder.mkdir(parents=True, exist_ok=True)
    for child in temp.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass

    return {
        "root": root,
        "backups": backups,
        "logs": logs,
        "temp": temp,
    }
