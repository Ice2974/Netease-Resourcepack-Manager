from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QMessageBox

from app.models.operations import DeleteResult
from app.models.resource_pack import ResourcePack
from app.services.delete_service import DeleteService
from app.services.import_service import ImportService
from app.services.log_service import LogService
from app.services.replace_service import ReplaceService
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class MainWindowDeleteAllTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scan_service = MagicMock(spec=ScanService)
        self.import_service = MagicMock(spec=ImportService)
        self.replace_service = MagicMock(spec=ReplaceService)
        self.delete_service = MagicMock(spec=DeleteService)
        self.log_service = MagicMock(spec=LogService)
        self.packcache_dir = Path("dummy_packcache")
        self.logs_dir = Path("dummy_logs")

        self.scan_service.scan.return_value = []

        self.window = MainWindow(
            self.scan_service,
            self.import_service,
            self.replace_service,
            self.delete_service,
            self.log_service,
            self.packcache_dir,
            self.logs_dir,
        )

    def test_delete_all_empty(self) -> None:
        self.window.packs = []
        with patch("app.ui.main_window.QMessageBox.information") as mock_info:
            self.window._delete_all_packs()
            mock_info.assert_called_once()
            self.delete_service.delete_pack.assert_not_called()

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.information")
    def test_delete_all_success(self, mock_info: MagicMock, mock_warning: MagicMock) -> None:
        p1 = ResourcePack("pack1", Path("p1"), Path("m1"), "Pack 1", None)
        p2 = ResourcePack("pack2", Path("p2"), Path("m2"), "Pack 2", None)
        self.window.packs = [p1, p2]

        mock_warning.return_value = QMessageBox.Yes
        self.delete_service.delete_pack.return_value = DeleteResult(True, "OK", None)

        # Mock refresh_packs to empty self.packs, proving we used a snapshot
        original_refresh = self.window.refresh_packs
        def mock_refresh():
            self.window.packs = []
        self.window.refresh_packs = mock_refresh

        self.window._delete_all_packs()

        self.assertEqual(self.delete_service.delete_pack.call_count, 2)
        mock_info.assert_called_once()
        self.assertIn("成功: 2 个", mock_info.call_args[0][2])
        self.assertIn("失败: 0 个", mock_info.call_args[0][2])
        self.window.refresh_packs = original_refresh

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.information")
    def test_delete_all_cancel(self, mock_info: MagicMock, mock_warning: MagicMock) -> None:
        p1 = ResourcePack("pack1", Path("p1"), Path("m1"), "Pack 1", None)
        self.window.packs = [p1]

        mock_warning.return_value = QMessageBox.No

        self.window._delete_all_packs()

        self.delete_service.delete_pack.assert_not_called()
        mock_info.assert_not_called()

    @patch("app.ui.main_window.QMessageBox.warning")
    def test_delete_all_partial_failure(self, mock_warning: MagicMock) -> None:
        p1 = ResourcePack("pack1", Path("p1"), Path("m1"), "Pack 1", None)
        p2 = ResourcePack("pack2", Path("p2"), Path("m2"), "Pack 2", None)
        p3 = ResourcePack("pack3", Path("p3"), Path("m3"), "Pack 3", None)
        self.window.packs = [p1, p2, p3]

        # First warning is confirmation, second is the partial failure result
        mock_warning.side_effect = [QMessageBox.Yes, None]

        def mock_delete(pack):
            if pack.folder_name == "pack2":
                return DeleteResult(False, "Failed", None, "Occupied")
            return DeleteResult(True, "OK", None)
        
        self.delete_service.delete_pack.side_effect = mock_delete

        self.window._delete_all_packs()

        self.assertEqual(self.delete_service.delete_pack.call_count, 3)
        self.assertEqual(mock_warning.call_count, 2)
        # Ensure error warning has correct counts
        error_msg = mock_warning.call_args_list[1][0][2]
        self.assertIn("成功: 2 个", error_msg)
        self.assertIn("失败: 1 个", error_msg)
        self.assertIn("Pack 2", error_msg)

    @patch("app.ui.main_window.QMessageBox.warning")
    def test_delete_all_exception_fallback(self, mock_warning: MagicMock) -> None:
        p1 = ResourcePack("pack1", Path("p1"), Path("m1"), "Pack 1", None)
        p2 = ResourcePack("pack2", Path("p2"), Path("m2"), "Pack 2", None)
        self.window.packs = [p1, p2]

        mock_warning.side_effect = [QMessageBox.Yes, None]

        def mock_delete(pack):
            if pack.folder_name == "pack1":
                raise RuntimeError("Something unexpectedly crashed")
            return DeleteResult(True, "OK", None)
        
        self.delete_service.delete_pack.side_effect = mock_delete

        self.window._delete_all_packs()

        self.assertEqual(self.delete_service.delete_pack.call_count, 2)
        self.assertEqual(mock_warning.call_count, 2)
        error_msg = mock_warning.call_args_list[1][0][2]
        self.assertIn("成功: 1 个", error_msg)
        self.assertIn("失败: 1 个", error_msg)
        self.assertIn("Pack 1", error_msg)
        self.assertIn("Something unexpectedly crashed", error_msg)

if __name__ == "__main__":
    unittest.main()
