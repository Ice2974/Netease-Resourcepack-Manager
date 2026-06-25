from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from app.models.resource_pack import ResourcePack
from app.models.replace_mode import ReplaceMode
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

    def _create_archive_with_files(self, archive_path: Path, files: dict[str, bytes | str]) -> Path:
        archive_real = archive_path.with_suffix(".zip")
        with zipfile.ZipFile(archive_real, "w") as zf:
            for name, data in files.items():
                if isinstance(data, str):
                    data = data.encode("utf-8")
                zf.writestr(name, data)
        return archive_real

    def _snapshot(self, d: Path) -> dict[str, bytes]:
        snap: dict[str, bytes] = {}
        for p in d.rglob("*"):
            if p.is_file():
                snap[p.relative_to(d).as_posix()] = p.read_bytes()
        return snap

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

    def _create_merge_target(self) -> ResourcePack:
        target = self._create_target_pack()
        (target.path / "keep.txt").write_text("keep", encoding="utf-8")
        (target.path / "shared.txt").write_text("target_shared", encoding="utf-8")
        nested = target.path / "nested"
        nested.mkdir()
        (nested / "inner.txt").write_text("target_nested", encoding="utf-8")
        return target

    def _create_merge_archive(self, archive_path: Path) -> Path:
        return self._create_archive_with_files(
            archive_path,
            {
                "manifest.json": json.dumps(_manifest("导入包"), ensure_ascii=False),
                "shared.txt": "import_shared",
                "new.txt": "import_new",
                "nested/inner.txt": "import_nested",
                "nested/extra.txt": "import_extra",
            },
        )

    def test_replace_full_explicit(self) -> None:
        target = self._create_merge_target()
        target_manifest_before = (target.path / "manifest.json").read_text(encoding="utf-8")
        archive = self._create_merge_archive(self.root / "full_explicit")
        validation = self.import_service.validate_archive(archive)
        self.assertTrue(validation.valid)

        result = self.replace_service.replace_from_archive(target, validation, ReplaceMode.FULL)

        self.assertTrue(result.success)
        self.assertEqual((target.path / "manifest.json").read_text(encoding="utf-8"), target_manifest_before)
        # 目标独有旧文件被清理
        self.assertFalse((target.path / "keep.txt").exists())
        # 新文件被导入（含嵌套目录；同名文件被导入包版本替换）
        self.assertEqual((target.path / "shared.txt").read_text(encoding="utf-8"), "import_shared")
        self.assertEqual((target.path / "new.txt").read_text(encoding="utf-8"), "import_new")
        self.assertEqual((target.path / "nested" / "inner.txt").read_text(encoding="utf-8"), "import_nested")
        self.assertEqual((target.path / "nested" / "extra.txt").read_text(encoding="utf-8"), "import_extra")

    def test_replace_merge(self) -> None:
        target = self._create_merge_target()
        target_manifest_before = (target.path / "manifest.json").read_text(encoding="utf-8")
        archive = self._create_merge_archive(self.root / "merge")
        validation = self.import_service.validate_archive(archive)
        self.assertTrue(validation.valid)

        result = self.replace_service.replace_from_archive(target, validation, ReplaceMode.MERGE)

        self.assertTrue(result.success)
        self.assertEqual((target.path / "manifest.json").read_text(encoding="utf-8"), target_manifest_before)
        # 同名文件被覆盖（含嵌套目录）
        self.assertEqual((target.path / "shared.txt").read_text(encoding="utf-8"), "import_shared")
        self.assertEqual((target.path / "nested" / "inner.txt").read_text(encoding="utf-8"), "import_nested")
        # 目标独有旧文件保留
        self.assertEqual((target.path / "keep.txt").read_text(encoding="utf-8"), "keep")
        # 新文件被加入
        self.assertEqual((target.path / "new.txt").read_text(encoding="utf-8"), "import_new")
        self.assertEqual((target.path / "nested" / "extra.txt").read_text(encoding="utf-8"), "import_extra")

    def test_replace_add_only(self) -> None:
        target = self._create_merge_target()
        target_manifest_before = (target.path / "manifest.json").read_text(encoding="utf-8")
        archive = self._create_merge_archive(self.root / "add_only")
        validation = self.import_service.validate_archive(archive)
        self.assertTrue(validation.valid)

        result = self.replace_service.replace_from_archive(target, validation, ReplaceMode.ADD_ONLY)

        self.assertTrue(result.success)
        self.assertEqual((target.path / "manifest.json").read_text(encoding="utf-8"), target_manifest_before)
        # 同名旧文件不被覆盖（含嵌套目录）
        self.assertEqual((target.path / "shared.txt").read_text(encoding="utf-8"), "target_shared")
        self.assertEqual((target.path / "nested" / "inner.txt").read_text(encoding="utf-8"), "target_nested")
        # 目标独有旧文件保留
        self.assertEqual((target.path / "keep.txt").read_text(encoding="utf-8"), "keep")
        # 新文件被加入
        self.assertEqual((target.path / "new.txt").read_text(encoding="utf-8"), "import_new")
        self.assertEqual((target.path / "nested" / "extra.txt").read_text(encoding="utf-8"), "import_extra")

    def test_replace_merge_fail_auto_rollback(self) -> None:
        target = self._create_merge_target()
        archive = self._create_merge_archive(self.root / "merge_fail")
        validation = self.import_service.validate_archive(archive)
        before = self._snapshot(target.path)

        def partial_fail(target_dir: Path, validation: ValidationResult, overwrite: bool) -> None:
            # 模拟半替换：写入一个文件后失败
            (target_dir / "shared.txt").write_bytes(b"import_shared")
            (target_dir / "partial.txt").write_bytes(b"partial")
            raise RuntimeError("mock failure")

        with patch.object(ReplaceService, "_copy_archive_content", side_effect=partial_fail):
            result = self.replace_service.replace_from_archive(target, validation, ReplaceMode.MERGE)

        self.assertFalse(result.success)
        after = self._snapshot(target.path)
        # 文件列表和文件内容都恢复到替换前
        self.assertEqual(before, after)

    def test_replace_add_only_fail_auto_rollback(self) -> None:
        target = self._create_merge_target()
        archive = self._create_merge_archive(self.root / "add_only_fail")
        validation = self.import_service.validate_archive(archive)
        before = self._snapshot(target.path)

        def partial_fail(target_dir: Path, validation: ValidationResult, overwrite: bool) -> None:
            (target_dir / "new.txt").write_bytes(b"import_new")
            raise RuntimeError("mock failure")

        with patch.object(ReplaceService, "_copy_archive_content", side_effect=partial_fail):
            result = self.replace_service.replace_from_archive(target, validation, ReplaceMode.ADD_ONLY)

        self.assertFalse(result.success)
        after = self._snapshot(target.path)
        self.assertEqual(before, after)

    def test_replace_merge_type_conflict_rollback(self) -> None:
        # 目标中 textures 是一个文件；导入包要写 textures/a.png，父路径是文件导致 mkdir 失败。
        target = self._create_target_pack()
        (target.path / "textures").write_text("target_textures_file", encoding="utf-8")
        target_manifest_before = (target.path / "manifest.json").read_text(encoding="utf-8")

        archive = self._create_archive_with_files(
            self.root / "merge_type_conflict",
            {
                "manifest.json": json.dumps(_manifest("导入包"), ensure_ascii=False),
                "textures/a.png": b"import_png",
            },
        )
        validation = self.import_service.validate_archive(archive)
        self.assertTrue(validation.valid)

        before = self._snapshot(target.path)

        result = self.replace_service.replace_from_archive(target, validation, ReplaceMode.MERGE)

        # 类型冲突必须失败并自动回滚，不得静默删除目录或改写结构。
        self.assertFalse(result.success)
        self.assertEqual((target.path / "manifest.json").read_text(encoding="utf-8"), target_manifest_before)
        after = self._snapshot(target.path)
        self.assertEqual(before, after)

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
