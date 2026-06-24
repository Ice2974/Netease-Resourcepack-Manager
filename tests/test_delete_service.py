from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from app.models.resource_pack import ResourcePack
from app.services.delete_service import DeleteService
from app.services.log_service import LogService


class DeleteServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.packcache = self.root / "packcache"
        self.packcache.mkdir(parents=True)
        self.logs = self.root / "logs"
        self.logs.mkdir()

        self.log_service = LogService(self.logs)
        self.delete_service = DeleteService(self.packcache, self.log_service)

    def tearDown(self) -> None:
        self.log_service.close()
        self.temp.cleanup()

    def test_validate_safe_path_valid(self) -> None:
        pack_dir = self.packcache / "mypack"
        pack_dir.mkdir()
        # Should not raise
        self.delete_service._validate_safe_path(pack_dir)

    def test_validate_safe_path_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "传入了空路径"):
            self.delete_service._validate_safe_path(Path(""))

    def test_validate_safe_path_not_exists(self) -> None:
        pack_dir = self.packcache / "not_exist"
        with self.assertRaisesRegex(ValueError, "路径不存在"):
            self.delete_service._validate_safe_path(pack_dir)

    def test_validate_safe_path_not_dir(self) -> None:
        pack_file = self.packcache / "file.txt"
        pack_file.write_text("123")
        with self.assertRaisesRegex(ValueError, "目标不是一个文件夹"):
            self.delete_service._validate_safe_path(pack_file)

    def test_validate_safe_path_is_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "禁止删除 packcache 根目录"):
            self.delete_service._validate_safe_path(self.packcache)

    def test_validate_safe_path_outside_cache(self) -> None:
        outside_dir = self.root / "outside"
        outside_dir.mkdir()
        with self.assertRaisesRegex(ValueError, "目标路径必须在 packcache 目录下"):
            self.delete_service._validate_safe_path(outside_dir)

    def test_validate_safe_path_nested_dir(self) -> None:
        pack_dir = self.packcache / "mypack"
        pack_dir.mkdir()
        nested_dir = pack_dir / "nested"
        nested_dir.mkdir()
        with self.assertRaisesRegex(ValueError, "只允许删除 packcache 的一级子目录"):
            self.delete_service._validate_safe_path(nested_dir)

    def test_validate_safe_path_traversal(self) -> None:
        # Create a pack directory
        pack_dir = self.packcache / "mypack"
        pack_dir.mkdir()
        # Attempt traversal to parent
        traversal_path = pack_dir / ".."
        # Although traversal_path evaluates to packcache, it should be resolved and caught
        with self.assertRaisesRegex(ValueError, "禁止删除 packcache 根目录"):
            self.delete_service._validate_safe_path(traversal_path)

    def test_delete_pack_success(self) -> None:
        import shutil
        pack_dir = self.packcache / "mypack_success"
        pack_dir.mkdir()

        target_pack = ResourcePack(
            folder_name="mypack_success",
            path=pack_dir,
            manifest_path=pack_dir / "manifest.json",
            display_name="Success Pack",
            icon_path=None
        )

        def mock_send(target_path):
            shutil.rmtree(target_path)

        with unittest.mock.patch.object(self.delete_service, "_send_to_recycle_bin", side_effect=mock_send):
            result = self.delete_service.delete_pack(target_pack)
            self.assertTrue(result.success)
            self.assertFalse(pack_dir.exists())

    def test_delete_pack_fail_exception(self) -> None:
        pack_dir = self.packcache / "mypack_fail_exc"
        pack_dir.mkdir()

        target_pack = ResourcePack(
            folder_name="mypack_fail_exc",
            path=pack_dir,
            manifest_path=pack_dir / "manifest.json",
            display_name="Fail Pack",
            icon_path=None
        )

        with unittest.mock.patch.object(self.delete_service, "_send_to_recycle_bin", side_effect=RuntimeError("Fake error")):
            result = self.delete_service.delete_pack(target_pack)
            self.assertFalse(result.success)
            self.assertIn("Fake error", result.message)
            self.assertTrue(pack_dir.exists())

    def test_delete_pack_fail_still_exists(self) -> None:
        pack_dir = self.packcache / "mypack_fail_exists"
        pack_dir.mkdir()

        target_pack = ResourcePack(
            folder_name="mypack_fail_exists",
            path=pack_dir,
            manifest_path=pack_dir / "manifest.json",
            display_name="Fail Exists Pack",
            icon_path=None
        )

        # Mock _send_to_recycle_bin to do nothing
        with unittest.mock.patch.object(self.delete_service, "_send_to_recycle_bin", return_value=None):
            result = self.delete_service.delete_pack(target_pack)
            self.assertFalse(result.success)
            self.assertIn("目标文件仍然存在", result.message)
            self.assertTrue(pack_dir.exists())

if __name__ == "__main__":
    unittest.main()
