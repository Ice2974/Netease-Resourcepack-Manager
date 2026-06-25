from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.utils import theme


class _FakeReg:
    """模拟 winreg 模块：仅提供 get_system_app_mode 用到的 API。"""

    HKEY_CURRENT_USER = 1

    def __init__(self, value, raise_missing: bool = False) -> None:
        self._value = value
        self._raise_missing = raise_missing
        self.opened = []

    class _Ctx:
        def __init__(self, fake) -> None:
            self._fake = fake

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def OpenKey(self, root, subkey):  # noqa: N802
        if self._raise_missing:
            raise FileNotFoundError(subkey)
        self.opened.append((root, subkey))
        return self._Ctx(self)

    def QueryValueEx(self, key, name):  # noqa: N802
        return (self._value, 4)  # REG_DWORD == 4


class SystemAppModeTests(unittest.TestCase):
    def test_light_when_apps_use_light_theme_is_1(self) -> None:
        fake = _FakeReg(value=1)
        with patch.object(theme, "winreg", fake):
            self.assertEqual(theme.get_system_app_mode(), "light")

    def test_dark_when_apps_use_light_theme_is_0(self) -> None:
        fake = _FakeReg(value=0)
        with patch.object(theme, "winreg", fake):
            self.assertEqual(theme.get_system_app_mode(), "dark")

    def test_light_when_registry_key_missing(self) -> None:
        fake = _FakeReg(value=1, raise_missing=True)
        with patch.object(theme, "winreg", fake):
            self.assertEqual(theme.get_system_app_mode(), "light")

    def test_light_when_winreg_unavailable(self) -> None:
        # 非 Windows 平台：winreg 为 None
        with patch.object(theme, "winreg", None):
            self.assertEqual(theme.get_system_app_mode(), "light")


class QssSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        # 准备两个可区分的 QSS 文本，避免依赖真实 styles.qss 内容
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ui_dir = self.root / "app" / "ui"
        self.ui_dir.mkdir(parents=True)
        (self.ui_dir / "styles.qss").write_text("/* LIGHT */", encoding="utf-8")
        (self.ui_dir / "styles_dark.qss").write_text("/* DARK */", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _patch_base_dir(self):
        # 让 get_resource_path 指向临时目录
        return patch.object(
            theme, "get_resource_path", lambda *parts: self.root.joinpath(*parts)
        )

    def test_light_qss_selected_in_light_mode(self) -> None:
        with patch.object(theme, "winreg", _FakeReg(value=1)), self._patch_base_dir():
            self.assertEqual(theme.get_qss_text(), "/* LIGHT */")

    def test_dark_qss_selected_in_dark_mode(self) -> None:
        with patch.object(theme, "winreg", _FakeReg(value=0)), self._patch_base_dir():
            self.assertEqual(theme.get_qss_text(), "/* DARK */")

    def test_empty_when_qss_file_missing(self) -> None:
        (self.ui_dir / "styles_dark.qss").unlink()
        with patch.object(theme, "winreg", _FakeReg(value=0)), self._patch_base_dir():
            self.assertEqual(theme.get_qss_text(), "")


if __name__ == "__main__":
    unittest.main()
