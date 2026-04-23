"""30-day habit heatmap rendered as a 10-column grid."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor
import theme as T


class HabitCalendar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # list of healthPct(0-100)
        self.setMinimumHeight(70)

    def setData(self, data):
        self._data = list(data)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        data = self._data
        if not data:
            return
        cols = 10
        rows = (len(data) + cols - 1) // cols
        W = self.width()
        gap = 4
        cell = (W - gap * (cols - 1)) / cols

        for i, hp in enumerate(data):
            r = i // cols
            c = i % cols
            x = c * (cell + gap)
            y = r * (cell + gap)
            if hp >= 80:
                col = QColor(T.BRAND); col.setAlphaF(0.80)
            elif hp >= 60:
                col = QColor(T.BRAND); col.setAlphaF(0.40)
            elif hp >= 40:
                col = QColor(T.WARN); col.setAlphaF(0.55)
            else:
                col = QColor(T.DANGER); col.setAlphaF(0.55)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(QRectF(x, y, cell, cell), 3, 3)
