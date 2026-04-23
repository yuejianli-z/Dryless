"""iOS-style toggle switch."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, pyqtSignal, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QBrush
import theme as T


class Toggle(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, value=False, small=False, parent=None):
        super().__init__(parent)
        self._value = value
        self._small = small
        self._w = 30 if small else 34
        self._h = 17 if small else 19
        self._knob = (self._w - self._h + 2) if value else 2
        self.setFixedSize(self._w, self._h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def value(self):
        return self._value

    def setValue(self, v: bool, emit=True):
        v = bool(v)
        if v == self._value:
            return
        self._value = v
        self._anim.stop()
        self._anim.setStartValue(self._knob)
        self._anim.setEndValue((self._w - self._h + 2) if v else 2)
        self._anim.start()
        if emit:
            self.toggled.emit(v)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.setValue(not self._value)

    def _get_knob(self):
        return self._knob

    def _set_knob(self, v):
        self._knob = v
        self.update()

    knob = pyqtProperty(int, fget=_get_knob, fset=_set_knob)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(T.BRAND) if self._value else QColor("#D0CBC3")
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self._w, self._h, self._h / 2, self._h / 2)
        # knob
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(self._knob, 2, self._h - 4, self._h - 4)
