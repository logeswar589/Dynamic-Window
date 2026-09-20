"""
keyboard_listener.py – Win32 RegisterHotKey for Ctrl+Win toggle.
Uses a native Windows message filter inside the Qt event loop so
no extra thread or pynput dependency is required.
"""

import ctypes
import ctypes.wintypes

from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter, QByteArray
from PySide6.QtWidgets import QApplication



MOD_CONTROL = 0x0002
MOD_WIN     = 0x0008
MOD_NOREPEAT = 0x4000
VK_SPACE    = 0x20

WM_HOTKEY   = 0x0312
HOTKEY_ID   = 42069


class _NativeFilter(QAbstractNativeEventFilter):
    """Intercept WM_HOTKEY inside the Qt event loop."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type: QByteArray | bytes, message):

        if event_type == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self._callback()
                    return True, 0
            except Exception:
                pass
        return False, 0


class HotkeyListener(QObject):
    """Registers Ctrl + Win + Space as a global hotkey."""

    triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter: _NativeFilter | None = None
        self._registered = False

    def start(self):
        mods = MOD_CONTROL | MOD_WIN | MOD_NOREPEAT
        ok = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, mods, VK_SPACE)
        self._registered = bool(ok)

        self._filter = _NativeFilter(self.triggered.emit)
        app = QApplication.instance()
        if app:
            app.installNativeEventFilter(self._filter)

    def stop(self):
        if self._registered:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            self._registered = False
        app = QApplication.instance()
        if app and self._filter:
            app.removeNativeEventFilter(self._filter)
