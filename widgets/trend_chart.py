"""Recent completed minute buckets, with explicit window and accessible values."""
import math

from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QLinearGradient

import theme as T
import config
from widgets.time_bubble_chart import _color


class TrendChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._window = None
        self._selected = -1
        self.setMinimumHeight(72)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(self._tr('逐分钟眨眼频率', 'Minute-by-minute blink frequency'))
        self.setAccessibleDescription(self._tr('左右方向键查看各分钟数值。', 'Use left and right arrows to inspect minute values.'))

    @staticmethod
    def _tr(zh, en):
        return zh if config.LANGUAGE == 'zh' else en

    def setData(self, data):
        values = []
        for value in data:
            try:
                value = float(value)
                values.append(value if math.isfinite(value) and value >= 0 else None)
            except (TypeError, ValueError):
                values.append(None)
        values = values[-60:]
        if values != self._data:
            self._data = values
            self._selected = -1
            QToolTip.hideText()
            self.update()

    def setWindow(self, minutes=None):
        if minutes not in (None, 15, 30, 60):
            raise ValueError('minutes must be None, 15, 30, or 60')
        self._window = minutes
        self._selected = -1
        QToolTip.hideText()
        self.update()

    def windowMinutes(self):
        return self._window or (15 if len(self._data) <= 15 else 30 if len(self._data) <= 30 else 60)

    def _visible(self):
        return self._data[-self.windowMinutes():]

    def _geometry(self):
        plot = QRectF(8, 10, max(1, self.width()-16), min(38, max(18, self.height()-40)))
        data = self._visible()
        window = self.windowMinutes()
        step = plot.width()/window
        points = [None if value is None else QPointF(
            plot.left()+(window-len(data)+i+.5)*step, plot.center().y())
            for i,value in enumerate(data)]
        return plot, 30., points

    def _label(self, index):
        data = self._visible()
        ago = len(data) - 1 - index
        when = self._tr('最新完整分钟', 'Latest completed minute') if ago == 0 else self._tr(
            f'最新完整分钟前 {ago} 分钟', f'{ago} min before the latest completed minute')
        return when + self._tr(f' · {data[index]:g} 次/分', f' · {data[index]:g} blinks/min')

    def _show_value(self, index):
        self._selected = index
        _, _, points = self._geometry()
        if 0 <= index < len(points) and points[index] is not None:
            label = self._label(index)
            QToolTip.showText(self.mapToGlobal(points[index].toPoint()), label, self)
            self.setAccessibleDescription(label)
        else:
            QToolTip.hideText()
        self.update()

    def mouseMoveEvent(self, event):
        plot, _, points = self._geometry()
        selected = -1
        if plot.contains(event.position()):
            step = plot.width()/self.windowMinutes()
            index = int((event.position().x()-plot.left())/step)-(self.windowMinutes()-len(points))
            if 0 <= index < len(points) and points[index] is not None:
                selected = index
        if selected != self._selected:
            self._show_value(selected)

    def leaveEvent(self, event):
        self._show_value(-1)
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        valid = [i for i, value in enumerate(self._visible()) if value is not None]
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End) and valid:
            if event.key() == Qt.Key.Key_Home:
                index = valid[0]
            elif event.key() == Qt.Key.Key_End or self._selected not in valid:
                index = valid[-1]
            else:
                step = -1 if event.key() == Qt.Key.Key_Left else 1
                index = valid[max(0, min(len(valid) - 1, valid.index(self._selected) + step))]
            self._show_value(index)
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self._show_value(-1)
        super().focusOutEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(T.ui_font(11))
        plot, _, points = self._geometry()
        data = self._visible()
        window = self.windowMinutes()
        offset = window-len(data)
        step = plot.width()/window
        gap = 6 if window==15 else 4 if window==30 else 3
        for slot in range(window):
            index = slot-offset
            value = data[index] if 0 <= index < len(data) else None
            rect = QRectF(plot.left()+slot*step+gap/2, plot.top(), max(1,step-gap), plot.height())
            selected = index == self._selected and value is not None
            radius = min(7, rect.width()/3)
            if value is None:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(T.C_BORDER), 1))
            else:
                # Same fixed frequency mapping as Stats; never a health score.
                p.setBrush(_color(value,16))
                p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, radius, radius)
            if selected:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(T.BRAND), 1.5))
                p.drawRoundedRect(rect.adjusted(-2,-2,2,2), radius+2, radius+2)
            if value is not None and rect.width() >= 38:
                text = f'{value:.1f}'.rstrip('0').rstrip('.')
                # Preserve zero as a recorded value, distinct from an empty slot.
                if not text: text='0'
                p.setPen(QColor('#183126' if value>=20 else '#302415'))
                p.drawText(rect,Qt.AlignmentFlag.AlignCenter,text)
        p.setPen(QColor(T.C_TEXT3))
        footer_y=plot.bottom()+10
        available=any(value is not None for value in data)
        p.drawText(QRectF(plot.left(),footer_y,180,18),Qt.AlignmentFlag.AlignLeft,
                   self._tr(f'前 {window-1} 分钟',f'{window-1} min earlier') if available else self._tr('每格 1 分钟','1 minute per tile'))
        p.drawText(QRectF(plot.right()-220,footer_y,220,18),Qt.AlignmentFlag.AlignRight,
                   self._tr('最新完整分钟','Latest completed minute') if available else self._tr('等待第一分钟的有效记录','Waiting for the first valid minute'))
        if available:
            # Compact key avoids an axis while explaining both colour and gaps.
            key_width=300
            x=plot.center().x()-key_width/2
            p.drawText(QRectF(x,footer_y,50,18),Qt.AlignmentFlag.AlignRight,self._tr('低频','Lower'))
            gradient=QLinearGradient(x+59,0,x+113,0)
            gradient.setColorAt(0,_color(10,16));gradient.setColorAt(.5,_color(16,16));gradient.setColorAt(1,_color(22,16))
            p.setBrush(gradient);p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x+59,footer_y+5,54,6),3,3)
            p.setPen(QColor(T.C_TEXT3))
            p.drawText(QRectF(x+122,footer_y,178,18),Qt.AlignmentFlag.AlignLeft,
                       self._tr('高频 · 空心为无记录','Higher · Outline: no record'))
