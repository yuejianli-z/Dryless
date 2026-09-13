"""Native, accessible time bubbles for historical recorded minute buckets.

Frequency is a visual reference, never a medical health classification. Bubble
area is proportional to recorded minutes, including minutes with zero blinks.
"""
from __future__ import annotations

import html
import math
from datetime import timedelta

from PyQt6.QtCore import Qt, QPointF, QRectF, QSize, QSizeF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QSizePolicy, QToolTip

import config
import theme as T
from widgets.chart_label_layout import place_mean_label


COLOR_LOW = "#D95C50"
COLOR_MID = "#E4B840"
COLOR_HIGH = "#4A9E80"


def _font(size=11, bold=False):
    font = T.ui_font()
    font.setFamilies([T.FONT_UI] + T.FONT_FB)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    return font


def _blend(a, b, amount):
    amount = min(1., max(0., amount))
    a, b = QColor(a), QColor(b)
    return QColor(*(round(x + (y - x) * amount) for x, y in zip(
        (a.red(), a.green(), a.blue()), (b.red(), b.green(), b.blue()))))


def _color(value, reference):
    # Fixed across dates and grains. Red through golden yellow to soft green;
    # the legend and every data point use this same continuous mapping.
    offset = float(value) - reference
    strength = min(1., abs(offset) / 6.)
    return _blend(COLOR_MID, COLOR_LOW if offset < 0 else COLOR_HIGH, strength)


class TimeBubbleChart(QWidget):
    """Chart plus legends. Times must be consistently naive or aware datetimes.

    ``periodClicked`` emits the original point dict; the parent owns drilling.
    Empty periods should be included in points to retain missing observations.
    ``axis_max`` can stabilize the frequency scale across grain changes.
    """
    periodClicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._language = None
        self._points = []
        self._grain = "day"
        self._mean = None
        self._reference = 16.
        self._axis_max = 30.
        self._max_minutes = 480.
        self._radius_max = 17.
        self._legend_values = [60, 180, 360]
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.scroll = QScrollArea(self)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        # Override main.py's global zero-height horizontal scrollbar rule locally.
        self.scroll.horizontalScrollBar().setStyleSheet(
            "QScrollBar:horizontal { height: 10px; background: #EAF2EC; border: none; margin: 0; }"
            "QScrollBar::handle:horizontal { background: #B9CEBF; min-width: 28px; border-radius: 4px; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }")
        self.canvas = _BubbleCanvas(self)
        self.scroll.setWidget(self.canvas)
        # QScrollArea.setWidget enables auto-fill; preserve the parent card surface.
        self.canvas.setAutoFillBackground(False)
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.horizontalScrollBar().valueChanged.connect(lambda _: QToolTip.hideText())
        layout.addWidget(self.scroll, 1)
        self.legend = _BubbleLegend(self)
        layout.addWidget(self.legend)
        self.setAccessibleName(self._tr("眨眼时间气泡图", "Blink frequency timeline"))

    def _tr(self, zh, en):
        return zh if (self._language or getattr(config, "LANGUAGE", "zh")) == "zh" else en

    def sizeHint(self):
        return QSize(800, 300)

    def set_language(self, language=None):
        self._language = language
        self.setAccessibleName(self._tr("眨眼时间气泡图", "Blink frequency timeline"))
        self.canvas.update()
        self.legend.update()

    def set_data(self, points, grain, mean=None, reference=16.0, axis_max=None):
        if grain not in ("hour", "day", "week", "month"):
            raise ValueError("grain must be hour, day, week or month")
        self._points = sorted(list(points), key=lambda row: row["start"])
        self._grain = grain
        self._reference = max(.001, float(reference))
        valid = [row for row in self._points if self._valid(row)]
        minutes = sum(row["minutes"] for row in valid)
        if mean is None and minutes:
            # Use totals when supplied, otherwise correctly weight each average.
            mean = sum(row["total"] if row.get("total") is not None else
                       row["average"] * row["minutes"] for row in valid) / minutes
        self._mean = float(mean) if mean is not None and math.isfinite(float(mean)) else None
        padding = 1. if axis_max is not None else 1.12
        peak = max([30., self._reference * 1.2, float(axis_max or 0)] +
                   [float(row["average"]) * padding for row in valid] +
                   ([self._mean * padding] if self._mean is not None else []))
        step = 10 ** math.floor(math.log10(peak / 4))
        self._tick_step = next(unit * step for unit in (1, 2, 5, 10) if unit * step >= peak / 4)
        self._axis_max = math.ceil(peak / self._tick_step) * self._tick_step
        if axis_max is not None:
            self._axis_max = peak
        if peak == 30.:
            self._axis_max, self._tick_step = 30., 10.
        base, values = {
            "hour": (60, [15, 30, 60]),
            "day": (480, [60, 180, 360]),
            "week": (3360, [600, 1800, 3000]),
            "month": (14400, [1800, 5400, 10800]),
        }[grain]
        self._max_minutes = max(base, max((row["minutes"] for row in valid), default=0))
        # Sparse real histories still get an honest, useful area legend.
        maximum = max((row["minutes"] for row in valid), default=base)
        if maximum < values[0]:
            power = 10 ** max(0, math.floor(math.log10(max(1, maximum))) - 1)
            values = sorted(set(max(1, round(maximum * factor / power) * power)
                                for factor in (.25, .5, 1)))
            self._max_minutes = max(1, maximum, max(values))
        self._legend_values = values
        self.canvas._selected = -1
        self.canvas._hovered = -1
        self.canvas._hits = []
        self.canvas.setMinimumWidth(max(0, len(self._points) * 24 + 85) if len(self._points) > 55 else 0)
        self.scroll.horizontalScrollBar().setValue(0)
        self.canvas.update()
        self.legend.update()

    @staticmethod
    def _valid(row):
        avg = row.get("average")
        return row.get("minutes", 0) > 0 and avg is not None and math.isfinite(float(avg)) and avg >= 0

    def _radius(self, minutes):
        return math.sqrt(max(0, minutes) / self._max_minutes) * self._radius_max

    def _duration(self, minutes):
        minutes = int(round(minutes))
        hours, remainder = divmod(minutes, 60)
        if hours:
            return (f"{hours}小时" + (f"{remainder}分" if remainder else "")) if self._tr("zh", "en") == "zh" else (
                f"{hours}h" + (f" {remainder}m" if remainder else ""))
        return self._tr(f"{minutes}分钟", f"{minutes} min")

    def _period_label(self, row):
        start, end = row["start"], row["end"] - timedelta(microseconds=1)
        if self._grain == "hour":
            return f"{start:%Y-%m-%d %H:%M} — {row['end']:%H:%M}"
        if self._grain == "day":
            return f"{start:%Y-%m-%d}"
        return f"{start:%Y-%m-%d} — {end:%Y-%m-%d}"

    def _tooltip(self, row):
        title = html.escape(self._period_label(row))
        values = [(self._tr("平均频率", "Average frequency"),
                   self._tr(f"{row['average']:.1f} 次/记录分钟", f"{row['average']:.1f} / recorded min")),
                  (self._tr("记录时长", "Recorded duration"), self._duration(row["minutes"]))]
        if row.get("total") is not None:
            values.append((self._tr("眨眼总数", "Total blinks"), f"{row['total']:,}"))
        if self._grain != "hour":
            values.append((self._tr("有记录天数", "Days with records"),
                           f"{row.get('recorded_days', 0)} / {row.get('calendar_days', 1)}"))
        body = "".join(f"<tr><td style='color:#D3D1CB;padding-right:20px'>{html.escape(k)}</td>"
                       f"<td align='right'>{html.escape(v)}</td></tr>" for k, v in values)
        note = self._tr("仅覆盖部分周期", "Partial period") if row.get("partial") else ""
        action = self._tr("点击或按 Enter 展开", "Click or press Enter to explore") if self._grain != "hour" else ""
        return f"<b>{title}</b><table cellspacing='4'>{body}</table><small>{note}{' · ' if note and action else ''}{action}</small>"


class _BubbleCanvas(QWidget):
    def __init__(self, chart):
        super().__init__()
        self.chart = chart
        self._hits = []
        self._selected = -1
        self._hovered = -1
        self._mean_label_rect = None
        self._mean_label_fallback = False
        self.setMinimumHeight(136)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(chart._tr("气泡图，方向键选择，回车展开", "Timeline. Arrow keys select, Enter explores."))
        self.setStyleSheet("QToolTip { color: #FFFFFF; background: #37352F; border: 1px solid #787774; padding: 10px; }")

    def paintEvent(self, event):
        c, rows = self.chart, self.chart._points
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(_font())
        # Header has enough clearance for a fallback label even when a large
        # bubble sits at the maximum frequency and extends above the plot.
        left, right, top, bottom = 48., self.width() - 25., 38., self.height() - 32.
        width, height = max(1., right - left), max(1., bottom - top)
        y = lambda value: bottom - value / c._axis_max * height
        p.fillRect(QRectF(left, y(20), width, y(15) - y(20)), QColor('#EDF4EF'))
        p.setPen(QPen(QColor('#C5DCCE'), 1))
        for bound in (15, 20):
            p.drawLine(QPointF(left, y(bound)), QPointF(right, y(bound)))
        value = 0.
        while value <= c._axis_max:
            yy = y(value)
            p.setPen(QPen(QColor(T.C_BORDER), 1))
            p.drawLine(QPointF(left, yy), QPointF(right, yy))
            p.setPen(QColor(T.C_TEXT3))
            p.drawText(QRectF(0, yy - 9, left - 11, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value:g}")
            value += c._tick_step if hasattr(c, "_tick_step") else 10.
        p.drawText(QRectF(left, 4, 400, 20), c._tr("频率 · 次/记录分钟", "Frequency · blinks / recorded min"))
        self._hits = []
        self._mean_label_rect = None
        self._mean_label_fallback = False
        if not rows:
            p.setPen(QColor(T.C_TEXT2))
            p.drawText(QRectF(left, top, width, height), Qt.AlignmentFlag.AlignCenter,
                       c._tr("这个时间范围还没有记录", "No records in this time range"))
            return
        start, end = rows[0]["start"], rows[-1]["end"]
        seconds = max(1., (end - start).total_seconds())
        x = lambda row: left + (((row["start"] - start).total_seconds() +
                                (row["end"] - row["start"]).total_seconds() / 2) / seconds) * width
        centers = [x(row) for row in rows]
        # Fit neighboring circle areas, so a short final month does not shrink
        # every full month to the width of that partial period.
        present = [(centers[i], math.sqrt(row["minutes"] / c._max_minutes))
                   for i, row in enumerate(rows) if c._valid(row)]
        limits = [(b[0] - a[0]) * .88 / (a[1] + b[1])
                  for a, b in zip(present, present[1:]) if b[0] > a[0]]
        new_radius = min([17.] + limits)
        if abs(new_radius - c._radius_max) > .1:
            c._radius_max = new_radius
            c.legend.update()
        tick_every = max(1, math.ceil(len(rows) / max(1, width // (90 if c._grain == "month" else 75))))
        last_label_end = -1000
        for index, row in enumerate(rows):
            if index % tick_every and index != len(rows) - 1:
                continue
            dt = row.get("period_start", row["start"])
            label = f"{dt:%H:%M}" if c._grain == "hour" else (
                f"{dt:%Y/%m}" if c._grain == "month" else f"{dt:%m/%d}")
            xx, label_width = centers[index], p.fontMetrics().horizontalAdvance(label) + 6
            if xx - label_width / 2 <= last_label_end + 8:
                continue
            p.setPen(QColor(T.C_TEXT3))
            p.drawText(QRectF(xx - label_width / 2, bottom + 13, label_width, 18), Qt.AlignmentFlag.AlignCenter, label)
            last_label_end = xx + label_width / 2
        if c._mean is not None:
            yy = y(c._mean)
            pen = QPen(QColor("#919AA6"), 1)
            pen.setDashPattern([4, 5])
            p.setPen(pen)
            p.drawLine(QPointF(left, yy), QPointF(right, yy))
        path = QPainterPath()
        previous = None
        previous_point = None
        segments = []
        for index, row in enumerate(rows):
            if not c._valid(row):
                previous = None
                previous_point = None
                p.setPen(QPen(QColor("#C7C7C2"), 1.5))
                p.drawLine(QPointF(centers[index] - 2, bottom + 7), QPointF(centers[index] + 2, bottom + 7))
                continue
            point = QPointF(centers[index], y(row["average"]))
            if previous is not None and previous["end"] == row["start"]:
                path.lineTo(point)
                segments.append((previous_point, point))
            else:
                path.moveTo(point)
            previous = row
            previous_point = point
            self._hits.append((index, point, c._radius(row["minutes"])))
        p.setPen(QPen(QColor("#BAC0C8"), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        for index, center, radius in self._hits:
            row = rows[index]
            color = _color(row["average"], c._reference)
            fill = QColor(color)
            fill.setAlpha(235)
            active = index == self._hovered or (self.hasFocus() and index == self._selected)
            pen = QPen(QColor("#1F2937") if active else color.darker(112), 2 if active else 1)
            if row.get("partial"):
                pen.setDashPattern([3, 2])
            p.setPen(pen)
            p.setBrush(fill)
            p.drawEllipse(center, radius, radius)
            if active:
                p.setPen(QPen(QColor("#D7DDE5"), 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(center, max(6, radius) + 4, max(6, radius) + 4)
        if c._mean is not None:
            label = c._tr(f"本期记录平均 {c._mean:.1f}", f"Recorded average {c._mean:.1f}")
            label_width = max(p.fontMetrics().horizontalAdvance(text) for text in (f"本期记录平均 {c._mean:.1f}", f"Recorded average {c._mean:.1f}")) + 16
            label_height = max(22, p.fontMetrics().height() + 8)
            plot = QRectF(left, top, width, height)
            visible_plot = plot.intersected(QRectF(self.visibleRegion().boundingRect()))
            if visible_plot.isEmpty():
                visible_plot = plot
            fallback = QRectF(visible_plot.right() - label_width, 3,
                              label_width, label_height)
            rect, outside = fallback, True
            self._mean_label_rect, self._mean_label_fallback = rect, outside
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(T.C_CARD))
            p.drawRoundedRect(rect, 4, 4)
            p.setPen(QColor("#535D6B"))
            p.drawText(rect.adjusted(8, 0, -8, 0),
                       Qt.AlignmentFlag.AlignCenter, label)
        if not self._hits:
            p.setPen(QColor(T.C_TEXT2))
            p.drawText(QRectF(left, top, width, height), Qt.AlignmentFlag.AlignCenter,
                       c._tr("这个时间范围还没有记录", "No records in this time range"))

    def _hit(self, position):
        candidates = [(math.hypot(position.x() - point.x(), position.y() - point.y()), index)
                      for index, point, radius in self._hits
                      if math.hypot(position.x() - point.x(), position.y() - point.y()) <= max(radius + 3, 8)]
        return min(candidates)[1] if candidates else -1

    def _show_tip(self, index, global_position):
        if index >= 0:
            QToolTip.showText(global_position, self.chart._tooltip(self.chart._points[index]), self)

    def mouseMoveEvent(self, event):
        index = self._hit(event.position())
        if index != self._hovered:
            self._hovered = index
            self.update()
        self.setCursor(Qt.CursorShape.PointingHandCursor if index >= 0 and self.chart._grain != "hour" else Qt.CursorShape.ArrowCursor)
        if index >= 0:
            self._show_tip(index, event.globalPosition().toPoint())
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered = -1
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._hit(event.position())
            if index >= 0:
                self._selected = index
                self.setFocus(Qt.FocusReason.MouseFocusReason)
                self.update()
                if self.chart._grain != "hour":
                    QToolTip.hideText()
                    self.chart.periodClicked.emit(self.chart._points[index])
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        indexes = [index for index, _, _ in self._hits]
        key = event.key()
        if indexes and key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End):
            if key == Qt.Key.Key_Home:
                self._selected = indexes[0]
            elif key == Qt.Key.Key_End:
                self._selected = indexes[-1]
            elif self._selected not in indexes:
                self._selected = indexes[-1 if key == Qt.Key.Key_Left else 0]
            else:
                move = -1 if key == Qt.Key.Key_Left else 1
                self._selected = indexes[max(0, min(len(indexes) - 1, indexes.index(self._selected) + move))]
            center = next(point for index, point, _ in self._hits if index == self._selected)
            self.chart.scroll.ensureVisible(round(center.x()), round(center.y()), 65, 30)
            self._show_tip(self._selected, self.mapToGlobal(center.toPoint()))
            self.update()
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space) and self._selected >= 0:
            if self.chart._grain != "hour":
                QToolTip.hideText()
                self.chart.periodClicked.emit(self.chart._points[self._selected])
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            QToolTip.hideText()
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        QToolTip.hideText()
        self.update()
        super().focusOutEvent(event)


class _BubbleLegend(QWidget):
    def __init__(self, chart):
        super().__init__(chart)
        self.chart = chart
        self.setFixedHeight(44)

    def paintEvent(self, event):
        c = self.chart
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(_font(10))
        p.setPen(QPen(QColor(T.C_BORDER), 1))
        p.drawLine(0, 0, self.width(), 0)
        width = min(225, self.width() * .30)
        gradient = QLinearGradient(0, 0, width, 0)
        for index in range(25):
            position = index / 24
            gradient.setColorAt(position, _color(c._reference - 6 + position * 12, c._reference))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(QRectF(0, 14, width, 8), 4, 4)
        p.setPen(QColor(T.C_TEXT3))
        p.drawText(QRectF(0, 24, width / 3, 18), c._tr(f"≤{c._reference-6:g} · 低频", f"≤{c._reference-6:g} · Lower"))
        p.drawText(QRectF(width / 3, 24, width / 3, 18), Qt.AlignmentFlag.AlignCenter,
                   f"{c._reference:g}")
        p.drawText(QRectF(width * 2 / 3, 24, width / 3, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   c._tr(f"≥{c._reference+6:g} · 高频", f"≥{c._reference+6:g} · Higher"))
        xx = width + 28
        title = c._tr("面积＝记录时长", "Area = recorded time")
        p.drawText(QRectF(xx, 13, 170, 20), title)
        xx += max(p.fontMetrics().horizontalAdvance(text) for text in ("面积＝记录时长", "Area = recorded time")) + 17
        for value in c._legend_values:
            radius = c._radius(value)
            p.setPen(QPen(QColor("#9B9B95"), 1))
            p.setBrush(QColor("#F1F1EF"))
            p.drawEllipse(QPointF(xx + radius, 22), radius, radius)
            xx += radius * 2 + 5
            hours, minutes = divmod(int(value), 60)
            label = (f"{hours}h" + (f" {minutes}m" if minutes else "")) if hours else f"{minutes}m"
            p.setPen(QColor(T.C_TEXT3))
            p.drawText(QRectF(xx, 14, p.fontMetrics().horizontalAdvance(label) + 2, 20), label)
            xx += p.fontMetrics().horizontalAdvance(label) + 19
