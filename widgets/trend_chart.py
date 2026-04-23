"""Blink-rate trend chart for the recent 30-minute window."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QFont, QPainterPath,
)
import theme as T
from i18n import t


class TrendChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # list[float]  rate per bucket
        self.setMinimumHeight(150)

    def setData(self, data):
        self._data = list(data) or []
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()
        PL, PR, PT, PB = 34, 10, 8, 24
        iW = W - PL - PR
        iH = H - PT - PB

        data = self._data
        if len(data) < 2:
            # 真实数据不足，显示空状态
            f = QFont(T.FONT_UI)
            f.setFamilies([T.FONT_UI] + T.FONT_FB)
            f.setPixelSize(12)
            p.setFont(f)
            p.setPen(QColor(T.C_TEXT3))
            p.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter,
                       t("no_data_trend"))
            return
        n = len(data)
        mn_val, mx_val = 4.0, 28.0

        def tx(i):
            return PL + i / (n - 1) * iW

        def ty(r):
            r = max(mn_val, min(mx_val, r))
            return PT + iH - (r - mn_val) / (mx_val - mn_val) * iH

        # y grid
        pen = QPen(QColor(T.C_BORDER))
        pen.setWidthF(1)
        p.setPen(pen)
        yt = [5, 10, 15, 20, 25]
        for v in yt:
            y = ty(v)
            p.drawLine(int(PL), int(y), int(PL + iW), int(y))

        # healthy band
        y20, y15 = ty(20), ty(15)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(74, 158, 128, 18))
        p.drawRect(QRectF(PL, y20, iW, y15 - y20))

        # area + line
        path = QPainterPath()
        line = QPainterPath()
        for i, r in enumerate(data):
            x, y = tx(i), ty(r)
            if i == 0:
                line.moveTo(x, y)
                path.moveTo(x, y)
            else:
                line.lineTo(x, y)
                path.lineTo(x, y)
        last_x = tx(n - 1)
        first_x = tx(0)
        path.lineTo(last_x, PT + iH)
        path.lineTo(first_x, PT + iH)
        path.closeSubpath()

        grad = QLinearGradient(0, PT, 0, PT + iH)
        grad.setColorAt(0.0, QColor(74, 158, 128, 51))
        grad.setColorAt(1.0, QColor(74, 158, 128, 0))
        p.fillPath(path, QBrush(grad))

        pen = QPen(QColor(T.BRAND))
        pen.setWidthF(2)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(line)

        # current dot
        cx, cy = tx(n - 1), ty(data[-1])
        p.setBrush(QColor(74, 158, 128, 46))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 7, 7)
        p.setBrush(QColor(T.BRAND))
        p.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

        # labels
        f = QFont(T.FONT_UI)
        f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(9)
        p.setFont(f)
        p.setPen(QColor(T.C_TEXT3))
        for v in yt:
            p.drawText(QRectF(0, ty(v) - 7, PL - 5, 14),
                       int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                       str(v))

        for i, l in enumerate(["-30min", "-20min", "-10min", t("trend_now")]):
            xi = PL + (i / 3) * iW
            p.drawText(QRectF(xi - 40, H - 18, 80, 14),
                       Qt.AlignmentFlag.AlignCenter, l)

        # band label
        p.setPen(QColor(74, 158, 128, 180))
        f2 = QFont(T.FONT_UI)
        f2.setFamilies([T.FONT_UI] + T.FONT_FB)
        f2.setPixelSize(9)
        p.setFont(f2)
        p.drawText(int(PL + 8), int(y20 - 4), t("trend_band"))
