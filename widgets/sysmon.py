"""
widgets/sysmon.py – System Monitor widget.
Shows CPU %, RAM %, and Battery % with animated gradient bars.
Uses psutil with a 2-second poll to keep CPU usage negligible.
"""

import psutil
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QFont, QPainter, QColor, QLinearGradient, QPen, QPainterPath,
)
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget

import styles as S
from widgets.base import IslandWidget


class _BarWidget(QWidget):
    """A single animated metric bar (painted, no stylesheets)."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._display_value = 0.0  # smoothly interpolated
        self._label = label
        self.setFixedHeight(24)

    def set_value(self, v: float):
        self._value = max(0.0, min(v, 100.0))

    def paintEvent(self, _event):
        # Smooth interpolation toward target value
        self._display_value += (self._value - self._display_value) * 0.25

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bar_h = 4
        bar_y = (h - bar_h) // 2
        radius = bar_h / 2

        # 1. Draw Label (Left)
        font = QFont(S.FONT_FAMILY, S.FONT_SIZE_SM)
        font.setWeight(QFont.Weight(S.FONT_WEIGHT_MEDIUM))
        p.setFont(font)
        p.setPen(QColor(*S.TEXT_SECONDARY[:3], 200))
        p.drawText(QRectF(0, 0, 40, h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        # 2. Draw Value (Right)
        p.setPen(QColor(*S.TEXT_PRIMARY[:3], 240))
        val_str = f"{self._display_value:.0f}%"
        p.drawText(QRectF(w - 40, 0, 40, h), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, val_str)

        # 3. Draw Bar Track (Middle)
        bar_start_x = 48
        bar_width = w - bar_start_x - 48
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(*S.ACCENT_WHITE, 20))
        p.drawRoundedRect(QRectF(bar_start_x, bar_y, bar_width, bar_h), radius, radius)

        # 4. Draw Bar Fill
        fill_width = max(bar_h, bar_width * self._display_value / 100.0)
        p.setBrush(QColor(*S.ACCENT_WHITE, 230))
        p.drawRoundedRect(QRectF(bar_start_x, bar_y, fill_width, bar_h), radius, radius)

        p.end()


class SysMonWidget(IslandWidget):
    """Expanded system-monitor panel: CPU / RAM / Battery."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(2)

        # Title
        self._title = QLabel("System")
        font = QFont(S.FONT_FAMILY, S.FONT_SIZE_MD)
        font.setWeight(QFont.Weight(S.FONT_WEIGHT_BOLD))
        self._title.setFont(font)
        r, g, b, a = S.TEXT_PRIMARY
        self._title.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        layout.addWidget(self._title)

        self._cpu_bar = _BarWidget("CPU", self)
        self._ram_bar = _BarWidget("RAM", self)
        self._bat_bar = _BarWidget("BAT", self)
        layout.addWidget(self._cpu_bar)
        layout.addWidget(self._ram_bar)
        layout.addWidget(self._bat_bar)

        # Poll timer
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._timer.timeout.connect(self._poll)
        self._timer.setInterval(S.SYSMON_POLL_MS)

        # Repaint timer for smooth bar interpolation (30 fps)
        self._paint_timer = QTimer(self)
        self._paint_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._paint_timer.timeout.connect(self._repaint_bars)
        self._paint_timer.setInterval(33)

    def preferred_size(self) -> tuple[int, int]:
        return S.ISLAND_EXPAND_W, 116

    def activate(self):
        super().activate()
        self._poll()  # immediate first read
        self._timer.start()
        self._paint_timer.start()

    def deactivate(self):
        self._timer.stop()
        self._paint_timer.stop()
        super().deactivate()

    def refresh_style(self):
        r, g, b, a = S.TEXT_PRIMARY
        self._title.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        self._cpu_bar.update()
        self._ram_bar.update()
        self._bat_bar.update()

    def _poll(self):
        self._cpu_bar.set_value(psutil.cpu_percent(interval=None))
        self._ram_bar.set_value(psutil.virtual_memory().percent)
        bat = psutil.sensors_battery()
        self._bat_bar.set_value(bat.percent if bat else 0)

    def _repaint_bars(self):
        self._cpu_bar.update()
        self._ram_bar.update()
        self._bat_bar.update()
