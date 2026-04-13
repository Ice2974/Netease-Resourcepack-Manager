from __future__ import annotations

from pathlib import Path

from app.models.resource_pack import ResourcePack
from app.utils.manifest import extract_manifest_name, load_json_from_path


class ScanService:
    def __init__(self, packcache_dir: Path) -> None:
        self.packcache_dir = packcache_dir

    def scan(self) -> list[ResourcePack]:
        packs: list[ResourcePack] = []
        if not self.packcache_dir.exists():
            return packs

        for child in self.packcache_dir.iterdir():
            if not child.is_dir():
                continue
            manifest_path = child / "manifest.json"
            if not manifest_path.is_file():
                continue

            name = child.name
            try:
                manifest = load_json_from_path(manifest_path)
                name = extract_manifest_name(manifest, child.name)
            except Exception:  # noqa: BLE001
                name = child.name

            icon_path = child / "pack_icon.png"
            packs.append(
                ResourcePack(
                    folder_name=child.name,
                    path=child,
                    manifest_path=manifest_path,
                    display_name=name,
                    icon_path=icon_path if icon_path.is_file() else None,
                )
            )

        packs.sort(key=lambda item: item.display_name.lower())
        return packs
