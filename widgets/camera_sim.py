"""Live camera surface and a container whose frame follows the source aspect ratio."""
import math
from fractions import Fraction

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QImage, QFont, QPainterPath

import theme as T
from i18n import t


class AspectRatioHost(QWidget):
    """Fit a child surface to the source ratio without expanding or cropping it.

    The host occupies the layout's available space, while the actual camera/stack
    rectangle uses only the fitted source bounds. Unused space belongs to the
    surrounding page, rather than to a letterboxed camera frame.
    """

    def __init__(self, content, parent=None, ratio=4 / 3,
                 alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop):
        super().__init__(parent)
        self.content = content
        self.content.setParent(self)
        self.content.setMinimumSize(0, 0)
        self.content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._ratio = 4 / 3
        self._alignment = alignment
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAspectRatio(ratio)

    def aspectRatio(self):
        return self._ratio

    def setAspectRatio(self, ratio):
        ratio = float(ratio)
        if not math.isfinite(ratio) or ratio <= 0:
            return
        self._ratio = ratio
        self._fit_content()
        self.updateGeometry()

    def setAlignment(self, alignment):
        self._alignment = alignment
        self._fit_content()

    def sizeHint(self):
        return QSize(480, round(480 / self._ratio))

    def minimumSizeHint(self):
        return QSize(0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_content()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_content()

    def _fit_content(self):
        area = self.contentsRect()
        available_width, available_height = area.width(), area.height()
        if available_width <= 0 or available_height <= 0:
            self.content.setGeometry(area.x(), area.y(), 0, 0)
            return
        # Whole aspect units keep common sources exactly proportional in integer
        # QWidget coordinates (4:3, 16:9, 9:16), with at most one unit unused.
        fraction = Fraction(self._ratio).limit_denominator(1000)
        unit_width, unit_height = fraction.numerator, fraction.denominator
        units = min(available_width // unit_width, available_height // unit_height)
        if units:
            width, height = units * unit_width, units * unit_height
        else:
            # Very small viewports or unusual source ratios need pixel rounding.
            width = min(available_width, max(1, round(available_height * self._ratio)))
            height = min(available_height, max(1, round(width / self._ratio)))
        x, y = area.x(), area.y()
        if self._alignment & Qt.AlignmentFlag.AlignHCenter:
            x += (available_width - width) // 2
        elif self._alignment & Qt.AlignmentFlag.AlignRight:
            x += available_width - width
        if self._alignment & Qt.AlignmentFlag.AlignVCenter:
            y += (available_height - height) // 2
        elif self._alignment & Qt.AlignmentFlag.AlignBottom:
            y += available_height - height
        self.content.setGeometry(x, y, width, height)


class CameraView(QWidget):
    frameAspectRatioChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(0, 0)
        self._frame = None
        self._frame_ratio = 4 / 3
        self._face = False
        self._eye_open = True
        self._error = None

    def sizeHint(self):
        return QSize(480, round(480 / self._frame_ratio))

    def minimumSizeHint(self):
        return QSize(0, 0)

    def frameAspectRatio(self):
        return self._frame_ratio

    def setFrame(self, img: QImage):
        self._error = None
        self.setAccessibleDescription("")
        self._frame = img if img is not None and not img.isNull() else None
        if self._frame is not None:
            ratio = self._frame.width() / self._frame.height()
            if not math.isclose(ratio, self._frame_ratio, rel_tol=1e-9):
                self._frame_ratio = ratio
                self.frameAspectRatioChanged.emit(ratio)
                self.updateGeometry()
        self.update()

    def setStatus(self, face_detected: bool, eye_open: bool):
        self._face = bool(face_detected)
        self._eye_open = bool(eye_open)
        self.update()

    def setError(self, msg: str):
        self._error = msg
        self.setAccessibleDescription(str(msg))
        self._frame = None
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        bounds = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(bounds, 14, 14)
        painter.setClipPath(clip)
        if self._frame is not None:
            # AspectRatioHost sizes this surface to the source image. Paint the
            # complete frame directly into that matching rectangle, without any
            # independently fitted inner image, crop, or letterbox background.
            painter.drawImage(bounds, self._frame, QRectF(self._frame.rect()))
            return
        painter.fillRect(bounds, QColor(T.C_SURFACE))
        font = T.ui_font()
        font.setFamilies([T.FONT_UI] + T.FONT_FB)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(QColor(T.DANGER if self._error else T.C_TEXT2))
        painter.drawText(
            bounds.adjusted(16, 12, -16, -12),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            t("camera_unavailable") if self._error else t("camera_pending"),
        )
