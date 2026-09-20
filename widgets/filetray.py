"""
widgets/filetray.py – Drag-and-Drop File Tray widget.
Files dragged from Explorer are cached here for quick access.
"""

import os
from PySide6.QtCore import Qt, QMimeData, QUrl, QRectF
from PySide6.QtGui import QFont, QPainter, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget,
)

import styles as S
from widgets.base import IslandWidget


class _FileChip(QWidget):
    """Single file entry chip."""

    def __init__(self, path: str, on_remove, parent=None):
        super().__init__(parent)
        self._path = path
        self.setFixedHeight(28)
        
        # Enable stylesheet rendering on custom QWidget and hover feedback
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(6)

        icon = QLabel("📄")
        icon.setFont(QFont("Segoe UI Emoji", 11))
        icon.setStyleSheet("background: transparent;")
        layout.addWidget(icon)

        name = QLabel(os.path.basename(path))
        font = QFont(S.FONT_FAMILY, S.FONT_SIZE_SM)
        name.setFont(font)
        r, g, b, a = S.TEXT_PRIMARY
        name.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        name.setMaximumWidth(200)
        layout.addWidget(name, stretch=1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                color: rgba(255,255,255,140);
                background: transparent;
                border: none;
                font-size: 10px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,40);
                color: white;
            }
        """)
        close_btn.clicked.connect(lambda: on_remove(self._path))
        layout.addWidget(close_btn)

        self.setStyleSheet("""
            _FileChip {
                background: rgba(255,255,255,10);
                border-radius: 6px;
            }
            _FileChip:hover {
                background: rgba(255,255,255,22);
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                os.startfile(self._path)
            except Exception:
                pass
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def _show_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        top_window = self.window()
        if hasattr(top_window, '_set_menu_active'):
            top_window._set_menu_active(True)

        menu = QMenu(self)
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

        act_open = QAction("Open", menu)
        act_open.triggered.connect(lambda: os.startfile(self._path))
        menu.addAction(act_open)

        act_reveal = QAction("Reveal in Explorer", menu)
        act_reveal.triggered.connect(self._reveal_in_explorer)
        menu.addAction(act_reveal)

        act_copy_path = QAction("Copy Path", menu)
        act_copy_path.triggered.connect(self._copy_path_to_clipboard)
        menu.addAction(act_copy_path)

        menu.exec(pos)

        if hasattr(top_window, '_set_menu_active'):
            top_window._set_menu_active(False)

    def _reveal_in_explorer(self):
        try:
            import subprocess
            subprocess.run(["explorer", "/select,", os.path.abspath(self._path)])
        except Exception:
            pass

    def _copy_path_to_clipboard(self):
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(os.path.abspath(self._path))


class FileTrayWidget(IslandWidget):
    """Drop-zone for files with a scrollable list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._files: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        self._title = QLabel("File Tray")
        font = QFont(S.FONT_FAMILY.split(",")[0].strip(), S.FONT_SIZE_MD)
        font.setWeight(QFont.Weight(S.FONT_WEIGHT_BOLD))
        self._title.setFont(font)
        r, g, b, a = S.TEXT_PRIMARY
        self._title.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        header.addWidget(self._title)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._clear)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)
        self._apply_btn_style()

        # Scroll area for chips
        self._scroll_content = QWidget()
        self._chip_layout = QVBoxLayout(self._scroll_content)
        self._chip_layout.setContentsMargins(0, 0, 0, 0)
        self._chip_layout.setSpacing(4)
        self._chip_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._scroll_content)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,30); border-radius: 2px;
            }
        """)
        layout.addWidget(scroll)

        # Drop hint
        self._hint = QLabel("Drop files here")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_font = QFont(S.FONT_FAMILY.split(",")[0].strip(), S.FONT_SIZE_SM)
        self._hint.setFont(hint_font)
        r2, g2, b2, a2 = S.TEXT_DIM
        self._hint.setStyleSheet(f"color: rgba({r2},{g2},{b2},{a2}); background: transparent;")
        self._chip_layout.insertWidget(0, self._hint)

    def preferred_size(self) -> tuple[int, int]:
        return S.ISLAND_EXPAND_W, S.ISLAND_EXPAND_H

    def refresh_style(self):
        r, g, b, a = S.TEXT_PRIMARY
        self._title.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent;")
        r2, g2, b2, a2 = S.TEXT_DIM
        self._hint.setStyleSheet(f"color: rgba({r2},{g2},{b2},{a2}); background: transparent;")
        self._apply_btn_style()

    def _apply_btn_style(self):
        r, g, b, _ = S.TEXT_PRIMARY
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                color: rgba({r},{g},{b},160);
                background: transparent;
                border: none;
                font-size: {S.FONT_SIZE_SM}px;
            }}
            QPushButton:hover {{
                color: rgba({r},{g},{b},255);
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and path not in self._files:
                self._files.append(path)
                self._add_chip(path)
        self._hint.setVisible(len(self._files) == 0)
        event.acceptProposedAction()

    def _add_chip(self, path: str):
        chip = _FileChip(path, self._remove, self._scroll_content)
        # Insert before the stretch
        self._chip_layout.insertWidget(self._chip_layout.count() - 1, chip)

    def _remove(self, path: str):
        if path in self._files:
            self._files.remove(path)
        # Rebuild chips
        self._rebuild()

    def _clear(self):
        self._files.clear()
        self._rebuild()

    def _rebuild(self):
        # Remove all chips except hint and stretch
        while self._chip_layout.count() > 2:
            item = self._chip_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        for f in self._files:
            self._add_chip(f)
        self._hint.setVisible(len(self._files) == 0)
