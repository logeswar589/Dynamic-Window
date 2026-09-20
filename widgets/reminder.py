"""
widgets/reminder.py – Persistent Reminders slide.
Shows a scrollable list of reminders with a clean check-off fade animation,
and a text input at the bottom to add new ones.
"""

import os
import json
from PySide6.QtCore import Qt, QSize, Signal, Slot, QPropertyAnimation
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QGraphicsOpacityEffect, QFrame,
)

import styles as S
from widgets.base import IslandWidget


class RoundCheckButton(QPushButton):
    """Custom premium round checkbox with hover and toggle visuals."""
    clicked_checked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False
        self._hovered = False

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            # Emit signal after brief delay so user can see it's checked
            self.clicked_checked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw circle border
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # Color based on state and theme
        is_light = S.CURRENT_THEME == "white"
        border_color = QColor(0, 0, 0, 160) if is_light else QColor(255, 255, 255, 160)
        hover_bg = QColor(0, 0, 0, 30) if is_light else QColor(255, 255, 255, 30)
        
        if self._checked:
            # Filled circle with checkmark dot
            accent_color = QColor(*S.ACCENT_WHITE)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent_color)
            p.drawEllipse(rect)
            
            # Inner white/black dot
            p.setBrush(QColor(255, 255, 255) if is_light else QColor(10, 10, 10))
            p.drawEllipse(self.rect().center(), 3, 3)
        else:
            # Border only
            p.setPen(QPen(border_color, 1.5))
            if self._hovered:
                p.setBrush(hover_bg)
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rect)

        p.end()


class ReminderItemRow(QFrame):
    """A single reminder row item that supports fading out upon completion."""
    completed = Signal(str)  # Emitted with task text when animation finishes

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = text
        
        self.setFixedHeight(30)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(10)

        # Check button
        self.check_btn = RoundCheckButton(self)
        self.check_btn.clicked_checked.connect(self._complete)
        layout.addWidget(self.check_btn)

        # Task label
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        font = QFont(S.FONT_FAMILY, S.FONT_SIZE_SM)
        self.label.setFont(font)
        self._update_label_style()
        layout.addWidget(self.label, stretch=1)

        # Opacity effect for fade out
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._anim = None

    def _update_label_style(self):
        r, g, b, a = S.TEXT_PRIMARY
        self.label.setStyleSheet(f"color: rgba({r},{g},{b},{a}); background: transparent; border: none;")

    def _complete(self):
        # Prevent double click issues
        self.check_btn.setEnabled(False)
        
        # Start smooth fade out
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(lambda: self.completed.emit(self.text))
        self._anim.start()


class ReminderWidget(IslandWidget):
    """Slide featuring scrollable reminders and quick add input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "reminders.json"
        )
        self._reminders = self._load_reminders()

        # Layout
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(14, 10, 14, 10)
        self._root_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._title_label = QLabel("Reminders")
        font_title = QFont(S.FONT_FAMILY, S.FONT_SIZE_MD)
        font_title.setWeight(QFont.Weight(S.FONT_WEIGHT_BOLD))
        self._title_label.setFont(font_title)
        
        self._count_label = QLabel("")
        font_count = QFont(S.FONT_FAMILY, S.FONT_SIZE_SM)
        self._count_label.setFont(font_count)
        
        header_row.addWidget(self._title_label)
        header_row.addWidget(self._count_label)
        header_row.addStretch()
        self._root_layout.addLayout(header_row)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 40);
                border-radius: 2px;
                min-height: 15px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 80);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
        """)

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent; border: none;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(1)
        self._list_layout.addStretch()  # Keep items pushed to top
        
        self._scroll.setWidget(self._list_container)
        self._root_layout.addWidget(self._scroll, stretch=1)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Add reminder...")
        font_input = QFont(S.FONT_FAMILY, S.FONT_SIZE_SM)
        self._input.setFont(font_input)
        self._input.returnPressed.connect(self._add_reminder)
        
        self._add_btn = QPushButton("+", self)
        self._add_btn.setFixedSize(24, 24)
        self._add_btn.setFont(QFont(S.FONT_FAMILY, S.FONT_SIZE_MD, QFont.Weight.Bold))
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._add_reminder)

        input_row.addWidget(self._input, stretch=1)
        input_row.addWidget(self._add_btn)
        self._root_layout.addLayout(input_row)

        self.refresh_style()
        self._populate_list()

    def preferred_size(self) -> tuple[int, int]:
        return S.ISLAND_EXPAND_W, S.ISLAND_EXPAND_H

    def activate(self):
        super().activate()
        self._input.setFocus()

    def refresh_style(self):
        is_light = S.CURRENT_THEME == "white"
        
        # Color definitions
        r_pri, g_pri, b_pri, a_pri = S.TEXT_PRIMARY
        r_sec, g_sec, b_sec, a_sec = S.TEXT_SECONDARY
        
        # Title and Count styling
        self._title_label.setStyleSheet(f"color: rgba({r_pri},{g_pri},{b_pri},{a_pri}); background: transparent; border: none;")
        self._count_label.setStyleSheet(f"color: rgba({r_sec},{g_sec},{b_sec},{a_sec}); background: transparent; border: none;")

        # Scrollbar theme adjustments
        scroll_handle_color = "rgba(0, 0, 0, 50)" if is_light else "rgba(255, 255, 255, 40)"
        scroll_hover_color = "rgba(0, 0, 0, 90)" if is_light else "rgba(255, 255, 255, 80)"
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle_color};
                border-radius: 2px;
                min-height: 15px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hover_color};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
                height: 0px;
            }}
        """)

        # Input styling
        bg_input = "rgba(0, 0, 0, 15)" if is_light else "rgba(255, 255, 255, 12)"
        border_color = "rgba(0, 0, 0, 30)" if is_light else "rgba(255, 255, 255, 25)"
        text_color = f"rgba({r_pri},{g_pri},{b_pri},{a_pri})"
        placeholder_color = "rgba(0, 0, 0, 100)" if is_light else "rgba(255, 255, 255, 100)"
        
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {bg_input};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 3px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid rgba({r_pri},{g_pri},{b_pri}, 120);
            }}
        """)
        
        # Add button styling
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg_input};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(0, 0, 0, 30) if is_light else rgba(255, 255, 255, 25);
            }}
            QPushButton:pressed {{
                background: rgba(0, 0, 0, 50) if is_light else rgba(255, 255, 255, 45);
            }}
        """)

        # Refresh existing rows
        for i in range(self._list_layout.count()):
            item = self._list_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ReminderItemRow):
                item.widget()._update_label_style()
                item.widget().check_btn.update()

        self._update_count()

    def _load_reminders(self) -> list[str]:
        if os.path.exists(self._db_path):
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return ["Drink water 💧", "Take a posture break 🧘", "Review schedule 📅"]

    def _save_reminders(self):
        try:
            with open(self._db_path, "w", encoding="utf-8") as f:
                json.dump(self._reminders, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _populate_list(self):
        # Clear layout (skip the stretch item at the very bottom)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
                
        for text in self._reminders:
            row = ReminderItemRow(text, self)
            row.completed.connect(self._on_item_completed)
            # Insert before the stretch at the bottom
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)
            
        self._update_count()

    def _update_count(self):
        count = len(self._reminders)
        if count == 0:
            self._count_label.setText("• All done!")
        else:
            self._count_label.setText(f"• {count} active")

    def _add_reminder(self):
        text = self._input.text().strip()
        if not text:
            return
        self._reminders.append(text)
        self._save_reminders()
        
        row = ReminderItemRow(text, self)
        row.completed.connect(self._on_item_completed)
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)
        
        self._input.clear()
        self._update_count()

    @Slot(str)
    def _on_item_completed(self, text: str):
        if text in self._reminders:
            self._reminders.remove(text)
            self._save_reminders()
        
        # Remove widget from layout
        for i in range(self._list_layout.count()):
            item = self._list_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ReminderItemRow):
                if item.widget().text == text:
                    w = item.widget()
                    self._list_layout.removeWidget(w)
                    w.deleteLater()
                    break
        
        self._update_count()
