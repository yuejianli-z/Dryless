"""A small, synchronized breathing light for recognition and reminder state."""
from __future__ import annotations

import math
import time

from PyQt6.QtCore import QEvent, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QSizePolicy

import theme as T


_STATES = {"detected", "no_face", "waiting", "paused", "error", "alert_0", "alert_1", "alert_2", "alert_3"}


def _normalized(state):
    key = str(state)
    return key if key in _STATES else "waiting"


def state_color(state):
    """Return a fresh QColor, shared by the light and its adjacent text."""
    key = _normalized(state)
    if key.startswith("alert_"):
        return QColor(T.ALERT_LEVELS[min(2, int(key[-1]))]["c"])
    return QColor({
        "detected": T.SUCCESS,
        "no_face": T.WARN,
        "waiting": "#819198",
        "paused": T.C_TEXT3,
        "error": T.DANGER,
    }[key])


class StatusLight(QWidget):
    """Stable 7 px core with an 18 px maximum, gently breathing halo.

    Only the halo changes. The core stays legible at every phase. All instances
    use the same clock, so the homepage and sidebar breathe together. A paused
    reminder is a static gray light; it does not imply that detection stopped.
    """

    def __init__(self, parent=None, size=18):
        super().__init__(parent)
        extent = max(18, int(size))
        self.setFixedSize(extent, extent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;border:none;")
        self._state = "waiting"
        self._tracked_window = None
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._animate)
        self.setAccessibleName("Recognition status: waiting")

    def state(self):
        return self._state

    def color(self):
        return state_color(self._state)

    def setState(self, state):
        key = _normalized(state)
        if key == self._state:
            return
        self._state = key
        self.setAccessibleName("Reminder paused" if key == "paused" else "Recognition status: " + key.replace("_", " "))
        self._sync_timer()
        self.update()

    def _pulse(self, now=None):
        period = 2.4 if self._state.startswith("alert_") else 2.8
        phase = (time.monotonic() if now is None else now) % period / period
        return .5 - .5 * math.cos(math.tau * phase)

    def _sync_timer(self):
        visible = self.isVisible() and not self.window().isMinimized()
        should_run = visible and self._state != "paused"
        if should_run and not self._timer.isActive():
            self._timer.start()
        elif not should_run and self._timer.isActive():
            self._timer.stop()

    def _animate(self):
        self._sync_timer()
        if self._timer.isActive():
            self.update()

    def showEvent(self, event):
        super().showEvent(event)
        window = self.window()
        if window is not self._tracked_window:
            if self._tracked_window is not None:
                self._tracked_window.removeEventFilter(self)
            self._tracked_window = window
            window.installEventFilter(self)
        self._sync_timer()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def eventFilter(self, watched, event):
        if watched is self._tracked_window and event.type() in (
            QEvent.Type.WindowStateChange, QEvent.Type.Show, QEvent.Type.Hide,
        ):
            QTimer.singleShot(0, self._sync_timer)
        return super().eventFilter(watched, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        center_x, center_y = self.width() / 2, self.height() / 2
        color = self.color()
        if self._state != "paused":
            pulse = self._pulse()
            radius = 5.5 + 3.5 * pulse
            halo = QColor(color)
            halo.setAlpha(round(10 + 30 * pulse))
            painter.setBrush(halo)
            painter.drawEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
        painter.setBrush(color)
        painter.drawEllipse(QRectF(center_x - 3.5, center_y - 3.5, 7, 7))
