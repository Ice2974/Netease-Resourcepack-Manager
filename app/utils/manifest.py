from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_from_path(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return load_json_from_bytes(raw)


def load_json_from_bytes(raw: bytes) -> dict[str, Any]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(encoding)
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("JSON 顶层不是对象。")
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise ValueError(f"JSON 解析失败: {last_error}")


def extract_manifest_name(manifest: dict[str, Any], fallback: str) -> str:
    header = manifest.get("header")
    if isinstance(header, dict):
        name = header.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback
