"""
widgets/idle.py – Collapsed "idle" pill showing the current time.
Extremely lightweight: one QTimer, one paintEvent.
"""

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel

import styles as S
from widgets.base import IslandWidget


class IdleWidget(IslandWidget):
    """Compact clock pill shown when nothing is active."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._time_label = QLabel()
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(S.FONT_FAMILY.split(",")[0].strip(), S.FONT_SIZE_MD)
        font.setWeight(QFont.Weight(S.FONT_WEIGHT_MEDIUM))
        self._time_label.setFont(font)
        r, g, b, a = S.TEXT_PRIMARY
        self._time_label.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        layout.addWidget(self._time_label)

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(S.CLOCK_TICK_MS)
        self._tick()

    def preferred_size(self) -> tuple[int, int]:
        return S.ISLAND_IDLE_W, S.ISLAND_IDLE_H

    def activate(self):
        super().activate()
        self._timer.start()

    def deactivate(self):
        self._timer.stop()
        super().deactivate()

    def refresh_style(self):
        r, g, b, a = S.TEXT_PRIMARY
        self._time_label.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")

    def _tick(self):
        now = datetime.now()
        self._time_label.setText(now.strftime("%I:%M %p").lstrip("0"))
