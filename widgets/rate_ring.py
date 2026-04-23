"""Circular blink-rate indicator (72x72)."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
import math
import theme as T
from i18n import t


class RateRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(72, 72)
        self._rate = 0.0
        self._alert = -1

    def setRate(self, r, alert_level=-1):
        self._rate = float(r)
        self._alert = alert_level
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 32
        cx = cy = 36
        pct = max(0.0, min(1.0, self._rate / 30.0))

        if self._alert >= 0:
            sc = QColor(T.ALERT_LEVELS[self._alert]["c"])
        elif 15 <= self._rate <= 20:
            sc = QColor(T.BRAND)
        else:
            sc = QColor(T.WARN)

        # track
        pen = QPen(QColor(T.C_BORDER))
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))

        # progress
        pen.setColor(sc)
        p.setPen(pen)
        span = -int(360 * 16 * pct)
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 90 * 16, span)

        # text
        f = QFont(T.FONT_UI)
        f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(15)
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(sc)
        p.drawText(QRectF(0, 18, 72, 18), Qt.AlignmentFlag.AlignCenter,
                   f"{self._rate:.1f}")

        f2 = QFont(T.FONT_UI)
        f2.setFamilies([T.FONT_UI] + T.FONT_FB)
        f2.setPixelSize(9)
        p.setFont(f2)
        p.setPen(QColor(T.C_TEXT3))
        p.drawText(QRectF(0, 38, 72, 14), Qt.AlignmentFlag.AlignCenter,
                   t("unit_per_min_zh"))
