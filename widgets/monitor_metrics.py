"""Compact live instruments; real values, common frequency colours, no hover popups."""
import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QSizePolicy
import config
import theme as T
from microbreak import PRESENCE_SECONDS
from widgets.time_bubble_chart import _color


def _tr(zh, en):
    return zh if config.LANGUAGE == 'zh' else en


class MonitorMetrics(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(185)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.state = {}
        self.ready = False
        self.running = False
        self.paused = False

    def setState(self, state, ready, running, paused):
        self.state = dict(state)
        self.ready, self.running, self.paused = ready, running, paused
        self.setAccessibleName(_tr('实时眨眼与微休息', 'Live blinks and microbreak'))
        value = self.rate
        self.setAccessibleDescription(_tr('最近60秒：', 'Last 60 seconds: ') +
            (f'{value:.1f} /min' if value is not None else _tr('采集中', 'Collecting')))
        self.update()

    @property
    def rate(self):
        value = self.state.get('rolling_rate')
        return value if self.running and self.ready and value is not None and math.isfinite(value) else None

    @property
    def blink_progress(self):
        if not self.running or not self.ready or self.paused or self.state.get('microbreak_active'):
            return 0.
        threshold = max(1., config.NO_BLINK_ALERT_SEC + 2*config.ALERT_INTERVAL_SEC)
        return min(1., max(0., self.state.get('reminder_elapsed', self.state.get('no_blink', 0.)))/threshold)

    @property
    def break_progress(self):
        if not self.running or self.paused:
            return 0.
        return min(1., max(0., self.state.get('microbreak_presence', 0.))/PRESENCE_SECONDS)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        half = (width-24)/2
        body_height = height-58
        diameter = min(half-20, body_height-29, 160)
        center_y = max(27+diameter/2, body_height/2)
        self._main_rect = QRectF(0, 0, width, body_height)
        self._break_rect = QRectF(0, height-53, width, 53)

        def text(rect, value, size=13, color=T.C_TEXT2, weight=400, align=Qt.AlignmentFlag.AlignLeft):
            p.setFont(T.ui_font(size, weight))
            p.setPen(QColor(color))
            p.drawText(rect, align | Qt.AlignmentFlag.AlignVCenter, value)

        def track(rect, portion, color, radius=3):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(T.C_SURFACE))
            p.drawRoundedRect(rect, radius, radius)
            if portion > 0:
                p.setBrush(QColor(color))
                p.drawRoundedRect(QRectF(rect.x(), rect.y(), max(2, rect.width()*portion), rect.height()), radius, radius)

        # Two fixed, equal columns keep language switches and live updates still.
        text(QRectF(0, 0, half, 22), _tr('距上次眨眼', 'Since last blink'))
        text(QRectF(half+24, 0, half, 22), _tr('最近 60 秒', 'Last 60 seconds'), align=Qt.AlignmentFlag.AlignHCenter)
        seconds = max(0., self.state.get('no_blink', 0.))
        level = int(self.state.get('alert_level', -1))
        micro = bool(self.state.get('microbreak_active')) and self.running and not self.paused
        active = self.running and self.ready
        accent = T.ALERT_LEVELS[min(2, level)]['c'] if active and not self.paused and not micro and level >= 0 else T.BRAND
        number = f'{seconds:.1f}' if active else '—'
        text(QRectF(0, center_y-25, half, 36), number, 28, T.C_TEXT, 500)
        if active:
            p.setFont(T.ui_font(28, 500))
            x = p.fontMetrics().horizontalAdvance(number)+5
            text(QRectF(x, center_y-12, max(1,half-x), 20), _tr('秒', 's'), 12)
        bar_y = body_height-29
        track(QRectF(0, bar_y, half, 5), self.blink_progress, accent)
        last = max(1., config.NO_BLINK_ALERT_SEC+2*config.ALERT_INTERVAL_SEC)
        for i in range(3):
            value = config.NO_BLINK_ALERT_SEC+i*config.ALERT_INTERVAL_SEC
            x = half*value/last
            p.setPen(QPen(QColor(T.C_CARD), 2))
            p.drawLine(QPointF(x, bar_y), QPointF(x, bar_y+5))
            label_x = min(half-30, max(0, x-15))
            text(QRectF(label_x, bar_y+7, 30, 17), f'{value:g}s', 10, align=Qt.AlignmentFlag.AlignHCenter)

        # Arc is a frequency scale, not a progress/health percentage.
        ring = QRectF(half+24+(half-diameter)/2, center_y-diameter/2, diameter, diameter)
        value = self.rate
        scale = max(40, math.ceil((value or 0)/20)*20)
        self._ring_rect, self._ring_scale = ring, scale
        pen = QPen(QColor(T.C_SURFACE), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(ring.adjusted(5, 5, -5, -5), 225*16, -270*16)
        if value is not None and value > 0:
            pen.setColor(_color(value, 16)); p.setPen(pen)
            p.drawArc(ring.adjusted(5, 5, -5, -5), 225*16, round(-270*16*value/scale))
        text(QRectF(ring.x(), ring.center().y()-25, diameter, 36), f'{value:.1f}' if value is not None else '—', 28, T.C_TEXT, 500, Qt.AlignmentFlag.AlignHCenter)
        text(QRectF(ring.x(), ring.center().y()+9, diameter, 18), _tr('次/分', 'blinks/min') if value is not None else (_tr('采集中', 'Collecting') if active else _tr('暂无数据', 'No data')), 11, align=Qt.AlignmentFlag.AlignHCenter)
        text(QRectF(ring.center().x()-31, ring.bottom()-16, 62, 16), f'0 — {scale}', 9, T.C_TEXT3, align=Qt.AlignmentFlag.AlignHCenter)

        # Independent presence clock, never inferred from application runtime.
        y = height-49
        p.setPen(QPen(QColor(T.C_BORDER), 1)); p.drawLine(QPointF(0, y-5), QPointF(width, y-5))
        text(QRectF(0, y, half, 23), _tr('微休息', 'Microbreak'), 13, T.C_TEXT, 500)
        remaining = max(0, math.ceil((1-self.break_progress)*PRESENCE_SECONDS))
        minutes, secs = divmod(remaining, 60)
        caption = _tr(f'{minutes:02}:{secs:02} 后提醒', f'In {minutes:02}:{secs:02}')
        if micro:
            caption = _tr('休息提醒中', 'Break reminder active')
        elif self.paused:
            caption = _tr('提醒已暂停', 'Alerts paused')
        elif not self.running or not self.ready:
            caption = _tr('等待在场检测', 'Waiting for presence')
        text(QRectF(half, y, width-half, 23), caption, 12, align=Qt.AlignmentFlag.AlignRight)
        track(QRectF(0, y+28, width, 5), 1. if micro else self.break_progress, T.BRAND if micro else '#8BA18E')
        p.end()
