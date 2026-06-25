from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout


class DropZone(QFrame):
    file_dropped = Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        # 配色与拖拽高亮态由全局 QSS（styles.qss / styles_dark.qss）按对象名与
        # dragActive 属性接管，深浅主题各自定义，避免内联硬编码浅色值。
        self.setObjectName("DropZone")
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        self.label = QLabel("拖拽 .zip 或 .mcpack 到此处")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("DropZoneLabel")

        self.sub_label = QLabel("或点击下方按钮选择文件")
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setObjectName("DropZoneSubLabel")

        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addWidget(self.sub_label)
        layout.addStretch(1)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        mime = event.mimeData()
        if not mime.hasUrls():
            event.ignore()
            return
        urls = mime.urls()
        if len(urls) != 1:
            event.ignore()
            return
        local = urls[0].toLocalFile()
        suffix = Path(local).suffix.lower()
        if suffix in {".zip", ".mcpack"}:
            self._set_drag_active(True)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event):  # noqa: N802
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_drag_active(False)
        urls = event.mimeData().urls()
        if len(urls) != 1:
            return
        local = urls[0].toLocalFile()
        if not local:
            return
        self.file_dropped.emit(Path(local))
