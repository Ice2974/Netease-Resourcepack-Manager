from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget

from app.utils import dark_titlebar

# QWidget 构造需要 QApplication 实例
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class SetDarkModeTests(unittest.TestCase):
    def _fake_dwm(self, return_values):
        calls = []

        def _set(hwnd, attr, ptr, size):
            calls.append({"hwnd": hwnd, "attr": attr})
            return return_values.pop(0)

        fake = MagicMock()
        fake.DwmSetWindowAttribute.side_effect = _set
        fake._calls = calls
        return fake

    def test_success_with_attr_20_does_not_try_19(self) -> None:
        fake = self._fake_dwm([0])  # S_OK on attr 20
        with patch.object(dark_titlebar, "_dwm", fake):
            self.assertTrue(dark_titlebar._set_dark_mode(12345, True))
        self.assertEqual([c["attr"] for c in fake._calls], [20])

    def test_fallback_to_attr_19_when_20_fails(self) -> None:
        fake = self._fake_dwm([-1, 0])  # attr 20 失败，19 成功
        with patch.object(dark_titlebar, "_dwm", fake):
            self.assertTrue(dark_titlebar._set_dark_mode(12345, True))
        self.assertEqual([c["attr"] for c in fake._calls], [20, 19])

    def test_returns_false_when_all_attrs_fail(self) -> None:
        fake = self._fake_dwm([-1, -1])
        with patch.object(dark_titlebar, "_dwm", fake):
            self.assertFalse(dark_titlebar._set_dark_mode(12345, True))

    def test_returns_false_when_dwm_unavailable(self) -> None:
        with patch.object(dark_titlebar, "_dwm", None):
            self.assertFalse(dark_titlebar._set_dark_mode(12345, True))

    def test_returns_false_when_hwnd_zero(self) -> None:
        fake = self._fake_dwm([0])
        with patch.object(dark_titlebar, "_dwm", fake):
            self.assertFalse(dark_titlebar._set_dark_mode(0, True))
        fake.DwmSetWindowAttribute.assert_not_called()


class ApplyDarkTitlebarTests(unittest.TestCase):
    def test_returns_false_on_non_windows(self) -> None:
        fake_sys = SimpleNamespace(platform="linux")
        widget = MagicMock()
        with patch.object(dark_titlebar, "sys", fake_sys):
            self.assertFalse(dark_titlebar.apply_dark_titlebar(widget, True))

    def test_invokes_set_dark_mode_on_windows(self) -> None:
        fake_sys = SimpleNamespace(platform="win32")
        widget = MagicMock()
        widget.winId.return_value = 4242
        with patch.object(dark_titlebar, "sys", fake_sys), \
                patch.object(dark_titlebar, "_dwm", MagicMock()), \
                patch.object(dark_titlebar, "_set_dark_mode", return_value=True) as m:
            self.assertTrue(dark_titlebar.apply_dark_titlebar(widget, True))
            m.assert_called_once_with(4242, True)


class DarkTitlebarFilterTests(unittest.TestCase):
    def test_applies_on_show_for_top_level_widget(self) -> None:
        flt = dark_titlebar.DarkTitlebarFilter()
        widget = QWidget()
        event = MagicMock()
        event.type.return_value = QEvent.Show
        with patch.object(dark_titlebar, "apply_dark_titlebar", return_value=True) as m:
            flt.eventFilter(widget, event)
            m.assert_called_once_with(widget, True)

    def test_ignores_non_show_events(self) -> None:
        flt = dark_titlebar.DarkTitlebarFilter()
        widget = QWidget()
        event = MagicMock()
        event.type.return_value = QEvent.Resize
        with patch.object(dark_titlebar, "apply_dark_titlebar") as m:
            flt.eventFilter(widget, event)
            m.assert_not_called()


if __name__ == "__main__":
    unittest.main()
