"""
widgets/timer.py – Timer and Stopwatch tools widget.
Provides a tabbed layout to toggle between stopwatch and countdown timer.
Uses system-level high-precision timers (time.perf_counter) and plays a
winsound alert on expiration.
"""

import time
import winsound
from PySide6.QtCore import Qt, QTimer, QRectF, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedLayout, QFrame, QGridLayout,
)

import styles as S
from widgets.base import IslandWidget


class TimerStopwatchWidget(IslandWidget):
    """Slide featuring both a Stopwatch and a countdown Timer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_tab = 0  # 0 = Timer, 1 = Stopwatch
        
        # Stopwatch states
        self._sw_running = False
        self._sw_elapsed = 0.0
        self._sw_start_time = 0.0
        
        # Timer states
        self._timer_running = False
        self._timer_duration = 300.0  # default 5 minutes
        self._timer_remaining = 300.0
        self._timer_start_time = 0.0
        self._timer_alarm_active = False
        self._alarm_flash_state = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 8, 14, 8)
        root_layout.setSpacing(6)

        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(10)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self._btn_tab_timer = QPushButton("Timer", self)
        self._btn_tab_sw = QPushButton("Stopwatch", self)
        
        for btn in (self._btn_tab_timer, self._btn_tab_sw):
            btn.setFixedSize(85, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
        self._btn_tab_timer.clicked.connect(lambda: self._set_tab(0))
        self._btn_tab_sw.clicked.connect(lambda: self._set_tab(1))

        tab_layout.addWidget(self._btn_tab_timer)
        tab_layout.addWidget(self._btn_tab_sw)
        tab_layout.addStretch()
        root_layout.addLayout(tab_layout)

        self._stack = QStackedLayout()
        
        # 1. Timer View
        self._timer_view = QWidget()
        self._init_timer_view()
        self._stack.addWidget(self._timer_view)
        
        # 2. Stopwatch View
        self._sw_view = QWidget()
        self._init_sw_view()
        self._stack.addWidget(self._sw_view)
        
        root_layout.addLayout(self._stack)

        # 30 FPS update for stopwatch, 100ms update for countdown
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_tick)
        self._poll_timer.setInterval(33)
        self._poll_timer.start()

        # Alarm flash timer (flashes every 500ms when expired)
        self._alarm_timer = QTimer(self)
        self._alarm_timer.timeout.connect(self._on_alarm_flash)
        self._alarm_timer.setInterval(500)

        self.refresh_style()
        self._set_tab(0)

    def preferred_size(self) -> tuple[int, int]:
        return S.ISLAND_EXPAND_W, S.ISLAND_EXPAND_H

    def activate(self):
        super().activate()

    def deactivate(self):
        super().deactivate()

    def refresh_style(self):
        is_light = S.CURRENT_THEME == "white"
        r_pri, g_pri, b_pri, a_pri = S.TEXT_PRIMARY
        r_sec, g_sec, b_sec, a_sec = S.TEXT_SECONDARY
        
        text_color = f"rgba({r_pri},{g_pri},{b_pri},{a_pri})"
        sec_color = f"rgba({r_sec},{g_sec},{b_sec},{a_sec})"
        bg_btn = "rgba(0, 0, 0, 15)" if is_light else "rgba(255, 255, 255, 12)"
        border_color = "rgba(0, 0, 0, 30)" if is_light else "rgba(255, 255, 255, 25)"

        # Style tab buttons
        active_sheet = f"""
            QPushButton {{
                background: rgba({r_pri},{g_pri},{b_pri}, 25);
                color: {text_color};
                border: 1px solid rgba({r_pri},{g_pri},{b_pri}, 60);
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }}
        """
        inactive_sheet = f"""
            QPushButton {{
                background: transparent;
                color: {sec_color};
                border: none;
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {text_color};
            }}
        """

        self._btn_tab_timer.setStyleSheet(active_sheet if self._current_tab == 0 else inactive_sheet)
        self._btn_tab_sw.setStyleSheet(active_sheet if self._current_tab == 1 else inactive_sheet)

        # Style controls
        self._lbl_timer_time.setStyleSheet(f"color: {text_color}; font-family: 'Consolas', 'Segoe UI Monospace', monospace; font-size: 26px; font-weight: bold;")
        self._lbl_sw_time.setStyleSheet(f"color: {text_color}; font-family: 'Consolas', 'Segoe UI Monospace', monospace; font-size: 28px; font-weight: bold;")

        btn_ctrl_sheet = f"""
            QPushButton {{
                background: {bg_btn};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background: rgba(0, 0, 0, 30) if is_light else rgba(255, 255, 255, 25);
            }}
        """
        
        self._btn_timer_start.setStyleSheet(btn_ctrl_sheet)
        self._btn_timer_reset.setStyleSheet(btn_ctrl_sheet)
        self._btn_timer_dismiss.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 59, 48, 220) if not is_light else rgba(255, 45, 85, 220);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background: rgba(255, 59, 48, 255) if not is_light else rgba(255, 45, 85, 255);
            }}
        """)
        self._btn_sw_start.setStyleSheet(btn_ctrl_sheet)
        self._btn_sw_reset.setStyleSheet(btn_ctrl_sheet)

        # Presets layout styling
        preset_sheet = f"""
            QPushButton {{
                background: {bg_btn};
                color: {sec_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                font-size: 9px;
            }}
            QPushButton:hover {{
                color: {text_color};
                background: rgba(0, 0, 0, 30) if is_light else rgba(255, 255, 255, 25);
            }}
        """
        for p_btn in self._preset_buttons:
            p_btn.setStyleSheet(preset_sheet)
        
        self._btn_inc.setStyleSheet(preset_sheet)
        self._btn_dec.setStyleSheet(preset_sheet)

        self._timer_view.update()
        self._sw_view.update()

    def _set_tab(self, index: int):
        self._current_tab = index
        self._stack.setCurrentIndex(index)
        self.refresh_style()

    def _init_timer_view(self):
        layout = QHBoxLayout(self._timer_view)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        # Left column (Timer countdown & controls)
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(6)

        self._lbl_timer_time = QLabel("05:00", self._timer_view)
        self._lbl_timer_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_col.addWidget(self._lbl_timer_time, stretch=1)

        # Start / Pause / Reset Row
        self._timer_ctrl_row = QWidget(self._timer_view)
        ctrl_layout = QHBoxLayout(self._timer_ctrl_row)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(8)

        self._btn_timer_start = QPushButton("Start", self._timer_ctrl_row)
        self._btn_timer_reset = QPushButton("Reset", self._timer_ctrl_row)
        
        self._btn_timer_start.clicked.connect(self._toggle_timer)
        self._btn_timer_reset.clicked.connect(self._reset_timer)
        
        self._btn_timer_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_timer_reset.setCursor(Qt.CursorShape.PointingHandCursor)

        ctrl_layout.addWidget(self._btn_timer_start)
        ctrl_layout.addWidget(self._btn_timer_reset)
        left_col.addWidget(self._timer_ctrl_row)

        # Alarm Dismiss Button (Hidden initially)
        self._btn_timer_dismiss = QPushButton("Dismiss Alarm", self._timer_view)
        self._btn_timer_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_timer_dismiss.clicked.connect(self._dismiss_alarm)
        self._btn_timer_dismiss.hide()
        left_col.addWidget(self._btn_timer_dismiss)

        layout.addLayout(left_col, stretch=3)

        # Right column (Quick Presets)
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(4)

        presets_grid = QGridLayout()
        presets_grid.setSpacing(4)
        presets_grid.setContentsMargins(0, 0, 0, 0)

        # Setup quick preset buttons
        self._preset_buttons = []
        presets = [("1m", 60), ("3m", 180), ("5m", 300), ("10m", 600)]
        for i, (name, val) in enumerate(presets):
            btn = QPushButton(name, self._timer_view)
            btn.setFixedSize(44, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, v=val: self._set_timer_duration(v))
            self._preset_buttons.append(btn)
            presets_grid.addWidget(btn, i // 2, i % 2)

        right_col.addLayout(presets_grid)

        # +/- Adjust Row
        adjust_layout = QHBoxLayout()
        adjust_layout.setSpacing(4)
        self._btn_dec = QPushButton("- 1m", self._timer_view)
        self._btn_inc = QPushButton("+ 1m", self._timer_view)
        
        for btn in (self._btn_dec, self._btn_inc):
            btn.setFixedSize(44, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
        self._btn_dec.clicked.connect(lambda: self._adjust_timer(-60))
        self._btn_inc.clicked.connect(lambda: self._adjust_timer(60))

        adjust_layout.addWidget(self._btn_dec)
        adjust_layout.addWidget(self._btn_inc)
        right_col.addLayout(adjust_layout)
        right_col.addStretch()

        layout.addLayout(right_col, stretch=2)

        # Draw custom progress line (we overwrite paintEvent of timer_view)
        self._timer_view.paintEvent = self._paint_timer_progress

    def _init_sw_view(self):
        layout = QVBoxLayout(self._sw_view)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        self._lbl_sw_time = QLabel("00:00.00", self._sw_view)
        self._lbl_sw_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_sw_time, stretch=1)

        # Buttons
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_sw_start = QPushButton("Start", self._sw_view)
        self._btn_sw_reset = QPushButton("Reset", self._sw_view)
        
        self._btn_sw_start.clicked.connect(self._toggle_sw)
        self._btn_sw_reset.clicked.connect(self._reset_sw)
        
        self._btn_sw_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_sw_reset.setCursor(Qt.CursorShape.PointingHandCursor)

        ctrl_layout.addWidget(self._btn_sw_start)
        ctrl_layout.addWidget(self._btn_sw_reset)
        layout.addLayout(ctrl_layout)

    def _paint_timer_progress(self, _event):
        p = QPainter(self._timer_view)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate progress ratio
        if self._timer_duration > 0:
            ratio = self._timer_remaining / self._timer_duration
        else:
            ratio = 0.0
            
        ratio = max(0.0, min(ratio, 1.0))

        # Bottom thin progress line
        w = self._timer_view.width()
        y = self._timer_view.height() - 4
        bar_w = w
        
        p.setPen(Qt.PenStyle.NoPen)
        
        # Background track
        p.setBrush(QColor(*S.ACCENT_WHITE, 20))
        p.drawRoundedRect(QRectF(0, y, bar_w, 2), 1, 1)

        # Foreground filled progress
        fill_w = bar_w * ratio
        
        # Alarm flashing visual color
        if self._timer_alarm_active and self._alarm_flash_state:
            p.setBrush(QColor(255, 59, 48, 230))
        else:
            p.setBrush(QColor(*S.ACCENT_WHITE, 230))
            
        p.drawRoundedRect(QRectF(0, y, fill_w, 2), 1, 1)
        p.end()

    def _set_timer_duration(self, seconds: int):
        if self._timer_running:
            self._toggle_timer()
        self._timer_duration = float(seconds)
        self._timer_remaining = float(seconds)
        self._update_timer_label()
        self._dismiss_alarm()
        self._timer_view.update()

    def _adjust_timer(self, seconds: int):
        if self._timer_alarm_active:
            self._dismiss_alarm()
        new_rem = max(10.0, self._timer_remaining + seconds)
        if self._timer_running:
            self._timer_target_time += (new_rem - self._timer_remaining)
        self._timer_remaining = new_rem
        if not self._timer_running:
            self._timer_duration = new_rem
        self._update_timer_label()
        self._timer_view.update()

    def _toggle_timer(self):
        if self._timer_alarm_active:
            self._dismiss_alarm()
            return
            
        if self._timer_running:
            # Pause
            self._timer_remaining = self._timer_target_time - time.perf_counter()
            self._timer_running = False
            self._btn_timer_start.setText("Start")
        else:
            # Start
            if self._timer_remaining <= 0:
                self._timer_remaining = self._timer_duration
            self._timer_target_time = time.perf_counter() + self._timer_remaining
            self._timer_running = True
            self._btn_timer_start.setText("Pause")
        self._timer_view.update()

    def _reset_timer(self):
        self._timer_running = False
        self._timer_remaining = self._timer_duration
        self._btn_timer_start.setText("Start")
        self._dismiss_alarm()
        self._update_timer_label()
        self._timer_view.update()

    def _dismiss_alarm(self):
        self._timer_alarm_active = False
        self._alarm_timer.stop()
        self._btn_timer_dismiss.hide()
        self._timer_ctrl_row.show()
        self._update_timer_label()
        self._timer_view.update()

    def _update_timer_label(self):
        total_sec = max(0, int(round(self._timer_remaining)))
        mins = total_sec // 60
        secs = total_sec % 60
        self._lbl_timer_time.setText(f"{mins:02d}:{secs:02d}")

    def _toggle_sw(self):
        if self._sw_running:
            # Pause
            self._sw_elapsed = time.perf_counter() - self._sw_start_time
            self._sw_running = False
            self._btn_sw_start.setText("Start")
        else:
            # Start
            self._sw_start_time = time.perf_counter() - self._sw_elapsed
            self._sw_running = True
            self._btn_sw_start.setText("Pause")

    def _reset_sw(self):
        self._sw_running = False
        self._sw_elapsed = 0.0
        self._btn_sw_start.setText("Start")
        self._lbl_sw_time.setText("00:00.00")

    def _on_tick(self):
        # 1. Update Stopwatch
        if self._sw_running:
            elapsed = time.perf_counter() - self._sw_start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            centis = int((elapsed * 100) % 100)
            self._lbl_sw_time.setText(f"{mins:02d}:{secs:02d}.{centis:02d}")
            
        # 2. Update countdown Timer
        if self._timer_running:
            rem = self._timer_target_time - time.perf_counter()
            if rem <= 0.05:
                # Timer expired!
                self._timer_remaining = 0.0
                self._timer_running = False
                self._btn_timer_start.setText("Start")
                self._trigger_alarm()
            else:
                self._timer_remaining = rem
            self._update_timer_label()
            self._timer_view.update()

    def _trigger_alarm(self):
        self._timer_alarm_active = True
        self._alarm_flash_state = True
        self._timer_ctrl_row.hide()
        self._btn_timer_dismiss.show()
        
        # Start alarm visual flash
        self._alarm_timer.start()
        
        # Trigger native Windows Beep in a non-blocking background way
        try:
            # SystemDefault beep
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

    def _on_alarm_flash(self):
        # Toggle flash state and repaint
        self._alarm_flash_state = not self._alarm_flash_state
        self._timer_view.update()
        
        # Keep playing soft beeps while alarm is flashing
        if self._timer_alarm_active and self._alarm_flash_state:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass
