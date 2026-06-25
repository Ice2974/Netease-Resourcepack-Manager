from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

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


class RefreshScrollTests(unittest.TestCase):
    """refresh_packs 应在刷新后恢复垂直滚动位置（min(old, maximum()) 防越界）。

    说明：未 show() 的 QTableWidget 视口高度可能为 0，导致 maximum() 为 0、
    无可滚动范围。此时用例退化为“不抛异常 + 值合法”，真实像素行为以 UI 冒烟为准；
    涉及“恢复到非零值”的用例在 maximum()==0 时跳过。
    """

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

    def _force_scrollable(self, count: int) -> list[ResourcePack]:
        """填充足够多的包并尝试让表格出现可滚动范围。"""
        packs = [_make_pack(f"pack{i}", i) for i in range(count)]
        self.scan_service.scan.return_value = packs
        self.window.refresh_packs()
        # 尝试缩小视口以产生可滚动范围（不 show() 时未必生效）。
        self.window.pack_table.resize(200, 90)
        QTest.qWait(10)
        return packs

    def test_refresh_empty_list_no_throw(self) -> None:
        self.scan_service.scan.return_value = []
        self.window.refresh_packs()
        QTest.qWait(20)
        self.assertEqual(self.window.pack_table.verticalScrollBar().value(), 0)

    def test_refresh_restores_scroll_value(self) -> None:
        self._force_scrollable(40)
        scroll_bar = self.window.pack_table.verticalScrollBar()
        if scroll_bar.maximum() == 0:
            self.skipTest("headless: maximum()==0, 无可滚动范围")

        target = min(10, scroll_bar.maximum())
        scroll_bar.setValue(target)
        self.assertEqual(scroll_bar.value(), target)

        old = scroll_bar.value()
        self.window.refresh_packs()
        # singleShot 尚未触发前，setRowCount 已重置滚动位置。
        QTest.qWait(20)

        self.assertEqual(scroll_bar.value(), min(old, scroll_bar.maximum()))

    def test_refresh_clamps_when_rows_shrink(self) -> None:
        self._force_scrollable(40)
        scroll_bar = self.window.pack_table.verticalScrollBar()
        if scroll_bar.maximum() == 0:
            self.skipTest("headless: maximum()==0, 无可滚动范围")

        scroll_bar.setValue(scroll_bar.maximum())
        old = scroll_bar.value()

        # 行数大幅减少后，原滚动位置应被 clamp 到新的合法最大值。
        self.scan_service.scan.return_value = [_make_pack("pack0", 0)]
        self.window.refresh_packs()
        QTest.qWait(20)

        new_max = scroll_bar.maximum()
        self.assertLessEqual(scroll_bar.value(), new_max)
        self.assertEqual(scroll_bar.value(), min(old, new_max))


if __name__ == "__main__":
    unittest.main()
