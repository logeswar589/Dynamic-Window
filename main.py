"""
main.py – DynamicWin entry point.
Sets up the QApplication, system tray, hotkey listener, media
listener, and launches the Dynamic Island.
"""

import sys
import os
import winreg
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QFont
from PySide6.QtCore import Qt, QSize

from island import DynamicIsland
from keyboard_listener import HotkeyListener
from win_media_listener import MediaListener


def set_startup(enabled: bool):
    """Enable or disable start on startup via Windows registry."""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "DynamicWin"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enabled:
            pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
            main_py = os.path.abspath(sys.argv[0])
            cmd = f'"{pythonw_exe}" "{main_py}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def is_startup_enabled() -> bool:
    """Check if start on startup is enabled in registry."""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "DynamicWin"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _create_tray_icon() -> QIcon:
    """Generate a simple pill-shaped tray icon programmatically."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(18, 18, 20))
    p.setPen(QColor(255, 255, 255, 60))
    margin = 8
    p.drawRoundedRect(margin, size // 2 - 8, size - margin * 2, 16, 8, 8)
    p.end()
    return QIcon(pm)


def main():

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("DynamicWin")


    island = DynamicIsland()
    island.show()


    media = MediaListener(poll_interval_ms=1000)


    media.media_changed.connect(island._media.update_media)
    media.thumbnail_changed.connect(island._media.update_thumbnail)
    media.media_changed.connect(
        lambda t, a, playing, aumid: island.set_media_active(bool(t))
    )
    media.session_lost.connect(lambda: island.set_media_active(False))


    island._media.play_pause_clicked.connect(media.try_play_pause)
    island._media.next_clicked.connect(media.try_next)
    island._media.prev_clicked.connect(media.try_prev)

    media.start()


    hotkey = HotkeyListener()

    def _toggle():
        island.toggle_island()

    hotkey.triggered.connect(_toggle)
    hotkey.start()


    tray = QSystemTrayIcon(_create_tray_icon(), island)

    menu = QMenu(island)
    menu.setStyleSheet("""
        QMenu {
            background: #0a0a0a;
            color: #ffffff;
            border: 1px solid rgba(255,255,255,20);
            border-radius: 6px;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 20px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background: rgba(255,255,255,20);
        }
    """)

    act_toggle = QAction("Toggle Island", menu)
    act_toggle.triggered.connect(_toggle)
    menu.addAction(act_toggle)

    act_startup = QAction("Start on Startup", menu, checkable=True)
    act_startup.setChecked(is_startup_enabled())
    act_startup.triggered.connect(set_startup)
    menu.addAction(act_startup)

    menu.addSeparator()

    act_quit = QAction("Quit", menu)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_quit)

    tray.setContextMenu(menu)
    tray.setToolTip("DynamicWin – Ctrl+Win+Space to toggle")

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            _toggle()
    tray.activated.connect(on_tray_activated)
    
    tray.show()


    code = app.exec()
    hotkey.stop()
    media.stop()
    sys.exit(code)


if __name__ == "__main__":
    import os, traceback, logging
    _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
    logging.basicConfig(
        filename=_log_path,
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)s  %(message)s",
    )
    logging.info("DynamicWin starting...")
    try:
        main()
    except Exception:
        logging.exception("FATAL – unhandled exception")
        raise
