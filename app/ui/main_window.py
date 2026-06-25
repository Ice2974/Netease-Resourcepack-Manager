from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QFileSystemWatcher, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.operations import ValidationResult
from app.models.replace_mode import ReplaceMode
from app.models.resource_pack import ResourcePack
from app.services.import_service import ImportService
from app.services.log_service import LogService
from app.services.replace_service import ReplaceService
from app.services.scan_service import ScanService
from app.services.delete_service import DeleteService
from app.ui.drop_zone import DropZone
from app.utils.shell import open_path, reveal_file


class PackTableDelegate(QStyledItemDelegate):
    def __init__(self, open_folder_callback, delete_pack_callback) -> None:
        super().__init__()
        self.open_folder_callback = open_folder_callback
        self.delete_pack_callback = delete_pack_callback
        self.folder_icon = self._create_folder_icon()
        self.trash_icon = self._create_trash_icon()

    def paint(self, painter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect.adjusted(4, 4, -4, -4)
        radius = 8

        # Draw Background
        if option.state & QStyle.State_Selected:
            painter.setPen(QColor("#BFDBFE"))
            painter.setBrush(QColor("#EFF6FF"))
            painter.drawRoundedRect(rect, radius, radius)
        elif option.state & QStyle.State_MouseOver:
            painter.setPen(QColor("#E5E7EB"))
            painter.setBrush(QColor("#F9FAFB"))
            painter.drawRoundedRect(rect, radius, radius)
        else:
            painter.setPen(QColor("#E5E7EB"))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawRoundedRect(rect, radius, radius)

        # Draw Icon
        icon = index.data(Qt.DecorationRole)
        icon_rect = QRect(rect.left() + 16, rect.top() + (rect.height() - 48) // 2, 48, 48)
        if isinstance(icon, QIcon) and not icon.isNull():
            icon.paint(painter, icon_rect, Qt.AlignCenter)

        # Draw Folder Button Background
        folder_rect = self._folder_icon_rect(option.rect)

        # Draw Text
        text = index.data(Qt.DisplayRole)
        text_x = icon_rect.right() + 16
        text_width = folder_rect.left() - 16 - text_x
        text_rect = QRect(text_x, rect.top(), text_width, rect.height())

        font = option.font
        font.setPixelSize(15)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#111827"))

        metrics = painter.fontMetrics()
        elided_text = metrics.elidedText(text, Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_text)

        if option.state & QStyle.State_Selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#DBEAFE"))
            painter.drawRoundedRect(folder_rect.adjusted(-4, -4, 4, 4), 6, 6)
        elif option.state & QStyle.State_MouseOver:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#F3F4F6"))
            painter.drawRoundedRect(folder_rect.adjusted(-4, -4, 4, 4), 6, 6)

        # Draw Folder Icon
        self.folder_icon.paint(painter, folder_rect, Qt.AlignCenter)

        # Draw Trash Button Background
        trash_rect = self._trash_icon_rect(option.rect)
        if option.state & QStyle.State_Selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FEE2E2"))
            painter.drawRoundedRect(trash_rect.adjusted(-4, -4, 4, 4), 6, 6)
        elif option.state & QStyle.State_MouseOver:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FEF2F2"))
            painter.drawRoundedRect(trash_rect.adjusted(-4, -4, 4, 4), 6, 6)

        # Draw Trash Icon
        self.trash_icon.paint(painter, trash_rect, Qt.AlignCenter)

        painter.restore()

    def editorEvent(self, event, model, option, index):  # noqa: N802
        if event.type() in (QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick):
            mouse_event = event
            if isinstance(mouse_event, QMouseEvent) and mouse_event.button() == Qt.LeftButton:
                folder_rect = self._folder_icon_rect(option.rect).adjusted(-4, -4, 4, 4)
                trash_rect = self._trash_icon_rect(option.rect).adjusted(-4, -4, 4, 4)
                if folder_rect.contains(mouse_event.position().toPoint()):
                    if event.type() == QEvent.MouseButtonRelease:
                        self.open_folder_callback(index.row())
                    return True
                elif trash_rect.contains(mouse_event.position().toPoint()):
                    if event.type() == QEvent.MouseButtonRelease:
                        self.delete_pack_callback(index.row())
                    return True
        return super().editorEvent(event, model, option, index)

    def _folder_icon_rect(self, rect):
        size = 20
        x = rect.right() - 68  # Moved left to make room for trash icon
        y = rect.center().y() - (size // 2)
        return QRect(x, y, size, size)

    def _trash_icon_rect(self, rect):
        size = 20
        x = rect.right() - 36
        y = rect.center().y() - (size // 2)
        return QRect(x, y, size, size)

    def _create_folder_icon(self) -> QIcon:
        pix = QPixmap(20, 20)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QColor("#4B5563")
        painter.setPen(pen)
        painter.drawRect(2, 6, 16, 11)
        painter.drawLine(4, 6, 7, 3)
        painter.drawLine(7, 3, 13, 3)
        painter.drawLine(13, 3, 15, 6)
        painter.end()
        return QIcon(pix)

    def _create_trash_icon(self) -> QIcon:
        pix = QPixmap(20, 20)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QColor("#DC2626")  # Red color
        painter.setPen(pen)

        # Trash bin body
        painter.drawRect(5, 7, 10, 10)
        # Trash bin lid
        painter.drawLine(3, 5, 17, 5)
        # Trash bin lid handle
        painter.drawLine(8, 3, 12, 3)
        painter.drawLine(8, 3, 8, 5)
        painter.drawLine(12, 3, 12, 5)
        # Lines on the bin
        painter.drawLine(8, 9, 8, 14)
        painter.drawLine(12, 9, 12, 14)

        painter.end()
        return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(
        self,
        scan_service: ScanService,
        import_service: ImportService,
        replace_service: ReplaceService,
        delete_service: DeleteService,
        log_service: LogService,
        packcache_dir: Path,
        logs_dir: Path,
    ) -> None:
        super().__init__()
        self.scan_service = scan_service
        self.import_service = import_service
        self.replace_service = replace_service
        self.delete_service = delete_service
        self.log_service = log_service
        self.packcache_dir = packcache_dir
        self.logs_dir = logs_dir

        self.setWindowTitle("Netease Resourcepack Manager")
        self.resize(980, 680)

        self.packs: list[ResourcePack] = []
        self.selected_pack: ResourcePack | None = None
        self.selected_archive: Path | None = None
        self.validation_result: ValidationResult | None = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.main_page = self._build_main_page()
        self.import_page = self._build_import_page()
        self.stack.addWidget(self.main_page)
        self.stack.addWidget(self.import_page)

        self.refresh_debounce = QTimer(self)
        self.refresh_debounce.setSingleShot(True)
        self.refresh_debounce.setInterval(500)
        self.refresh_debounce.timeout.connect(self.refresh_packs)

        self.fs_watcher = QFileSystemWatcher(self)
        self.fs_watcher.directoryChanged.connect(self._schedule_refresh)
        self._update_watch_paths()

        self.refresh_packs()

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Top Card
        top_card = QFrame()
        top_card.setProperty("class", "Card")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(20, 16, 20, 16)

        info_layout = QVBoxLayout()
        title_label = QLabel("资源包列表")
        title_label.setObjectName("TitleLabel")
        self.packcache_label = QLabel(f"扫描目录: {self.packcache_dir}")
        self.packcache_label.setObjectName("SubtitleLabel")

        info_layout.addWidget(title_label)
        info_layout.addWidget(self.packcache_label)

        self.refresh_button = QPushButton("手动刷新")
        self.open_logs_button = QPushButton("查看日志")
        self.delete_all_button = QPushButton("全部删除")
        self.refresh_button.setFocusPolicy(Qt.NoFocus)
        self.open_logs_button.setFocusPolicy(Qt.NoFocus)
        self.delete_all_button.setFocusPolicy(Qt.NoFocus)
        self.delete_all_button.setObjectName("DangerOutlineButton")

        self.refresh_button.clicked.connect(self.refresh_packs)
        self.open_logs_button.clicked.connect(lambda: open_path(self.logs_dir))
        self.delete_all_button.clicked.connect(self._delete_all_packs)

        top_layout.addLayout(info_layout)
        top_layout.addStretch(1)
        top_layout.addWidget(self.refresh_button)
        top_layout.addWidget(self.open_logs_button)
        top_layout.addWidget(self.delete_all_button)

        # Table Card
        table_card = QFrame()
        table_card.setProperty("class", "Card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(16, 16, 16, 16)

        self.pack_table = QTableWidget(0, 1)
        self.pack_table.setHorizontalHeaderLabels(["双击资源包开始替换"])
        self.pack_table.verticalHeader().setVisible(False)
        self.pack_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pack_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pack_table.setShowGrid(False)
        self.pack_table.setFocusPolicy(Qt.NoFocus)
        self.pack_table.verticalHeader().setDefaultSectionSize(72)

        self.pack_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.pack_table.doubleClicked.connect(self._on_table_double_clicked)
        self.pack_table.horizontalHeader().setStretchLastSection(True)
        self.pack_table.setItemDelegate(PackTableDelegate(self._open_pack_by_row, self._delete_pack_by_row))

        table_layout.addWidget(self.pack_table)

        layout.addWidget(top_card, 0)
        layout.addWidget(table_card, 1)
        return page

    def _build_import_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header with back button
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("返回主页")
        self.back_button.setFixedWidth(100)
        self.back_button.setFocusPolicy(Qt.NoFocus)
        header_title = QLabel("导入与替换")
        header_title.setObjectName("TitleLabel")

        header_layout.addWidget(self.back_button)
        header_layout.addWidget(header_title)
        header_layout.addStretch(1)

        # Target Card
        target_card = QFrame()
        target_card.setProperty("class", "Card")
        target_layout = QVBoxLayout(target_card)
        target_layout.setContentsMargins(20, 16, 20, 16)

        target_title = QLabel("目标资源包")
        target_title.setObjectName("SubtitleLabel")
        self.target_label = QLabel("未选择")
        self.target_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827;")
        target_layout.addWidget(target_title)
        target_layout.addWidget(self.target_label)

        # Import File Card
        import_card = QFrame()
        import_card.setProperty("class", "Card")
        import_layout = QVBoxLayout(import_card)
        import_layout.setContentsMargins(20, 20, 20, 20)
        import_layout.setSpacing(16)

        file_title = QLabel("导入文件")
        file_title.setObjectName("SubtitleLabel")

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._set_archive_file)
        self.drop_zone.setMinimumHeight(160)

        button_row = QHBoxLayout()
        self.choose_file_button = QPushButton("从电脑选择文件")
        self.choose_file_button.setFocusPolicy(Qt.NoFocus)
        self.file_label = QLabel("未选择")
        self.file_label.setStyleSheet("color: #4B5563; font-size: 14px;")

        button_row.addWidget(self.choose_file_button)
        button_row.addSpacing(16)
        button_row.addWidget(self.file_label)
        button_row.addStretch(1)

        self.validate_label = QLabel("请先选择 .zip 或 .mcpack 文件")
        self.validate_label.setWordWrap(True)
        self.validate_label.setStyleSheet("color: #6B7280; font-size: 13px; margin-top: 8px;")

        import_layout.addWidget(file_title)
        import_layout.addWidget(self.drop_zone)
        import_layout.addLayout(button_row)
        import_layout.addWidget(self.validate_label)

        # Replace Mode Card
        mode_card = QFrame()
        mode_card.setProperty("class", "Card")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(20, 20, 20, 20)
        mode_layout.setSpacing(12)

        mode_title = QLabel("替换模式")
        mode_title.setObjectName("SubtitleLabel")
        mode_layout.addWidget(mode_title)

        self.mode_group = QButtonGroup(self)
        self.mode_map: dict[int, ReplaceMode] = {
            0: ReplaceMode.FULL,
            1: ReplaceMode.MERGE,
            2: ReplaceMode.ADD_ONLY,
        }
        mode_options = [
            (0, "全量替换", "清空原资源包内容后导入新文件，保留原 manifest.json"),
            (1, "覆盖合并", "导入新文件，同名文件会被覆盖，其他原文件保留"),
            (2, "仅新增", "只导入不存在的文件，同名文件跳过，不覆盖"),
        ]
        for mode_id, title, desc in mode_options:
            row = QHBoxLayout()
            radio = QRadioButton(title)
            radio.setFocusPolicy(Qt.NoFocus)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #6B7280; font-size: 12px;")
            desc_label.setWordWrap(True)
            row.addWidget(radio)
            row.addWidget(desc_label, 1)
            mode_layout.addLayout(row)
            self.mode_group.addButton(radio, mode_id)

        self.mode_group.button(0).setChecked(True)

        mode_hint = QLabel("所有模式都会保留目标 manifest.json，并在替换前自动备份。")
        mode_hint.setStyleSheet("color: #6B7280; font-size: 12px; margin-top: 4px;")
        mode_hint.setWordWrap(True)
        mode_layout.addWidget(mode_hint)

        # Action & Result Card
        action_card = QFrame()
        action_card.setProperty("class", "Card")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(20, 16, 20, 16)

        self.replace_button = QPushButton("执行替换")
        self.replace_button.setObjectName("PrimaryButton")
        self.replace_button.setEnabled(False)
        self.replace_button.setMinimumHeight(36)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)

        result_action_layout = QHBoxLayout()
        self.open_target_button = QPushButton("打开目标目录")
        self.rollback_button = QPushButton("回滚到替换前")
        self.rollback_button.setObjectName("DangerButton")
        self.view_logs_button = QPushButton("查看日志")
        self.open_target_button.setFocusPolicy(Qt.NoFocus)
        self.rollback_button.setFocusPolicy(Qt.NoFocus)
        self.view_logs_button.setFocusPolicy(Qt.NoFocus)

        result_action_layout.addWidget(self.open_target_button)
        result_action_layout.addWidget(self.rollback_button)
        result_action_layout.addWidget(self.view_logs_button)
        result_action_layout.addStretch(1)

        action_layout.addWidget(self.replace_button)
        action_layout.addWidget(self.result_label)
        action_layout.addLayout(result_action_layout)

        layout.addLayout(header_layout)
        layout.addWidget(target_card)
        layout.addWidget(import_card)
        layout.addWidget(mode_card)
        layout.addWidget(action_card)
        layout.addStretch(1)

        self.choose_file_button.clicked.connect(self._choose_import_file)
        self.replace_button.clicked.connect(self._do_replace)
        self.back_button.clicked.connect(self._go_main)
        self.open_target_button.clicked.connect(self._open_target_folder)
        self.rollback_button.clicked.connect(self._rollback_latest)
        self.view_logs_button.clicked.connect(lambda: reveal_file(self.log_service.log_file))

        self._toggle_result_buttons(False, False)
        return page

    def _toggle_result_buttons(self, show_success_actions: bool, show_view_logs: bool) -> None:
        self.open_target_button.setVisible(show_success_actions)
        self.rollback_button.setVisible(show_success_actions)
        self.view_logs_button.setVisible(show_view_logs)

    def _make_placeholder_icon(self) -> QIcon:
        pix = QPixmap(48, 48)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw rounded rect background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#E5E7EB"))
        painter.drawRoundedRect(pix.rect(), 8, 8)

        # Draw Text
        painter.setPen(QColor("#6B7280"))
        font = painter.font()
        font.setPixelSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignCenter, "RP")

        painter.end()
        return QIcon(pix)

    def refresh_packs(self) -> None:
        # 保存当前垂直滚动位置，刷新后恢复，避免删除/刷新后跳回顶部。
        # 使用 min(old, maximum()) 防止行数减少后越界。
        old_scroll = self.pack_table.verticalScrollBar().value()

        previous = self.selected_pack.folder_name if self.selected_pack else None
        self.packs = self.scan_service.scan()
        self.log_service.info(f"扫描到的资源包数量: {len(self.packs)}")

        self.pack_table.setRowCount(len(self.packs))
        placeholder_icon = self._make_placeholder_icon()

        for row, pack in enumerate(self.packs):
            icon = placeholder_icon
            if pack.icon_path:
                pixmap = QPixmap(str(pack.icon_path))
                if not pixmap.isNull():
                    icon = QIcon(pixmap)

            name_item = QTableWidgetItem(icon, pack.display_name)
            name_item.setToolTip(str(pack.path))
            self.pack_table.setItem(row, 0, name_item)

        self._restore_selection(previous)
        self._update_watch_paths()

        # 在事件循环下一拍恢复滚动位置，确保表格行高/视口布局已更新、maximum() 有效。
        # 回调内重新获取 verticalScrollBar()，不捕获刷新前的滚动条对象。
        def restore_scroll() -> None:
            scroll_bar = self.pack_table.verticalScrollBar()
            scroll_bar.setValue(min(old_scroll, scroll_bar.maximum()))

        QTimer.singleShot(0, restore_scroll)

    def _restore_selection(self, previous_folder: str | None) -> None:
        if not self.packs:
            self.selected_pack = None
            return

        row_to_select = 0
        if previous_folder:
            for idx, pack in enumerate(self.packs):
                if pack.folder_name == previous_folder:
                    row_to_select = idx
                    break

        self.pack_table.selectRow(row_to_select)
        self.selected_pack = self.packs[row_to_select]

    def _on_selection_changed(self) -> None:
        row = self.pack_table.currentRow()
        if row < 0 or row >= len(self.packs):
            self.selected_pack = None
            return
        self.selected_pack = self.packs[row]

    def _on_table_double_clicked(self, *_args) -> None:
        self.enter_import_page()

    def _open_pack_by_row(self, row: int) -> None:
        if 0 <= row < len(self.packs):
            self.pack_table.selectRow(row)
            self.selected_pack = self.packs[row]
            open_path(self.packs[row].path)

    def _delete_pack_by_row(self, row: int) -> None:
        if 0 <= row < len(self.packs):
            pack = self.packs[row]

            # 确认弹窗
            reply = QMessageBox.warning(
                self,
                "确认删除",
                f"是否确认将资源包移入回收站？\n\n名称：{pack.display_name}\n路径：{pack.path}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                result = self.delete_service.delete_pack(pack)
                if result.success:
                    QMessageBox.information(self, "删除成功", result.message)
                    self.refresh_packs()
                else:
                    QMessageBox.critical(self, "删除失败", result.message)
            else:
                self.log_service.info(f"用户取消删除资源包: {pack.path}")

    def _delete_all_packs(self) -> None:
        if not self.packs:
            QMessageBox.information(self, "提示", "当前没有可删除的资源包。")
            return

        packs_to_delete = list(self.packs)
        total = len(packs_to_delete)

        names_to_show = [p.display_name for p in packs_to_delete[:10]]
        names_str = "\n".join(f"- {n}" for n in names_to_show)
        if total > 10:
            names_str += f"\n...等共 {total} 个资源包（完整详情见日志）"

        reply = QMessageBox.warning(
            self,
            "确认批量删除",
            f"是否确认将当前列表中的 {total} 个资源包移入回收站？\n\n{names_str}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.log_service.info(f"开始批量删除 {total} 个资源包...")

        self.delete_all_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.open_logs_button.setEnabled(False)
        self.pack_table.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.fs_watcher.blockSignals(True)

        success_count = 0
        failed_items = []

        try:
            for pack in packs_to_delete:
                try:
                    result = self.delete_service.delete_pack(pack)
                    if result.success:
                        success_count += 1
                        self.log_service.info(f"成功移入回收站: {pack.display_name} ({pack.path})")
                    else:
                        failed_items.append((pack.display_name, str(pack.path), result.message))
                except Exception as exc:  # noqa: BLE001
                    self.log_service.error(f"单包删除发生异常: {pack.display_name} - {exc}")
                    failed_items.append((pack.display_name, str(pack.path), f"执行异常: {exc}"))
        finally:
            self.fs_watcher.blockSignals(False)
            QApplication.restoreOverrideCursor()
            self.delete_all_button.setEnabled(True)
            self.refresh_button.setEnabled(True)
            self.open_logs_button.setEnabled(True)
            self.pack_table.setEnabled(True)

        # 刷新单独捕获，避免扫描异常吞掉批量删除的结果汇总与结束日志
        try:
            self.refresh_packs()
        except Exception as exc:  # noqa: BLE001
            self.log_service.error(f"批量删除后刷新列表失败: {exc}")

        self.log_service.info(f"批量删除结束: 成功 {success_count} 个, 失败 {len(failed_items)} 个")

        if failed_items:
            for name, path, reason in failed_items:
                self.log_service.error(f"删除失败项: {name} ({path}) - 原因: {reason}")

            error_msg = f"批量删除完成。\n成功: {success_count} 个\n失败: {len(failed_items)} 个\n\n失败项示例:\n"
            for i, (name, path, reason) in enumerate(failed_items[:10]):
                error_msg += f"- {name}: {reason}\n"
            if len(failed_items) > 10:
                error_msg += "...\n完整失败列表请查看日志。"

            QMessageBox.warning(self, "批量删除完成(部分失败)", error_msg)
        else:
            success_msg = f"批量删除完成。\n成功: {success_count} 个\n失败: 0 个"
            QMessageBox.information(self, "批量删除完成", success_msg)

    def enter_import_page(self) -> None:
        if not self.selected_pack:
            QMessageBox.warning(self, "提示", "请先在列表中选择一个目标资源包。")
            return

        self.validation_result = None
        self.selected_archive = None
        self.replace_button.setEnabled(False)
        self.result_label.setText("")
        self._toggle_result_buttons(False, False)

        self.target_label.setText(f"{self.selected_pack.display_name} ({self.selected_pack.folder_name})")
        self.file_label.setText("未选择")
        self.validate_label.setText("请先选择 .zip 或 .mcpack 文件")
        self.validate_label.setStyleSheet("color: #6B7280; font-size: 13px; margin-top: 8px;")

        # 每次进入导入页重置替换模式为“全量替换”，不持久化用户上次选择。
        default_mode_button = self.mode_group.button(0)
        if default_mode_button is not None:
            default_mode_button.setChecked(True)

        self.stack.setCurrentWidget(self.import_page)

    def _go_main(self) -> None:
        self.stack.setCurrentWidget(self.main_page)

    def _choose_import_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择资源包",
            "",
            "Bedrock Resourcepack (*.zip *.mcpack)",
        )
        if file_path:
            self._set_archive_file(Path(file_path))

    def _set_archive_file(self, path: Path) -> None:
        self.selected_archive = path
        self.file_label.setText(f"{path.name}")
        self.file_label.setToolTip(str(path))
        self.log_service.info(f"导入文件路径: {path}")
        self._validate_current_archive()

    def _validate_current_archive(self) -> None:
        if not self.selected_archive:
            return
        result = self.import_service.validate_archive(self.selected_archive)
        self.validation_result = result
        self.log_service.info(f"校验结果: {result.valid}, {result.message}")

        self.validate_label.setText(result.message)
        if result.valid:
            self.validate_label.setStyleSheet("color: #059669; font-size: 13px; font-weight: bold; margin-top: 8px;")
            self.replace_button.setEnabled(True)
        else:
            self.validate_label.setStyleSheet("color: #DC2626; font-size: 13px; font-weight: bold; margin-top: 8px;")
            self.replace_button.setEnabled(False)

    def _do_replace(self) -> None:
        if not self.selected_pack or not self.validation_result or not self.validation_result.valid:
            QMessageBox.warning(self, "提示", "请先选择并通过校验后再执行替换。")
            return

        mode = self.mode_map.get(self.mode_group.checkedId(), ReplaceMode.FULL)
        result = self.replace_service.replace_from_archive(self.selected_pack, self.validation_result, mode)
        self.result_label.setText(result.message)

        if result.success:
            self.result_label.setStyleSheet("color: #059669; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
            self._toggle_result_buttons(True, False)
            QMessageBox.information(self, "替换成功", result.message)
            self.refresh_packs()
        else:
            self.result_label.setStyleSheet("color: #DC2626; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
            self._toggle_result_buttons(False, True)
            QMessageBox.critical(self, "替换失败", result.message)

    def _rollback_latest(self) -> None:
        if not self.selected_pack:
            QMessageBox.warning(self, "提示", "未找到目标资源包。")
            return
        result = self.replace_service.rollback_latest(self.selected_pack)
        self.result_label.setText(result.message)
        if result.success:
            self.result_label.setStyleSheet("color: #059669; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
            QMessageBox.information(self, "回滚完成", result.message)
            self.refresh_packs()
        else:
            self.result_label.setStyleSheet("color: #DC2626; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
            self._toggle_result_buttons(False, True)
            QMessageBox.critical(self, "回滚失败", result.message)

    def _open_target_folder(self) -> None:
        if self.selected_pack:
            open_path(self.selected_pack.path)

    def _schedule_refresh(self) -> None:
        self.refresh_debounce.start()

    def _update_watch_paths(self) -> None:
        existing = set(self.fs_watcher.directories())
        if existing:
            self.fs_watcher.removePaths(list(existing))

        if self.packcache_dir.exists():
            self.fs_watcher.addPath(str(self.packcache_dir))
