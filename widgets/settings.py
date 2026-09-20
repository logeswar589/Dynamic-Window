"""
widgets/settings.py – Settings panel widget.
Theme selection (Black / White), Glassy UI toggle,
Start-on-Startup toggle, and Close button.
"""

import sys
import os
import winreg

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QApplication, QSizePolicy,
)

import styles as S
from widgets.base import IslandWidget


_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "DynamicWin"


def _is_startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _set_startup(enabled: bool):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_ALL_ACCESS)
        if enabled:
            pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
            main_py = os.path.abspath(sys.argv[0])
            cmd = f'"{pythonw_exe}" "{main_py}"'
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


class _ToggleSwitch(QWidget):
    """Minimal iOS-style toggle switch, painted."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(36, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, v: bool):
        self._checked = v
        self.update()
        self.toggled.emit(v)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)
        event.accept()  # ← consume event so it doesn't cycle the island

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        radius = h / 2

        is_dark = S.CURRENT_THEME == "black"

        # Track
        if self._checked:
            track_color = QColor(255, 255, 255, 200) if is_dark else QColor(30, 30, 30, 210)
        else:
            track_color = QColor(255, 255, 255, 40) if is_dark else QColor(0, 0, 0, 30)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Knob
        knob_r = h - 4
        margin = 2
        if self._checked:
            knob_x = w - knob_r - margin
            knob_color = QColor(10, 10, 10) if is_dark else QColor(255, 255, 255)
        else:
            knob_x = margin
            knob_color = QColor(180, 180, 180) if is_dark else QColor(160, 160, 160)
        p.setBrush(knob_color)
        p.drawEllipse(QRectF(knob_x, margin, knob_r, knob_r))
        p.end()


class _ThemePill(QPushButton):
    """Small selectable pill for a theme option."""

    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self._selected = False
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def set_selected(self, sel: bool):
        self._selected = sel
        self._apply_style()

    def _apply_style(self):
        is_dark = S.CURRENT_THEME == "black"
        if self._selected:
            if is_dark:
                self.setStyleSheet(f"""
                    QPushButton {{
                        color: rgba(0,0,0,230);
                        background: rgba(255,255,255,220);
                        border: none; border-radius: 13px;
                        font-size: {S.FONT_SIZE_SM}px; font-weight: 600;
                        padding: 0 14px;
                    }}
                """)
            else:
                self.setStyleSheet(f"""
                    QPushButton {{
                        color: rgba(255,255,255,240);
                        background: rgba(20,20,20,220);
                        border: none; border-radius: 13px;
                        font-size: {S.FONT_SIZE_SM}px; font-weight: 600;
                        padding: 0 14px;
                    }}
                """)
        else:
            if is_dark:
                self.setStyleSheet(f"""
                    QPushButton {{
                        color: rgba(255,255,255,160);
                        background: rgba(255,255,255,12);
                        border: none; border-radius: 13px;
                        font-size: {S.FONT_SIZE_SM}px; padding: 0 14px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255,255,255,25);
                        color: rgba(255,255,255,220);
                    }}
                """)
            else:
                self.setStyleSheet(f"""
                    QPushButton {{
                        color: rgba(0,0,0,140);
                        background: rgba(0,0,0,8);
                        border: none; border-radius: 13px;
                        font-size: {S.FONT_SIZE_SM}px; padding: 0 14px;
                    }}
                    QPushButton:hover {{
                        background: rgba(0,0,0,18);
                        color: rgba(0,0,0,200);
                    }}
                """)


class SettingsWidget(IslandWidget):
    """Settings panel: themes, glassy-UI, start-on-startup, close."""

    theme_changed = Signal(str)        # "black" or "white"
    glassy_changed = Signal(bool)
    startup_changed = Signal(bool)
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme = "black"

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(8)

        header = QHBoxLayout()
        self._title = QLabel("Settings")
        font = QFont(S.FONT_FAMILY.split(",")[0].strip(), S.FONT_SIZE_MD)
        font.setWeight(QFont.Weight(S.FONT_WEIGHT_BOLD))
        self._title.setFont(font)
        header.addWidget(self._title)
        header.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._on_close)
        header.addWidget(self._close_btn)
        root.addLayout(header)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(6)

        lbl_font = QFont(S.FONT_FAMILY.split(",")[0].strip(), S.FONT_SIZE_SM)
        lbl_font.setWeight(QFont.Weight(S.FONT_WEIGHT_MEDIUM))

        self._theme_label = QLabel("Theme")
        self._theme_label.setFont(lbl_font)
        theme_row.addWidget(self._theme_label)
        theme_row.addStretch()

        self._pill_black = _ThemePill("Black", self)
        self._pill_white = _ThemePill("White", self)
        self._pill_black.set_selected(True)
        self._pill_black.clicked.connect(lambda: self._select_theme("black"))
        self._pill_white.clicked.connect(lambda: self._select_theme("white"))
        theme_row.addWidget(self._pill_black)
        theme_row.addWidget(self._pill_white)
        root.addLayout(theme_row)

        glassy_row = QHBoxLayout()
        self._glassy_label = QLabel("Glassy UI")
        self._glassy_label.setFont(lbl_font)
        glassy_row.addWidget(self._glassy_label)
        glassy_row.addStretch()
        self._glassy_toggle = _ToggleSwitch(False, self)
        self._glassy_toggle.toggled.connect(self._on_glassy_changed)
        glassy_row.addWidget(self._glassy_toggle)
        root.addLayout(glassy_row)

        startup_row = QHBoxLayout()
        self._startup_label = QLabel("Start on Start")
        self._startup_label.setFont(lbl_font)
        startup_row.addWidget(self._startup_label)
        startup_row.addStretch()
        self._startup_toggle = _ToggleSwitch(_is_startup_enabled(), self)
        self._startup_toggle.toggled.connect(self._on_startup_changed)
        startup_row.addWidget(self._startup_toggle)
        root.addLayout(startup_row)

        root.addStretch()
        self._apply_styles()

    def preferred_size(self) -> tuple[int, int]:
        return S.ISLAND_EXPAND_W, 150

    def activate(self):
        self._startup_toggle._checked = _is_startup_enabled()
        self._startup_toggle.update()
        super().activate()

    def refresh_style(self):
        """Re-apply all styles after a theme change."""
        self._apply_styles()
        self._pill_black.set_selected(self._current_theme == "black")
        self._pill_white.set_selected(self._current_theme == "white")
        self._glassy_toggle.update()
        self._startup_toggle.update()

    def _apply_styles(self):
        """Set all label / button styles from the current S.* colours."""
        r, g, b, a = S.TEXT_PRIMARY
        self._title.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")

        r2, g2, b2, a2 = S.TEXT_SECONDARY
        for lbl in (self._theme_label, self._glassy_label, self._startup_label):
            lbl.setStyleSheet(f"color: rgba({r2},{g2},{b2},{a2}); background: transparent;")

        is_dark = S.CURRENT_THEME == "black"
        if is_dark:
            self._close_btn.setStyleSheet("""
                QPushButton {
                    color: rgba(255,255,255,140); background: transparent;
                    border: none; font-size: 12px; border-radius: 12px;
                }
                QPushButton:hover { background: rgba(255,70,70,160); color: white; }
            """)
        else:
            self._close_btn.setStyleSheet("""
                QPushButton {
                    color: rgba(0,0,0,120); background: transparent;
                    border: none; font-size: 12px; border-radius: 12px;
                }
                QPushButton:hover { background: rgba(255,70,70,160); color: white; }
            """)

    def _select_theme(self, theme: str):
        self._current_theme = theme
        self._pill_black.set_selected(theme == "black")
        self._pill_white.set_selected(theme == "white")
        self.theme_changed.emit(theme)

    def _on_glassy_changed(self, checked: bool):
        self.glassy_changed.emit(checked)

    def _on_startup_changed(self, checked: bool):
        _set_startup(checked)
        self.startup_changed.emit(checked)

    def _on_close(self):
        self.close_requested.emit()
        QApplication.quit()
