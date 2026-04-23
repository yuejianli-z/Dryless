"""Semi-circular health score gauge."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
import math
import theme as T
from i18n import t


class HealthGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(108, 88)
        self._score = 0
    def setScore(self, s):
        self._score = max(0, min(100, int(s)))
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        R = 38
        CX = 54
        CY = 48
        # 半环：从 0.85π 到 0.85π + 1.3π，共 234°
        start_deg = 180 - 27   # Qt: 12点=90°，逆时针为正
        sweep_deg = 234
        pct = self._score / 100.0

        if self._score >= 80:
            sc = QColor(T.BRAND)
        elif self._score >= 60:
            sc = QColor(T.WARN)
        else:
            sc = QColor("#B03030")

        rect = QRectF(CX - R, CY - R, 2 * R, 2 * R)

        # track
        pen = QPen(QColor(T.C_BORDER))
        pen.setWidthF(5.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, int(start_deg * 16), int(-sweep_deg * 16))

        # fill
        if pct > 0.02:
            pen.setColor(sc)
            p.setPen(pen)
            p.drawArc(rect, int(start_deg * 16), int(-sweep_deg * 16 * pct))

        # center text
        f = QFont(T.FONT_UI)
        f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(22)
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(sc)
        p.drawText(QRectF(0, CY - 12, 108, 22), Qt.AlignmentFlag.AlignCenter,
                   str(self._score))

        f2 = QFont(T.FONT_UI)
        f2.setFamilies([T.FONT_UI] + T.FONT_FB)
        f2.setPixelSize(9)
        p.setFont(f2)
        p.setPen(QColor(T.C_TEXT3))
        p.drawText(QRectF(0, CY + 7, 108, 12), Qt.AlignmentFlag.AlignCenter,
                   t("health_score"))
