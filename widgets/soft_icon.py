"""Small, consistent line icons on softly rounded semantic tiles."""
from functools import lru_cache
from pathlib import Path
import sys

from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QWidget
import theme as T


@lru_cache(maxsize=32)
def _brand_eye_pixmap(color, pixel_size):
    """Tint the existing logo at paint time; retain its alpha and white details."""
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    source = QImage(str(base / 'assets' / 'icons' / 'desktop-eye-transparent.png'))
    if source.isNull():
        return QPixmap()
    tinted = source.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(tinted)
    # Screen maps black ink to the brand color while leaving white highlights white.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
    painter.fillRect(tinted.rect(), QColor(color))
    # Restore the source silhouette, including its antialiased transparent edge.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, source)
    painter.end()
    # Pre-filter the large source at device resolution to avoid sparse sampling.
    scaled = tinted.scaled(pixel_size, pixel_size, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    return QPixmap.fromImage(scaled)


def _glyph(p, name):
    pen = QPen(QColor(T.ICON_FG), 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if name in ('brand_eye', 'eye'):
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pixel_size = max(1, round(20 * abs(p.deviceTransform().m11())))
        pix = _brand_eye_pixmap(T.BRAND, pixel_size)
        p.drawPixmap(QRectF(0, 0, 20, 20), pix, QRectF(pix.rect()))
    elif name == 'eye_closed':
        path = QPainterPath(); path.moveTo(2, 8)
        path.cubicTo(6, 14, 14, 14, 18, 8); p.drawPath(path)
        p.drawLine(5, 11, 3, 14); p.drawLine(10, 13, 10, 16); p.drawLine(15, 11, 17, 14)
    elif name == 'distance':
        path=QPainterPath();path.moveTo(2,15);path.lineTo(7,8);path.lineTo(10,12)
        path.lineTo(13,9);path.lineTo(18,15);p.drawPath(path);p.drawLine(2,17,18,17)
        p.drawEllipse(QRectF(12,3,4,4))
    elif name == 'globe':
        p.drawEllipse(QRectF(3,3,14,14))
        p.drawEllipse(QRectF(7,3,6,14))
        p.drawLine(3,10,17,10)
    elif name == 'clock':
        p.drawEllipse(QRectF(3, 3, 14, 14))
        p.drawLine(10, 6, 10, 10); p.drawLine(10, 10, 13, 12)
    elif name == 'calendar':
        p.drawRoundedRect(QRectF(3, 4, 14, 13), 2, 2)
        p.drawLine(3, 8, 17, 8); p.drawLine(7, 2, 7, 6); p.drawLine(13, 2, 13, 6)
        p.drawLine(7, 11, 9, 11); p.drawLine(12, 11, 14, 11)
        p.drawLine(7, 14, 9, 14)
    elif name in ('chart', 'activity'):
        if name == 'chart':
            for x, y in ((4,12),(9,8),(14,4)):
                p.drawRoundedRect(QRectF(x, y, 2.5, 17-y), 1, 1)
        else:
            path=QPainterPath();path.moveTo(2,11);path.lineTo(6,11);path.lineTo(8,5)
            path.lineTo(12,15);path.lineTo(14,9);path.lineTo(18,9);p.drawPath(path)
    elif name == 'camera':
        p.drawRoundedRect(QRectF(2, 6, 16, 11), 2, 2)
        p.drawEllipse(QRectF(7, 8.5, 6, 6))
        p.drawLine(5, 6, 7, 3);p.drawLine(7, 3, 13, 3);p.drawLine(13, 3, 15, 6)
    elif name == 'bell':
        path=QPainterPath();path.moveTo(4,14);path.lineTo(5,12);path.lineTo(5,8)
        path.cubicTo(5,2,15,2,15,8);path.lineTo(15,12);path.lineTo(16,14)
        path.closeSubpath();p.drawPath(path);p.drawArc(QRectF(8,13,4,5),180*16,180*16)
    elif name == 'sound':
        path=QPainterPath();path.moveTo(3,8);path.lineTo(6,8);path.lineTo(10,5)
        path.lineTo(10,15);path.lineTo(6,12);path.lineTo(3,12);path.closeSubpath();p.drawPath(path)
        p.drawArc(QRectF(10,6,6,8),-60*16,120*16)
    else:
        for y, x in ((5,8),(10,13),(15,6)):
            p.drawLine(3,y,17,y)
            p.setBrush(QColor(T.ICON_BG));p.drawEllipse(QRectF(x-2,y-2,4,4));p.setBrush(Qt.BrushStyle.NoBrush)


def _paint(p, name, size, glyph_size, tile):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if tile:
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(T.ICON_BG))
        p.drawRoundedRect(QRectF(0, 0, size, size), min(8, size/3), min(8, size/3))
    p.save();p.translate((size-glyph_size)/2,(size-glyph_size)/2)
    p.scale(glyph_size/20,glyph_size/20);_glyph(p,name);p.restore()


def icon(name, size=16, tile=False):
    pix=QPixmap(size*2,size*2);pix.setDevicePixelRatio(2);pix.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pix);_paint(painter,name,size,round(size*.62) if tile else size,tile);painter.end()
    return QIcon(pix)


class SoftIcon(QWidget):
    def __init__(self, name, size=26, glyph_size=15, parent=None):
        super().__init__(parent)
        self._name=name;self._size=size;self._glyph_size=glyph_size
        self.setFixedSize(size,size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAccessibleName('')

    def paintEvent(self, event):
        p=QPainter(self);_paint(p,self._name,self._size,self._glyph_size,True)
