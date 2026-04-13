from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from app.models.resource_pack import ResourcePack
from app.services.backup_service import BackupService
from app.services.import_service import ImportService
from app.services.log_service import LogService
from app.services.replace_service import ReplaceService
from app.services.scan_service import ScanService


def _manifest(name: str, module_type: str = "resources") -> dict:
    return {
        "format_version": 2,
        "header": {
            "name": name,
            "uuid": "11111111-1111-1111-1111-111111111111",
            "version": [1, 0, 0],
        },
        "modules": [
            {
                "type": module_type,
                "uuid": "22222222-2222-2222-2222-222222222222",
                "version": [1, 0, 0],
            }
        ],
    }


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.packcache = self.root / "packcache"
        self.packcache.mkdir(parents=True)
        self.logs = self.root / "logs"
        self.backups = self.root / "backups"
        self.logs.mkdir()
        self.backups.mkdir()

        self.log_service = LogService(self.logs)
        self.scan_service = ScanService(self.packcache)
        self.import_service = ImportService()
        self.backup_service = BackupService(self.backups)
        self.replace_service = ReplaceService(self.backup_service, self.import_service, self.log_service)

    def tearDown(self) -> None:
        self.log_service.close()
        self.temp.cleanup()

    def _create_target_pack(self, folder: str = "target_pack", name: str = "云材质A") -> ResourcePack:
        target_dir = self.packcache / folder
        target_dir.mkdir(parents=True)
        (target_dir / "manifest.json").write_text(json.dumps(_manifest(name), ensure_ascii=False), encoding="utf-8")
        (target_dir / "pack_icon.png").write_bytes(b"fake")
        (target_dir / "old.txt").write_text("old", encoding="utf-8")
        return ResourcePack(
            folder_name=folder,
            path=target_dir,
            manifest_path=target_dir / "manifest.json",
            display_name=name,
            icon_path=target_dir / "pack_icon.png",
        )

    def _create_archive(self, archive_path: Path, outer_folder: bool = False, suffix: str = ".zip", name: str = "自定义材质") -> Path:
        archive_real = archive_path.with_suffix(suffix)
        root = "MyPack/" if outer_folder else ""
        with zipfile.ZipFile(archive_real, "w") as zf:
            zf.writestr(root + "manifest.json", json.dumps(_manifest(name), ensure_ascii=False))
            zf.writestr(root + "textures/blocks/stone.png", b"new")
            zf.writestr(root + "texts/en_US.lang", b"k=v")
        return archive_real

    def test_scan_first_level_only(self) -> None:
        pack1 = self.packcache / "pack1"
        pack1.mkdir()
        (pack1 / "manifest.json").write_text(json.dumps(_manifest("A")), encoding="utf-8")

        nested = self.packcache / "pack1" / "nested"
        nested.mkdir()
        (nested / "manifest.json").write_text(json.dumps(_manifest("B")), encoding="utf-8")

        pack2 = self.packcache / "pack2"
        pack2.mkdir()

        packs = self.scan_service.scan()
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0].folder_name, "pack1")

    def test_scan_name_and_icon_fallback(self) -> None:
        p1 = self.packcache / "with_name"
        p1.mkdir()
        (p1 / "manifest.json").write_text(json.dumps(_manifest("显示名"), ensure_ascii=False), encoding="utf-8")
        (p1 / "pack_icon.png").write_bytes(b"x")

        p2 = self.packcache / "fallback"
        p2.mkdir()
        (p2 / "manifest.json").write_text("not-json", encoding="utf-8")

        packs = {p.folder_name: p for p in self.scan_service.scan()}
        self.assertEqual(packs["with_name"].display_name, "显示名")
        self.assertIsNotNone(packs["with_name"].icon_path)
        self.assertEqual(packs["fallback"].display_name, "fallback")
        self.assertIsNone(packs["fallback"].icon_path)

    def test_validate_zip_valid(self) -> None:
        archive = self._create_archive(self.root / "valid_zip", suffix=".zip")
        result = self.import_service.validate_archive(archive)
        self.assertTrue(result.valid)

    def test_validate_mcpack_valid(self) -> None:
        archive = self._create_archive(self.root / "valid_pack", suffix=".mcpack")
        result = self.import_service.validate_archive(archive)
        self.assertTrue(result.valid)

    def test_validate_invalid_archive(self) -> None:
        bad = self.root / "bad.zip"
        bad.write_text("abc", encoding="utf-8")
        result = self.import_service.validate_archive(bad)
        self.assertFalse(result.valid)

    def test_validate_with_outer_folder(self) -> None:
        archive = self._create_archive(self.root / "outer", outer_folder=True)
        result = self.import_service.validate_archive(archive)
        self.assertTrue(result.valid)
        self.assertEqual(result.root_prefix, "MyPack")

    def test_replace_keeps_target_manifest(self) -> None:
        target = self._create_target_pack()
        target_manifest_before = (target.path / "manifest.json").read_text(encoding="utf-8")
        archive = self._create_archive(self.root / "replace")
        validation = self.import_service.validate_archive(archive)
        self.assertTrue(validation.valid)

        result = self.replace_service.replace_from_archive(target, validation)

        self.assertTrue(result.success)
        self.assertEqual((target.path / "manifest.json").read_text(encoding="utf-8"), target_manifest_before)
        self.assertTrue((target.path / "textures" / "blocks" / "stone.png").is_file())
        self.assertFalse((target.path / "old.txt").exists())

    def test_replace_fail_auto_rollback(self) -> None:
        target = self._create_target_pack()
        archive = self._create_archive(self.root / "replace_fail")
        validation = self.import_service.validate_archive(archive)
        before_files = sorted([p.relative_to(target.path).as_posix() for p in target.path.rglob("*")])

        with patch.object(ReplaceService, "_copy_archive_content", side_effect=RuntimeError("mock failure")):
            result = self.replace_service.replace_from_archive(target, validation)

        self.assertFalse(result.success)
        after_files = sorted([p.relative_to(target.path).as_posix() for p in target.path.rglob("*")])
        self.assertEqual(before_files, after_files)

    def test_manual_rollback_latest(self) -> None:
        target = self._create_target_pack()
        archive = self._create_archive(self.root / "replace_once")
        validation = self.import_service.validate_archive(archive)
        replace_result = self.replace_service.replace_from_archive(target, validation)
        self.assertTrue(replace_result.success)

        rollback = self.replace_service.rollback_latest(target)
        self.assertTrue(rollback.success)
        self.assertTrue((target.path / "old.txt").is_file())


if __name__ == "__main__":
    unittest.main()
