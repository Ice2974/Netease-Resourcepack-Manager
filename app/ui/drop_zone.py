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
        self.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 2px dashed #D1D5DB;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
        """)

        layout = QVBoxLayout(self)
        self.label = QLabel("拖拽 .zip 或 .mcpack 到此处")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #6B7280; font-size: 16px; font-weight: 500; border: none; background: transparent;")
        
        self.sub_label = QLabel("或点击下方按钮选择文件")
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setStyleSheet("color: #9CA3AF; font-size: 13px; border: none; background: transparent;")

        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addWidget(self.sub_label)
        layout.addStretch(1)

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
            self.setStyleSheet("""
                QFrame {
                    background-color: #EFF6FF;
                    border: 2px dashed #3B82F6;
                    border-radius: 12px;
                }
            """)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event):  # noqa: N802
        self.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 2px dashed #D1D5DB;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
        """)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 2px dashed #D1D5DB;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
        """)
        urls = event.mimeData().urls()
        if len(urls) != 1:
            return
        local = urls[0].toLocalFile()
        if not local:
            return
        self.file_dropped.emit(Path(local))
