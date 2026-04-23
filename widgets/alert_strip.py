"""Sliding alert strip displayed below the title bar."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont
import theme as T
from i18n import t


class AlertStrip(QWidget):
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = -1
        self._secs = 0.0
        self.setFixedHeight(56)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)

        self._dot = QLabel("●")
        self._dot.setStyleSheet("color:rgba(255,255,255,230); font-size:12px; background:transparent; border:none;")
        self._label = QLabel("")
        self._label.setStyleSheet("color:#fff; font-weight:600; font-size:14px; background:transparent; border:none;")
        self._desc = QLabel("")
        self._desc.setStyleSheet("color:rgba(255,255,255,180); font-size:13px; background:transparent; border:none;")
        self._secs_lbl = QLabel("")
        f = QFont(T.FONT_MONO)
        f.setPixelSize(14)
        self._secs_lbl.setFont(f)
        self._secs_lbl.setStyleSheet("color:rgba(255,255,255,215); background:transparent; border:none;")
        self._btn = QPushButton(t("blinked_btn"))
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,52);border:none;"
            "border-radius:7px;color:#fff;padding:6px 18px;font-size:13px;}"
            "QPushButton:hover{background:rgba(255,255,255,80);}"
        )
        self._btn.clicked.connect(self.dismissed)

        lay.addWidget(self._dot)
        lay.addWidget(self._label)
        lay.addWidget(self._desc, 1)
        lay.addWidget(self._secs_lbl)
        lay.addWidget(self._btn)

        self.hide()

        # urgent pulse
        self._pulse = QTimer(self)
        self._pulse.timeout.connect(self._toggle_dot)
        self._dot_on = True

    def _toggle_dot(self):
        self._dot_on = not self._dot_on
        a = 230 if self._dot_on else 120
        self._dot.setStyleSheet(f"color:rgba(255,255,255,{a}); font-size:10px; background:transparent; border:none;")

    def setState(self, level: int, secs: float):
        self._level = level
        self._secs = secs
        if level < 0:
            self.hide()
            self._pulse.stop()
            return
        info = T.alert_levels()[level]
        self.setStyleSheet(f"AlertStrip{{background:{info['c']};}}")
        self._label.setText(info["label"])
        self._desc.setText(t("alert_desc", sec=info["sec"]))
        self._btn.setText(t("blinked_btn"))
        self._secs_lbl.setText(f"{secs:.1f}s")
        self.show()
        if level >= 3:
            if not self._pulse.isActive():
                self._pulse.start(500)
        else:
            self._pulse.stop()
            self._dot.setStyleSheet("color:rgba(255,255,255,230); font-size:10px; background:transparent; border:none;")

    def paintEvent(self, e):
        # 让 setStyleSheet 的 AlertStrip{background} 生效
        from PyQt6.QtWidgets import QStyleOption, QStyle
        from PyQt6.QtGui import QPainter
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
