"""
Camera preview widget with live frames and overlay decorations.

Modes:
- Live frame mode renders the current QImage with overlays.
- Fallback mode renders a placeholder when no face is detected.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QImage, QPixmap, QFont, QPainterPath,
    QRadialGradient,
)
import theme as T
from i18n import t


class CameraView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self._frame = None        # QImage
        self._face = False
        self._eye_open = True
        self._error: str | None = None

    def setFrame(self, img: QImage):
        self._error = None
        self._frame = img
        self.update()

    def setStatus(self, face_detected: bool, eye_open: bool):
        self._face = bool(face_detected)
        self._eye_open = bool(eye_open)
        self.update()

    def setError(self, msg: str):
        self._error = msg
        self._frame = None
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # rounded clip
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, W, H), 9, 9)
        p.setClipPath(path)

        # bg
        grad = QRadialGradient(W / 2, H * 0.42, max(W, H))
        grad.setColorAt(0.0, QColor("#25242A"))
        grad.setColorAt(1.0, QColor("#101014"))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, W, H)

        # frame (cover-fit into rect)
        if self._frame is not None and not self._frame.isNull():
            pix = QPixmap.fromImage(self._frame)
            scaled = pix.scaled(W, H,
                                 Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                 Qt.TransformationMode.SmoothTransformation)
            ox = (scaled.width() - W) // 2
            oy = (scaled.height() - H) // 2
            p.drawPixmap(-ox, -oy, scaled)
        else:
            f = QFont(T.FONT_UI)
            f.setFamilies([T.FONT_UI] + T.FONT_FB)
            f.setPixelSize(12)
            p.setFont(f)
            if self._error:
                p.setPen(QColor("#C05858"))
                p.drawText(QRectF(12, H / 2 - 24, W - 24, 48),
                           int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                           f"⚠ {self._error}")
            else:
                p.setPen(QColor("#444450"))
                p.drawText(QRectF(0, H / 2 - 10, W, 20),
                           Qt.AlignmentFlag.AlignCenter, t("no_face"))
        # detection badge (top-left)
        if self._face:
            ec = QColor("#5ABF88") if self._eye_open else QColor("#C05858")
            badge_bg = QColor(ec)
            badge_bg.setAlphaF(0.18)
            p.setBrush(badge_bg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(10, 10, 78, 18), 4, 4)
            p.setBrush(ec)
            p.drawEllipse(QRectF(18, 15, 8, 8))
            p.setPen(ec)
            f = QFont(T.FONT_MONO)
            f.setPixelSize(9)
            f.setWeight(QFont.Weight.Medium)
            p.setFont(f)
            p.drawText(QRectF(30, 10, 60, 18),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                       "DETECTED")

        # corner brackets
        brand = QColor(T.BRAND)
        brand.setAlphaF(0.55)
        pen = QPen(brand)
        pen.setWidthF(1.6)
        p.setPen(pen)
        L = 12
        # 4 corners
        for cx, cy, dx1, dy1, dx2, dy2 in [
            (7, 7, L, 0, 0, L),
            (W - 7, 7, -L, 0, 0, L),
            (7, H - 7, L, 0, 0, -L),
            (W - 7, H - 7, -L, 0, 0, -L),
        ]:
            p.drawLine(int(cx), int(cy), int(cx + dx1), int(cy + dy1))
            p.drawLine(int(cx), int(cy), int(cx + dx2), int(cy + dy2))

        # footer tag
        p.setPen(QColor("#505058"))
        f = QFont(T.FONT_MONO)
        f.setPixelSize(8)
        p.setFont(f)
        p.drawText(QRectF(W - 120, H - 16, 110, 14),
                   int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                   "CAM0 · 640×480")
