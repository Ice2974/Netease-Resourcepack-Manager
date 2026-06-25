from __future__ import annotations

try:  # winreg 仅 Windows 平台提供；非 Windows 导入失败时降级为浅色
    import winreg  # type: ignore
except ImportError:  # pragma: no cover - 非 Windows 平台
    winreg = None  # type: ignore

from app.utils.runtime_paths import get_resource_path

# Windows「选择默认应用模式」注册表子键
_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def get_system_app_mode() -> str:
    """读取 Windows「默认应用模式」。

    返回 ``"light"`` 或 ``"dark"``：
    - ``AppsUseLightTheme == 1`` → 亮色应用模式 → ``"light"``
    - ``AppsUseLightTheme == 0`` → 暗色应用模式 → ``"dark"``

    任何异常（键缺失、权限不足、非 Windows 平台无 ``winreg``）一律降级为
    ``"light"``，保证不阻断启动。
    """
    if winreg is None:
        return "light"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SUBKEY) as key:
            value, _reg_type = winreg.QueryValueEx(key, "AppsUseLightTheme")
    except OSError:
        return "light"
    return "light" if value == 1 else "dark"


def get_qss_text() -> str:
    """根据系统应用模式返回对应 QSS 文本。

    浅色模式读取 ``app/ui/styles.qss``，深色模式读取 ``app/ui/styles_dark.qss``。
    目标文件缺失时返回空串（与历史 ``main.py`` 的容错行为一致）。
    """
    filename = "styles.qss" if get_system_app_mode() == "light" else "styles_dark.qss"
    qss_path = get_resource_path("app", "ui", filename)
    if not qss_path.exists():
        return ""
    return qss_path.read_text(encoding="utf-8")
