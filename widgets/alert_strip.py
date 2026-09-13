"""An inset reminder card, aligned with the page surfaces above it."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter
import theme as T
from i18n import t
import config


def _dismiss_text():
    return '收起提示' if config.LANGUAGE == 'zh' else 'Dismiss'


class _ReminderSurface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fill = QColor(T.C_CARD)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.fill)
        painter.drawRoundedRect(QRectF(self.rect()), T.R_CARD, T.R_CARD)


class AlertStrip(QWidget):
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = -1
        self._secs = 0.0
        self.setFixedHeight(60)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 0, 24, 12)
        self._surface = _ReminderSurface(self)
        outer.addWidget(self._surface)
        row = QHBoxLayout(self._surface)
        row.setContentsMargins(16, 0, 12, 0)
        row.setSpacing(12)
        self._dot = QLabel('●')
        self._dot.setFixedSize(12, 24)
        self._label = QLabel()
        self._label.setFont(T.ui_font(13, 600))
        self._label.setFixedSize(100, 24)
        self._desc = QLabel()
        self._desc.setFont(T.ui_font(13))
        self._desc.setFixedHeight(24)
        self._secs_lbl = QLabel()
        self._secs_lbl.setFont(T.ui_font(14, 500))
        self._secs_lbl.setFixedSize(64, 24)
        self._secs_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._btn = QPushButton(_dismiss_text())
        self._btn.setFont(T.ui_font(13, 500))
        self._btn.setFixedSize(84, 32)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.clicked.connect(self.dismissed)
        row.addWidget(self._dot)
        row.addWidget(self._label)
        row.addWidget(self._desc, 1)
        row.addWidget(self._secs_lbl)
        row.addWidget(self._btn)
        self._pulse = QTimer(self)
        self._pulse.timeout.connect(self._toggle_dot)
        self._dot_on = True
        self.hide()

    def _toggle_dot(self):
        self._dot_on = not self._dot_on
        ink = QColor(self._ink)
        ink.setAlpha(230 if self._dot_on else 120)
        self._dot.setStyleSheet(f'color:{ink.name(QColor.NameFormat.HexArgb)};background:transparent;border:none;font-size:11px;')

    def setState(self, level, secs):
        self._level, self._secs = level, secs
        if level < 0:
            self.hide()
            self._pulse.stop()
            return
        level = min(2, int(level))
        info = T.alert_levels()[level]
        self._ink = ['#8C6417', '#9C4C1E', '#A63E30', '#A12C2C'][level]
        self._surface.fill = QColor(['#F8F0DC', '#F9ECDC', '#F8E6DF', '#F6E1DF'][level])
        self._surface.update()
        for label in (self._label, self._secs_lbl):
            label.setStyleSheet(f'color:{self._ink};background:transparent;border:none;')
        self._desc.setStyleSheet(f'color:{T.C_TEXT2};background:transparent;border:none;')
        self._btn.setStyleSheet(
            f'QPushButton{{background:{T.C_CARD};color:{self._ink};border:1px solid transparent;border-radius:8px;padding:4px 8px;}}'
            f'QPushButton:hover{{background:{T.C_BG};}}'
            f'QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}')
        self._label.setText(info['label'])
        threshold = int(config.NO_BLINK_ALERT_SEC + level * config.ALERT_INTERVAL_SEC)
        self._desc.setText(t('alert_desc', sec=threshold).lstrip(' ·'))
        self._btn.setText(_dismiss_text())
        self._secs_lbl.setText(f'{secs:.1f}s')
        self.show()
        if level >= 3:
            if not self._pulse.isActive():
                self._pulse.start(500)
        else:
            self._pulse.stop()
            self._dot.setStyleSheet(f'color:{self._ink};font-size:11px;background:transparent;border:none;')
