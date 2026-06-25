from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QEvent, QObject

# DWMWA_USE_IMMERSIVE_DARK_MODE：Win10 2004 (build 19041) 起为 20；
# 更早的 Win10 1809 (17763) 使用别名 19。按 20 → 19 顺序尝试。
_ATTR_DARK_MODE = (20, 19)

try:  # dwmapi 仅 Windows 存在；非 Windows 导入阶段不报错，运行时降级
    _dwm = ctypes.windll.dwmapi  # type: ignore[attr-defined]
    _dwm.DwmSetWindowAttribute.argtypes = [
        wintypes.HWND,
        ctypes.c_uint,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _dwm.DwmSetWindowAttribute.restype = ctypes.c_long  # HRESULT
except (AttributeError, OSError):  # pragma: no cover - 非 Windows 平台
    _dwm = None


def _set_dark_mode(hwnd: int, enabled: bool) -> bool:
    """对指定窗口句柄设置沉浸式深色标题栏。成功返回 True。"""
    if _dwm is None or not hwnd:
        return False
    value = ctypes.c_int(1 if enabled else 0)
    for attr in _ATTR_DARK_MODE:
        hr = _dwm.DwmSetWindowAttribute(
            hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
        )
        if hr == 0:  # S_OK
            return True
    return False


def apply_dark_titlebar(widget, dark: bool) -> bool:
    """对 Qt 顶层窗口应用深色标题栏。

    需要窗口已具备原生句柄（通常在 ``show()`` 之后）。非 Windows 平台、
    缺少 dwmapi 或无法获取句柄时静默返回 False，不影响程序运行。
    """
    if sys.platform != "win32" or _dwm is None:
        return False
    try:
        hwnd = int(widget.winId())
    except Exception:  # noqa: BLE001 - winId 在极少数情况下可能抛出
        return False
    return _set_dark_mode(hwnd, dark)


class DarkTitlebarFilter(QObject):
    """全局事件过滤器：在顶层窗口显示时自动应用深色标题栏。

    装在 ``QApplication`` 上后，主窗口与所有 QMessageBox 等弹窗在 ``Show``
    /``WinIdChange`` 时被捕获，无需逐个调用点改动。仅深色模式安装此过滤器。
    """

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() in (QEvent.Show, QEvent.WinIdChange):
            if obj.isWidgetType() and obj.isWindow():
                apply_dark_titlebar(obj, True)
        return False
