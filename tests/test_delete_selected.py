from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

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


def _make_pack(folder: str, idx: int) -> ResourcePack:
    return ResourcePack(
        folder_name=folder,
        path=Path(folder),
        manifest_path=Path(folder) / "manifest.json",
        display_name=f"Pack {idx}",
        icon_path=None,
    )


class MainWindowDeleteSelectedTests(unittest.TestCase):
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

    def _set_packs(self, count: int) -> list[ResourcePack]:
        packs = [_make_pack(f"pack{i}", i) for i in range(count)]
        self.window.packs = packs
        self.window.pack_table.setRowCount(len(packs))
        return packs

    def _select_rows(self, *rows: int) -> None:
        sm = self.window.pack_table.selectionModel()
        sm.clearSelection()
        from PySide6.QtCore import QItemSelectionModel
        for r in rows:
            sm.select(self.window.pack_table.model().index(r, 0),
                      QItemSelectionModel.Select | QItemSelectionModel.Rows)

    # --- _get_selected_packs / _format_pack_names ---

    def test_get_selected_packs_empty(self) -> None:
        self._set_packs(3)
        self.assertEqual(self.window._get_selected_packs(), [])

    def test_get_selected_packs_returns_selected_only(self) -> None:
        self._set_packs(5)
        self._select_rows(1, 3)
        packs = self.window._get_selected_packs()
        self.assertEqual([p.folder_name for p in packs], ["pack1", "pack3"])

    def test_get_selected_packs_dedup_and_sorted(self) -> None:
        self._set_packs(4)
        self._select_rows(3, 1, 1)
        packs = self.window._get_selected_packs()
        self.assertEqual([p.folder_name for p in packs], ["pack1", "pack3"])

    def test_format_pack_names_under_10(self) -> None:
        packs = [_make_pack(f"p{i}", i) for i in range(3)]
        text = MainWindow._format_pack_names(packs)
        self.assertIn("Pack 0", text)
        self.assertNotIn("等共", text)

    def test_format_pack_names_over_10(self) -> None:
        packs = [_make_pack(f"p{i}", i) for i in range(12)]
        text = MainWindow._format_pack_names(packs)
        self.assertIn("等共 12 个资源包", text)
        self.assertIn("Pack 0", text)
        self.assertNotIn("Pack 10", text)  # 仅前 10 个

    # --- _delete_selected_packs ---

    def test_delete_selected_none_no_action(self) -> None:
        self._set_packs(3)
        # 未选中
        with patch("app.ui.main_window.QMessageBox") as mock_box:
            self.window._delete_selected_packs()
            mock_box.warning.assert_not_called()
            mock_box.information.assert_not_called()
        self.delete_service.delete_pack.assert_not_called()

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.information")
    def test_delete_selected_single_uses_selected_row(
        self, mock_info: MagicMock, mock_warning: MagicMock
    ) -> None:
        """选中 1 个：以 selectedRows() 推导的删除目标为准，而非 currentRow()。"""
        packs = self._set_packs(4)
        # 让 currentRow 指向第 0 行，但实际只选中第 2 行
        self.window.pack_table.setCurrentCell(0, 0)
        self._select_rows(2)

        mock_warning.return_value = QMessageBox.Yes
        self.delete_service.delete_pack.return_value = DeleteResult(True, "OK", None)

        self.window._delete_selected_packs()

        # 只删了第 2 行对应的包，不是 currentRow 的第 0 行
        self.assertEqual(self.delete_service.delete_pack.call_count, 1)
        deleted_pack = self.delete_service.delete_pack.call_args[0][0]
        self.assertEqual(deleted_pack.folder_name, packs[2].folder_name)

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.critical")
    def test_delete_selected_single_cancel(self, mock_critical: MagicMock, mock_warning: MagicMock) -> None:
        self._set_packs(3)
        self._select_rows(1)
        mock_warning.return_value = QMessageBox.No

        self.window._delete_selected_packs()

        self.delete_service.delete_pack.assert_not_called()
        mock_critical.assert_not_called()
        self.log_service.info.assert_any_call("用户取消删除资源包: pack1")

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.information")
    def test_delete_selected_multiple_success(
        self, mock_info: MagicMock, mock_warning: MagicMock
    ) -> None:
        packs = self._set_packs(5)
        self._select_rows(0, 2, 4)

        mock_warning.return_value = QMessageBox.Yes
        self.delete_service.delete_pack.return_value = DeleteResult(True, "OK", None)

        self.window._delete_selected_packs()

        self.assertEqual(self.delete_service.delete_pack.call_count, 3)
        deleted_names = {c.args[0].folder_name for c in self.delete_service.delete_pack.call_args_list}
        self.assertEqual(deleted_names, {packs[0].folder_name, packs[2].folder_name, packs[4].folder_name})
        mock_info.assert_called_once()
        self.assertIn("成功: 3 个", mock_info.call_args[0][2])
        self.assertIn("失败: 0 个", mock_info.call_args[0][2])

    @patch("app.ui.main_window.QMessageBox.warning")
    def test_delete_selected_multiple_cancel(self, mock_warning: MagicMock) -> None:
        self._set_packs(4)
        self._select_rows(1, 2)
        mock_warning.return_value = QMessageBox.No

        self.window._delete_selected_packs()

        self.delete_service.delete_pack.assert_not_called()
        self.log_service.info.assert_any_call("用户取消批量删除选中的 2 个资源包")

    @patch("app.ui.main_window.QMessageBox.warning")
    def test_delete_selected_partial_failure(self, mock_warning: MagicMock) -> None:
        packs = self._set_packs(3)
        self._select_rows(0, 1, 2)

        # 确认 yes + 结果 warning
        mock_warning.side_effect = [QMessageBox.Yes, None]

        def mock_delete(pack):
            if pack.folder_name == packs[1].folder_name:
                return DeleteResult(False, "Failed", None, "Occupied")
            return DeleteResult(True, "OK", None)

        self.delete_service.delete_pack.side_effect = mock_delete

        self.window._delete_selected_packs()

        self.assertEqual(self.delete_service.delete_pack.call_count, 3)
        self.assertEqual(mock_warning.call_count, 2)
        error_msg = mock_warning.call_args_list[1][0][2]
        self.assertIn("成功: 2 个", error_msg)
        self.assertIn("失败: 1 个", error_msg)
        self.assertIn(packs[1].display_name, error_msg)

    @patch("app.ui.main_window.QMessageBox.warning")
    def test_delete_selected_all_failure(self, mock_warning: MagicMock) -> None:
        packs = self._set_packs(2)
        self._select_rows(0, 1)
        mock_warning.side_effect = [QMessageBox.Yes, None]
        self.delete_service.delete_pack.return_value = DeleteResult(False, "Failed", None, "Locked")

        self.window._delete_selected_packs()

        self.assertEqual(self.delete_service.delete_pack.call_count, 2)
        error_msg = mock_warning.call_args_list[1][0][2]
        self.assertIn("成功: 0 个", error_msg)
        self.assertIn("失败: 2 个", error_msg)

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.information")
    def test_delete_selected_uses_snapshot(
        self, mock_info: MagicMock, mock_warning: MagicMock
    ) -> None:
        """批量删除应以传入快照为准，refresh 修改 self.packs 不影响循环。"""
        self._set_packs(3)
        self._select_rows(0, 1, 2)
        mock_warning.return_value = QMessageBox.Yes
        self.delete_service.delete_pack.return_value = DeleteResult(True, "OK", None)

        original_refresh = self.window.refresh_packs

        def mock_refresh():
            self.window.packs = []

        self.window.refresh_packs = mock_refresh
        try:
            self.window._delete_selected_packs()
        finally:
            self.window.refresh_packs = original_refresh

        # 仍应删除全部 3 个，未因 refresh 清空 packs 而提前停止
        self.assertEqual(self.delete_service.delete_pack.call_count, 3)

    # --- _on_delete_shortcut ---

    def test_shortcut_empty_no_action(self) -> None:
        self._set_packs(3)
        # 未选中任何行 → 快捷键虽触发删除流程，但内部空列表直接返回，不调用 service
        self.window._on_delete_shortcut()
        self.delete_service.delete_pack.assert_not_called()

    def test_shortcut_main_page_triggers(self) -> None:
        self._set_packs(3)
        self._select_rows(1)
        self.window.stack.setCurrentWidget(self.window.main_page)
        with patch.object(self.window, "_delete_selected_packs") as mock_del:
            self.window._on_delete_shortcut()
            mock_del.assert_called_once()

    def test_shortcut_import_page_no_action(self) -> None:
        self._set_packs(3)
        self._select_rows(1)
        self.window.stack.setCurrentWidget(self.window.import_page)
        with patch.object(self.window, "_delete_selected_packs") as mock_del:
            self.window._on_delete_shortcut()
            mock_del.assert_not_called()

    def test_shortcut_focus_in_lineedit_no_action(self) -> None:
        self._set_packs(3)
        self._select_rows(1)
        self.window.stack.setCurrentWidget(self.window.main_page)

        edit = QLineEdit()
        with patch("app.ui.main_window.QApplication.focusWidget", return_value=edit):
            with patch.object(self.window, "_delete_selected_packs") as mock_del:
                self.window._on_delete_shortcut()
                mock_del.assert_not_called()

    # --- 滚动 / 刷新复用 ---

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.information")
    def test_delete_selected_refreshes_packs(
        self, mock_info: MagicMock, mock_warning: MagicMock
    ) -> None:
        """批量删除完成后应调用 refresh_packs，从而复用滚动保持机制。"""
        self._set_packs(2)
        self._select_rows(0, 1)
        mock_warning.return_value = QMessageBox.Yes
        self.delete_service.delete_pack.return_value = DeleteResult(True, "OK", None)

        with patch.object(self.window, "refresh_packs") as mock_refresh:
            self.window._delete_selected_packs()
            mock_refresh.assert_called_once()

    # --- 安全边界：传入 delete_service 的包均来自 self.packs ---

    @patch("app.ui.main_window.QMessageBox.warning")
    @patch("app.ui.main_window.QMessageBox.information")
    def test_delete_selected_only_targets_known_packs(
        self, mock_info: MagicMock, mock_warning: MagicMock
    ) -> None:
        packs = self._set_packs(3)
        self._select_rows(0, 2)
        mock_warning.return_value = QMessageBox.Yes
        self.delete_service.delete_pack.return_value = DeleteResult(True, "OK", None)

        self.window._delete_selected_packs()

        known_paths = {str(p.path) for p in packs}
        for call in self.delete_service.delete_pack.call_args_list:
            self.assertIn(str(call.args[0].path), known_paths)


if __name__ == "__main__":
    unittest.main()
