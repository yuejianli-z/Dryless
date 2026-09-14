"""Rounded native window boundary without rendering the content into an effect.

Call ``apply_window_shape(window, 18)`` once before its first ``show()``.
The corner overlay only removes corner pixels from Qt's shared backing store;
labels and controls retain their original native rendering and hit areas.
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QRegion
from PyQt6.QtWidgets import QWidget


class _CornerCutout(QWidget):
    def __init__(self, window, radius):
        super().__init__(window)
        self.radius = float(radius)
        self.setObjectName("WindowCornerCutout")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, _event):
        if self.radius <= 0:
            return
        bounds = QRectF(self.rect())
        radius = min(self.radius, bounds.width() / 2, bounds.height() / 2)
        outside = QPainterPath()
        outside.setFillRule(Qt.FillRule.OddEvenFill)
        outside.addRect(bounds)
        outside.addRoundedRect(bounds, radius, radius)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        painter.fillPath(outside, QColor(0, 0, 0, 255))


class _WindowShape(QObject):
    def __init__(self, window, radius):
        super().__init__(window)
        self.window = window
        self.radius = float(radius)
        self.overlay = _CornerCutout(window, self.radius)
        self._syncing = False
        window.installEventFilter(self)
        self.sync()

    def sync(self):
        if self._syncing:
            return
        self._syncing = True
        try:
            rect = self.window.rect()
            self.overlay.radius = self.radius
            self.overlay.setGeometry(rect)
            # Keep the integer native hit region just outside the antialiased
            # visible edge. It never clips the overlay's fractional alpha edge.
            path = QPainterPath()
            radius = max(0.0, min(self.radius, rect.width()/2, rect.height()/2)-1.5)
            path.addRoundedRect(QRectF(rect), radius, radius)
            self.window.setMask(QRegion(path.toFillPolygon().toPolygon()))
            self.overlay.raise_()
            self.overlay.show()
            self.overlay.update()
        finally:
            self._syncing = False

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() in (
            QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.WindowStateChange,
            QEvent.Type.WinIdChange, QEvent.Type.DevicePixelRatioChange,
        ):
            self.sync()
        return False


def apply_window_shape(window: QWidget, radius: float = 18) -> QObject:
    """Install/update a logical-pixel corner radius, including maximized mode.

    Invoke before the native window is first shown so Windows creates a layered
    surface with transparent corners. No widget sizes or layouts are changed.
    """
    radius = max(0.0, float(radius))
    controller = getattr(window, "_dryless_window_shape", None)
    if controller is None:
        window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        window.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        controller = _WindowShape(window, radius)
        window._dryless_window_shape = controller
    else:
        controller.radius = radius
        controller.sync()
    return controller
