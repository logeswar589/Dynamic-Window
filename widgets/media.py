"""
widgets/media.py – Media Controls widget.
Displays currently-playing track info and play/pause/prev/next buttons.
Receives data from win_media_listener via signals.
"""

from PySide6.QtCore import Qt, QSize, QRectF, Signal, Slot, QFileInfo
from PySide6.QtGui import (
    QFont, QPainter, QColor, QIcon, QPen, QPainterPath, QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QSizePolicy, QFileIconProvider,
)
import os
import psutil

import styles as S
from widgets.base import IslandWidget

_icon_cache = {}

def _get_app_icon(aumid: str, size: int = 48) -> QPixmap:
    if not aumid:
        return QPixmap()
    if aumid in _icon_cache:
        return _icon_cache[aumid]

    aumid_lower = aumid.lower()
    exe_path = ""
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            pname = proc.info['name']
            if not pname:
                continue
            pname_lower = pname.lower()
            if pname_lower == aumid_lower or pname_lower in aumid_lower or aumid_lower in pname_lower:
                exe = proc.info['exe']
                if exe and os.path.exists(exe):
                    exe_path = exe
                    break
        except Exception:
            pass

    pixmap = QPixmap()
    if exe_path:
        try:
            file_info = QFileInfo(exe_path)
            provider = QFileIconProvider()
            icon = provider.icon(file_info)
            pixmap = icon.pixmap(size, size)
        except Exception:
            pass

    _icon_cache[aumid] = pixmap
    return pixmap


class _IconButton(QPushButton):
    """Minimal flat icon button with hover glow."""

    def __init__(self, icon_char: str, size: int = 28, parent=None):
        super().__init__(parent)
        self._icon_char = icon_char
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,25);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,40);
            }
        """)

    def paintEvent(self, _event):
        super().paintEvent(_event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Segoe UI Symbol", self._size // 2)
        p.setFont(font)
        p.setPen(QColor(*S.TEXT_PRIMARY[:3], 230))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._icon_char)
        p.end()


class MediaWidget(IslandWidget):
    """Now-playing bar with transport controls."""

    # outgoing control signals (island connects these to the media listener)
    play_pause_clicked = Signal()
    prev_clicked = Signal()
    next_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_aumid = ""
        self._app_icon_pixmap = QPixmap()
        self._album_art = QPixmap()

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(12)

        self._art_label = QLabel()
        self._art_label.setFixedSize(48, 48)
        self._art_label.setStyleSheet(
            "background: rgba(255,255,255,12); border-radius: 8px;"
        )
        self._art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Music note fallback
        self._art_label.setText("🎵")
        font_art = QFont("Segoe UI Emoji", 18)
        self._art_label.setFont(font_art)
        root.addWidget(self._art_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setContentsMargins(0, 4, 0, 4)

        self._title_label = QLabel("No media")
        font_title = QFont(S.FONT_FAMILY.split(",")[0].strip(), S.FONT_SIZE_MD)
        font_title.setWeight(QFont.Weight(S.FONT_WEIGHT_BOLD))
        self._title_label.setFont(font_title)
        r, g, b, a = S.TEXT_PRIMARY
        self._title_label.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        self._title_label.setMaximumWidth(160)
        info_col.addWidget(self._title_label)

        self._artist_label = QLabel("")
        font_artist = QFont(S.FONT_FAMILY.split(",")[0].strip(), S.FONT_SIZE_SM)
        self._artist_label.setFont(font_artist)
        r2, g2, b2, a2 = S.TEXT_SECONDARY
        self._artist_label.setStyleSheet(f"color: rgba({r2},{g2},{b2},{a2}); background: transparent;")
        self._artist_label.setMaximumWidth(160)
        info_col.addWidget(self._artist_label)

        root.addLayout(info_col, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_prev = _IconButton("⏮", 28, self)
        self._btn_play = _IconButton("▶", 32, self)
        self._btn_next = _IconButton("⏭", 28, self)

        self._btn_prev.clicked.connect(self.prev_clicked.emit)
        self._btn_play.clicked.connect(self.play_pause_clicked.emit)
        self._btn_next.clicked.connect(self.next_clicked.emit)

        btn_row.addWidget(self._btn_prev)
        btn_row.addWidget(self._btn_play)
        btn_row.addWidget(self._btn_next)
        root.addLayout(btn_row)

    def preferred_size(self) -> tuple[int, int]:
        return S.ISLAND_MEDIA_W, S.ISLAND_MEDIA_H

    def refresh_style(self):
        r, g, b, a = S.TEXT_PRIMARY
        self._title_label.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        r2, g2, b2, a2 = S.TEXT_SECONDARY
        self._artist_label.setStyleSheet(f"color: rgba({r2},{g2},{b2},{a2}); background: transparent;")
        bg_alpha = 12 if S.CURRENT_THEME == "black" else 8
        self._art_label.setStyleSheet(
            f"background: rgba({r},{g},{b},{bg_alpha}); border-radius: 8px;"
        )


    @Slot(str, str, bool, str)
    def update_media(self, title: str, artist: str, is_playing: bool, aumid: str):
        self._title_label.setText(title or "No media")
        self._artist_label.setText(artist or "")
        self._btn_play._icon_char = "⏸" if is_playing else "▶"
        self._btn_play.update()

        if aumid != self._current_aumid:
            self._current_aumid = aumid
            self._app_icon_pixmap = _get_app_icon(aumid, 48)
            # If we don't have album art active, update the display to show the app icon
            if self._album_art.isNull():
                self._draw_placeholder()

    @Slot(QPixmap)
    def update_thumbnail(self, pixmap: QPixmap):
        self._album_art = pixmap
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                48, 48,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._art_label.setPixmap(scaled)
            self._art_label.setText("")
        else:
            self._draw_placeholder()

    def _draw_placeholder(self):
        if self._app_icon_pixmap and not self._app_icon_pixmap.isNull():
            self._art_label.setPixmap(self._app_icon_pixmap)
            self._art_label.setText("")
        else:
            self._art_label.setPixmap(QPixmap())
            self._art_label.setText("🎵")
