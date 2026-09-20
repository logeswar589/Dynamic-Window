"""
island.py – The main Dynamic Island window.

A frameless, translucent, always-on-top pill that:
  • Sits centred at the top of the primary screen.
  • Custom-paints a macOS-style dark capsule with rounded corners.
  • Smoothly morphs (width, height) via QPropertyAnimation.
  • Expands on hover, collapses on mouse-leave after a delay.
  • Slides off-screen when an app is focused, and stays visible on the Desktop.
  • Drops down with an elastic bounce animation when the cursor hits the top-left corner
    or near the top-center edge (e.g. during a drag-and-drop).
  • Auto-switches to the File Tray mode and stays open during active drags over the island.
  • Supports sticky manual modes (doesn't collapse chosen widget when mouse leaves).
  • Quits immediately on double right-click.
"""

import ctypes
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QRectF, Property, Signal, Slot,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QRegion, QCursor, QDragEnterEvent, QDragMoveEvent, QDragLeaveEvent, QDropEvent
)
from PySide6.QtWidgets import QWidget, QStackedLayout, QApplication

import styles as S
from widgets.idle import IdleWidget
from widgets.sysmon import SysMonWidget
from widgets.media import MediaWidget
from widgets.filetray import FileTrayWidget
from widgets.settings import SettingsWidget
from widgets.reminder import ReminderWidget
from widgets.timer import TimerStopwatchWidget


def get_foreground_window_class() -> str:
    """Fetch the Win32 class name of the current foreground window."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ""
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


class DynamicIsland(QWidget):
    """Top-level island window."""

    toggle_requested = Signal()

    def _get_island_w(self): return self._island_w
    def _set_island_w(self, v):
        self._island_w = int(v)
        self._reposition()
    island_w = Property(int, _get_island_w, _set_island_w)

    def _get_island_h(self): return self._island_h
    def _set_island_h(self, v):
        self._island_h = int(v)
        self._reposition()
    island_h = Property(int, _get_island_h, _set_island_h)

    def _get_y_slide(self): return self._y_slide
    def _set_y_slide(self, v):
        self._y_slide = int(v)
        self._reposition()
    y_slide = Property(int, _get_y_slide, _set_y_slide)

    def __init__(self, parent=None):
        super().__init__(parent)


        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._island_w = S.ISLAND_IDLE_W
        self._island_h = S.ISLAND_IDLE_H
        self._y_slide = 10
        self._hovered = False
        self._dragging_over = False
        self._current_mode = 0
        self._media_active = False
        self._on_desktop = True
        self._forced_visible = False
        self._manual_mode = False
        self._menu_active = False


        self._container = QWidget(self)
        self._container.setMouseTracking(True)

        self._stack = QStackedLayout(self._container)
        self._stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._idle     = IdleWidget(self._container)
        self._media    = MediaWidget(self._container)
        self._sysmon   = SysMonWidget(self._container)
        self._reminder = ReminderWidget(self._container)
        self._timer    = TimerStopwatchWidget(self._container)
        self._ftray    = FileTrayWidget(self._container)
        self._settings = SettingsWidget(self._container)


        self._stack.addWidget(self._idle)
        self._stack.addWidget(self._media)
        self._stack.addWidget(self._sysmon)
        self._stack.addWidget(self._reminder)
        self._stack.addWidget(self._timer)
        self._stack.addWidget(self._ftray)
        self._stack.addWidget(self._settings)

        self._widgets = [
            self._idle, self._media, self._sysmon,
            self._reminder, self._timer, self._ftray, self._settings
        ]


        for w in self._widgets:
            w.deactivate()
        self._idle.activate()
        self._stack.setCurrentIndex(0)


        self._anim_w = QPropertyAnimation(self, b"island_w", self)
        self._anim_w.setDuration(S.ANIM_DURATION_MS)
        self._anim_w.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_h = QPropertyAnimation(self, b"island_h", self)
        self._anim_h.setDuration(S.ANIM_DURATION_MS)
        self._anim_h.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_slide = QPropertyAnimation(self, b"y_slide", self)


        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(S.COLLAPSE_DELAY)
        self._collapse_timer.timeout.connect(self._collapse)


        self._hover_music_timer = QTimer(self)
        self._hover_music_timer.setSingleShot(True)
        self._hover_music_timer.setInterval(S.HOVER_MUSIC_DELAY)
        self._hover_music_timer.timeout.connect(self._on_hover_music_timeout)


        self._desktop_timer = QTimer(self)
        self._desktop_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._desktop_timer.setInterval(S.DESKTOP_POLL_MS)
        self._desktop_timer.timeout.connect(self._check_desktop)

        self._forced_visible = True
        QTimer.singleShot(3000, self._end_startup_grace)

        self._hotcorner_timer = QTimer(self)
        self._hotcorner_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._hotcorner_timer.setInterval(S.HOTCORNER_POLL_MS)
        self._hotcorner_timer.timeout.connect(self._check_hot_corner)
        self._hotcorner_timer.start()

        self._expanded_mode_index = 0  # which expanded mode to show next
        self._last_non_tray_expanded_mode_index = 0


        self._settings.theme_changed.connect(self._change_theme)
        self._settings.glassy_changed.connect(self._change_glassy)


        self._reposition()


    def _screen_center_x(self) -> int:
        screen = QApplication.primaryScreen()
        if screen:
            return screen.geometry().center().x()
        return 960

    def _reposition(self):
        """Keep centred horizontally, pinned to top / slide position."""
        cx = self._screen_center_x()
        x = cx - self._island_w // 2
        y = self._y_slide
        pad = S.PAD

        self.setFixedSize(self._island_w + pad * 2, self._island_h + pad * 2)
        self.move(x - pad, y - pad)


        self._container.setGeometry(pad, pad, self._island_w, self._island_h)


        path = QPainterPath()
        path.addRoundedRect(
            QRectF(pad, pad, self._island_w, self._island_h),
            S.CORNER_RADIUS, S.CORNER_RADIUS,
        )
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        self.update()

    def _morph_to(self, w: int, h: int):
        """Animate island size."""
        for anim in (self._anim_w, self._anim_h):
            anim.stop()

        self._anim_w.setStartValue(self._island_w)
        self._anim_w.setEndValue(w)
        self._anim_h.setStartValue(self._island_h)
        self._anim_h.setEndValue(h)

        self._anim_w.start()
        self._anim_h.start()


    def _check_desktop(self):
        if not self.isVisible():
            return
        
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                is_desktop = True
            else:

                if hwnd == self.winId().__int__():
                    return
                    
                buf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
                name = buf.value
                if not name:
                    return
                    

                if name == "#32768":
                    return
                    

                is_desktop = name in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd")
            
            if is_desktop != self._on_desktop:
                self._on_desktop = is_desktop
                self._update_visibility()
        except Exception:
            pass

    def _check_hot_corner(self):
        if not self.isVisible():
            return
        pos = QCursor.pos()
        cx = self._screen_center_x()
        

        in_top_left = pos.x() < S.HOTCORNER_SIZE and pos.y() < S.HOTCORNER_SIZE
        

        in_top_center = pos.y() < 10 and abs(pos.x() - cx) < 120
        
        if in_top_left or in_top_center:
            if not self._forced_visible:
                self._forced_visible = True
                self._update_visibility()
                self._collapse_timer.start()

    def _set_menu_active(self, active: bool):
        """Called by child widgets when a context menu opens/closes."""
        self._menu_active = active
        if not active:
            self._update_visibility()

    def _end_startup_grace(self):
        """Called 3s after launch — start normal desktop tracking."""
        self._forced_visible = False
        self._desktop_timer.start()
        self._update_visibility()

    def _update_visibility(self):
        should_be_visible = (
            self._on_desktop 
            or self._forced_visible 
            or self._hovered 
            or self._dragging_over
            or self._menu_active
        )
        if should_be_visible:
            self._slide_down()
        else:
            self._slide_up()

    def _slide_down(self):
        self._anim_slide.stop()
        self._anim_slide.setStartValue(self._y_slide)
        self._anim_slide.setEndValue(10)
        self._anim_slide.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim_slide.setDuration(S.SLIDE_DURATION)
        self._anim_slide.start()

    def _slide_up(self):
        self._anim_slide.stop()
        self._anim_slide.setStartValue(self._y_slide)
        target_hidden = -self._island_h - S.PAD * 2
        self._anim_slide.setEndValue(target_hidden)
        self._anim_slide.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_slide.setDuration(S.SLIDE_DURATION)
        self._anim_slide.start()


    def _switch_mode(self, index: int):
        if index == self._current_mode:
            return
        old = self._widgets[self._current_mode]
        new = self._widgets[index]
        old.deactivate()
        new.activate()
        self._stack.setCurrentIndex(index)
        self._current_mode = index
        w, h = new.preferred_size()
        self._morph_to(w, h)

    def _expand(self):
        """Show the appropriate expanded widget."""
        idx = self._expanded_mode_index
        if idx == 0:
            idx = 1
        if idx in (5, 6):
            idx = self._last_non_tray_expanded_mode_index
        self._switch_mode(idx)

    def _on_hover_music_timeout(self):
        if self._hovered and self._current_mode == 0:
            self._switch_mode(1)

    def _collapse(self):
        """Return to idle pill."""
        if self._hovered or self._dragging_over:
            return

        self._forced_visible = False
        if not self._manual_mode or self._current_mode != 5:
            self._switch_mode(0)
            self._manual_mode = False
            self._expanded_mode_index = 0
            
        self._update_visibility()


    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self._dragging_over = True
            self._collapse_timer.stop()
            self._update_visibility()

            if self._current_mode != 5:
                self._switch_mode(5)
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self._dragging_over = False
        self._collapse_timer.start()
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self._dragging_over = False

        if self._current_mode == 5:
            self._ftray.dropEvent(event)
            self._manual_mode = True
        self._collapse_timer.start()
        event.acceptProposedAction()


    def set_media_active(self, active: bool):
        """Called by media listener – tracks if media is active."""
        self._media_active = active

    def toggle_island(self):
        """Invoked via Tray / Hotkey."""
        if self.isVisible() and self._y_slide > 0:
            self._forced_visible = False
            self._on_desktop = False
            self._update_visibility()
        else:
            self.show()
            self._forced_visible = True
            self._update_visibility()
            self._collapse_timer.start()


    def enterEvent(self, event):
        self._hovered = True
        self._collapse_timer.stop()
        if self._current_mode == 0:
            self._hover_music_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._hover_music_timer.stop()
        self._collapse_timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._hover_music_timer.stop()

            next_idx = (self._current_mode + 1) % len(self._widgets)
            self._switch_mode(next_idx)
            

            if next_idx == 0:
                self._manual_mode = False
                self._expanded_mode_index = 0
            else:
                self._manual_mode = True
                self._expanded_mode_index = next_idx
                if next_idx not in (5, 6):
                    self._last_non_tray_expanded_mode_index = next_idx
                
            self._collapse_timer.stop()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            QApplication.quit()
        elif event.button() == Qt.MouseButton.LeftButton and self._current_mode == 0:
            self._hover_music_timer.stop()
            self._expand()
        super().mouseDoubleClickEvent(event)

    def _change_theme(self, theme_name: str):
        S.set_theme(theme_name)
        for w in self._widgets:
            w.refresh_style()
        self.update()

    def _change_glassy(self, enabled: bool):
        S.set_glassy(enabled)
        self.update()


    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        pad = S.PAD
        rect = QRectF(pad, pad, self._island_w, self._island_h)
        radius = S.CORNER_RADIUS


        p.setPen(Qt.PenStyle.NoPen)
        for i in range(6):
            alpha = 24 - i * 4
            if alpha <= 0:
                break
            p.setBrush(QColor(0, 0, 0, alpha))
            expanded = rect.adjusted(-i - 1, -i - 1, i + 1, i + 1)
            p.drawRoundedRect(expanded, radius + i, radius + i)


        bg = QPainterPath()
        bg.addRoundedRect(rect, radius, radius)

        if S.GLASSY_UI:

            from PySide6.QtGui import QLinearGradient
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            if S.CURRENT_THEME == "black":
                base_color = S.BG_HOVER if self._hovered else S.BG_PRIMARY
                grad.setColorAt(0.0, QColor(base_color[0] + 15, base_color[1] + 15, base_color[2] + 15, 130))
                grad.setColorAt(1.0, QColor(base_color[0], base_color[1], base_color[2], 160))
            else:
                base_color = S.BG_HOVER if self._hovered else S.BG_PRIMARY
                grad.setColorAt(0.0, QColor(255, 255, 255, 170))
                grad.setColorAt(1.0, QColor(base_color[0] - 5, base_color[1] - 5, base_color[2], 120))
            
            p.fillPath(bg, grad)

            highlight_pen = QPen(QColor(255, 255, 255, 60) if S.CURRENT_THEME == "black" else QColor(255, 255, 255, 180), 0.8)
            p.setPen(highlight_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius - 1, radius - 1)
        else:
            r, g, b, a = S.BG_HOVER if self._hovered else S.BG_PRIMARY
            p.fillPath(bg, QColor(r, g, b, a))


        if S.GLASSY_UI:

            if S.CURRENT_THEME == "black":
                border_pen = QPen(QColor(255, 255, 255, 45), 1.0)
            else:
                border_pen = QPen(QColor(0, 0, 0, 25), 1.0)
        else:
            border_pen = QPen(QColor(*S.BORDER_COLOR), 1.0)
            
        p.setPen(border_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        p.end()
