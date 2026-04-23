"""
30-day stacked area chart for blink-rate quality.

Layers from bottom to top:
  Blue   - minutes above the healthy range
  Green  - minutes within the healthy range
  Orange - minutes below the healthy range
Y axis = minutes, X axis = date.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPolygonF, QLinearGradient
import theme as T

_HMIN = 15.0
_HMAX = 20.0

# 三层颜色
_C_HEALTHY  = T.BRAND        # 健康：品牌绿
_C_TOO_LOW  = T.WARN         # 过少：警告橙
_C_TOO_HIGH = "#5B8FC9"      # 过多：蓝色（与现有配色不冲突）


def _split_day(day: dict) -> tuple[int, int, int]:
    """
    把一天的原始分钟记录拆成三层分钟数。
    day 格式来自 history_store.load_daily_stats()，额外携带 _minutes 列表。
    如果没有 _minutes 则用 avg 估算。
    """
    minutes = day.get("_minutes", [])
    if minutes:
        healthy  = sum(1 for m in minutes if _HMIN <= m <= _HMAX)
        too_low  = sum(1 for m in minutes if m < _HMIN)
        too_high = sum(1 for m in minutes if m > _HMAX)
    else:
        # 降级：只有聚合数据时用 avg 归类，按总分钟数估算
        total_min = max(1, round(day.get("total", 0) / max(day.get("avg", 1), 1)))
        avg = day.get("avg", 0)
        if _HMIN <= avg <= _HMAX:
            healthy, too_low, too_high = total_min, 0, 0
        elif avg < _HMIN:
            healthy, too_low, too_high = 0, total_min, 0
        else:
            healthy, too_low, too_high = 0, 0, total_min
    return healthy, too_low, too_high


class DailyKChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self.setMinimumHeight(200)

    def setData(self, data):
        self._data = list(data) or []
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        data = self._data
        if not data:
            return

        W = self.width()
        H = self.height()
        PL, PR, PT, PB = 34, 10, 10, 28
        iW = W - PL - PR
        iH = H - PT - PB

        # 拆三层
        layers = [_split_day(d) for d in data]
        totals = [h + l + hi for h, l, hi in layers]
        max_total = max(totals) if totals else 1
        if max_total == 0:
            max_total = 1

        def sy(v):
            return PT + iH - (v / max_total) * iH

        n = len(data)
        def sx(i):
            return PL + (i + 0.5) * (iW / n)

        # 网格线
        pen = QPen(QColor(T.C_BORDER))
        pen.setWidthF(0.6)
        p.setPen(pen)
        for frac in (0.25, 0.5, 0.75, 1.0):
            y = int(PT + iH - frac * iH)
            p.drawLine(PL, y, PL + iW, y)

        # Y 轴标签（分钟数）
        f = QFont(T.FONT_UI)
        f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(9)
        p.setFont(f)
        p.setPen(QColor(T.C_TEXT3))
        for frac in (0.25, 0.5, 0.75, 1.0):
            val = int(frac * max_total)
            y = PT + iH - frac * iH
            p.drawText(QRectF(0, y - 7, PL - 4, 14),
                       int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                       str(val))

        def _area(ys_bot, ys_top, hex_color, alpha):
            color = QColor(hex_color)
            color.setAlphaF(alpha)
            pts = []
            for i in range(n):
                pts.append(QPointF(sx(i), ys_top[i]))
            for i in range(n - 1, -1, -1):
                pts.append(QPointF(sx(i), ys_bot[i]))
            poly = QPolygonF(pts)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawPolygon(poly)
            # 顶部描边
            pen2 = QPen(QColor(hex_color))
            pen2.setWidthF(1.4)
            p.setPen(pen2)
            p.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(n - 1):
                p.drawLine(QPointF(sx(i), ys_top[i]), QPointF(sx(i + 1), ys_top[i + 1]))

        # 计算各层 y 坐标
        base   = [PT + iH] * n          # 底线（最大值处的像素底）
        top1   = [sy(layers[i][2]) if totals[i] else PT + iH for i in range(n)]   # 过多层顶
        # 底部堆叠：too_high 先，然后 healthy，然后 too_low
        top_th = [PT + iH - (layers[i][2] / max_total) * iH for i in range(n)]
        top_h  = [PT + iH - ((layers[i][2] + layers[i][0]) / max_total) * iH for i in range(n)]
        top_tl = [PT + iH - (totals[i] / max_total) * iH for i in range(n)]

        # 绘制三层（从底到顶）
        _area(base,   top_th, _C_TOO_HIGH, 0.55)
        _area(top_th, top_h,  _C_HEALTHY,  0.65)
        _area(top_h,  top_tl, _C_TOO_LOW,  0.55)

        # X 轴日期标签
        p.setPen(QColor(T.C_TEXT3))
        for i, d in enumerate(data):
            if i % 5 == 0 or i == n - 1:
                x = sx(i)
                dt = d["date"]
                txt = f"{dt.month}/{dt.day}"
                p.drawText(QRectF(x - 20, H - 18, 40, 14),
                           Qt.AlignmentFlag.AlignCenter, txt)
