"""Bar chart of today's hourly average blink rate."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont
import theme as T
from i18n import t


class HourlyBars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # list of (hour_label, rate)
        self.setMinimumHeight(72)

    def setData(self, data):
        self._data = list(data) or []
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()
        GAP = 2
        N = 24
        slot = (W - GAP * (N - 1)) / N
        bar_area_h = H - 14
        peak = 28.0

        # 把传入数据转成 hour→rate 字典
        rate_map = {}
        for label, rate in (self._data or []):
            try:
                rate_map[int(label)] = rate
            except ValueError:
                pass

        f = QFont(T.FONT_UI)
        f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(9)
        p.setFont(f)

        # 无数据时显示提示
        if not rate_map:
            p.setPen(QColor(T.C_TEXT3))
            p.drawText(QRectF(0, 0, W, H),
                       Qt.AlignmentFlag.AlignCenter, t("no_data_hourly"))
            return

        for hour in range(N):
            x = hour * (slot + GAP)
            rate = rate_map.get(hour)

            if rate is not None:
                pct = max(0.0, min(1.0, rate / peak))
                bh = max(4.0, pct * (bar_area_h - 4))
                y = bar_area_h - bh
                if 15 <= rate <= 20:
                    c = QColor(T.BRAND)
                elif rate < 15:
                    c = QColor(T.WARN)
                else:
                    c = QColor("#B04030")
                c.setAlphaF(0.8)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(QRectF(x, y, slot, bh), 2, 2)

            # X 轴标签：只标 0/6/12/18
            if hour % 6 == 0:
                p.setPen(QColor(T.C_TEXT3))
                p.drawText(QRectF(x, bar_area_h + 2, slot * 2, 12),
                           Qt.AlignmentFlag.AlignLeft, str(hour))
