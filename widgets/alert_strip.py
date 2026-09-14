"""Compact reminder surface, hosted in a permanent sidebar slot."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QPainter
import theme as T
import config
from widgets.status_light import StatusLight


class _ReminderSurface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fill = QColor(T.C_CARD)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.fill)
        painter.drawRoundedRect(QRectF(self.rect()), 14, 14)


class AlertStrip(QWidget):
    """Visibility changes only the card; its sidebar host always keeps its size."""
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = -1
        self._secs = 0.0
        self.setFixedHeight(144)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._surface = _ReminderSurface(self)
        outer.addWidget(self._surface)
        column = QVBoxLayout(self._surface)
        column.setContentsMargins(12, 12, 12, 12)
        column.setSpacing(8)
        heading = QHBoxLayout()
        heading.setSpacing(5)
        self._dot = StatusLight(size=18)
        self._label = QLabel()
        self._label.setFont(T.ui_font(13, 600))
        self._label.setFixedHeight(24)
        heading.addWidget(self._dot)
        heading.addWidget(self._label, 1)
        column.addLayout(heading)
        self._desc = QLabel()
        self._desc.setFont(T.ui_font(13))
        self._desc.setWordWrap(True)
        self._desc.setFixedHeight(36)
        self._desc.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        column.addWidget(self._desc)
        footer = QHBoxLayout()
        footer.setSpacing(6)
        self._secs_lbl = QLabel()
        self._secs_lbl.setFont(T.ui_font(16, 500))
        self._secs_lbl.setFixedSize(68, 30)
        footer.addWidget(self._secs_lbl)
        footer.addStretch(1)
        self._btn = QPushButton()
        self._btn.setFont(T.ui_font(12, 500))
        self._btn.setFixedSize(70, 30)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.clicked.connect(self.dismissed)
        footer.addWidget(self._btn)
        column.addLayout(footer)
        self.hide()

    def setState(self, level, secs):
        self._level, self._secs = min(2, int(level)), max(0., float(secs))
        if level < 0:
            self.hide()
            return
        self.retranslate()
        self._dot.setState(f'alert_{self._level}')
        ink = ['#8C6417', '#9C4C1E', '#A63E30'][self._level]
        self._surface.fill = QColor(['#F8F0DC', '#F9ECDC', '#F8E6DF'][self._level])
        self._surface.update()
        for label in (self._label, self._secs_lbl):
            label.setStyleSheet(f'color:{ink};background:transparent;border:none;')
        self._desc.setStyleSheet(f'color:{T.C_TEXT2};background:transparent;border:none;')
        self._btn.setStyleSheet(
            f'QPushButton{{background:{T.C_CARD};color:{ink};border:1px solid transparent;border-radius:8px;padding:0;}}'
            f'QPushButton:hover{{background:{T.C_BG};}}'
            f'QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}')
        self._secs_lbl.setText(f'{self._secs:.1f}s')
        self.show()

    def retranslate(self):
        if self._level < 0:
            return
        self._label.setText(T.alert_levels()[self._level]['label'])
        self._desc.setText('轻轻、完整地眨一下眼。' if config.LANGUAGE == 'zh' else 'Blink gently and fully.')
        self._btn.setText('收起' if config.LANGUAGE == 'zh' else 'Dismiss')
        self.setAccessibleName('眨眼提醒' if config.LANGUAGE == 'zh' else 'Blink reminder')
        self._secs_lbl.setAccessibleName('距上次眨眼' if config.LANGUAGE == 'zh' else 'Time since last blink')
