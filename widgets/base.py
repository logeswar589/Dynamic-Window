"""
widgets/base.py – Abstract base for island sub-widgets.
Each widget knows how to paint itself inside a given rect and
report its preferred expanded size.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal


class IslandWidget(QWidget):
    """Base class every island mode inherits from."""

    # Emitted when this widget wants the island to re-morph to its size.
    request_resize = Signal(int, int)   # (width, height)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)

    def preferred_size(self) -> tuple[int, int]:
        """Return (w, h) the widget wants when expanded."""
        raise NotImplementedError

    def activate(self):
        """Called when the island switches TO this widget."""
        self.show()

    def deactivate(self):
        """Called when the island switches AWAY from this widget."""
        self.hide()

    def refresh_style(self):
        """Called when theme changes – subclasses re-apply stylesheets."""
        pass
