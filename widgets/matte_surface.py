"""Quiet background material, kept behind native text and interactive widgets."""
import random
from PyQt6.QtCore import Qt, QEvent, QRectF
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap, QPen
from PyQt6.QtWidgets import QWidget
import theme as T


class MatteSurface(QWidget):
    def __init__(self, host):
        super().__init__(host)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._host=host
        # Fixed, cached two-sided grain. It never animates or filters the text.
        grain=QImage(96,96,QImage.Format.Format_ARGB32_Premultiplied)
        grain.fill(Qt.GlobalColor.transparent)
        rng=random.Random(716)
        for y in range(96):
            for x in range(96):
                light=rng.randrange(2)==0
                grain.setPixelColor(x,y,QColor(255 if light else 42,255 if light else 66,255 if light else 51,rng.randrange(0,2)))
        self._grain=QPixmap.fromImage(grain)
        host.installEventFilter(self)
        self._fit()
        self.show();self.lower()

    def _fit(self):
        self.setGeometry(0,0,max(0,self._host.width()-1),self._host.height())

    def eventFilter(self,obj,event):
        if obj is self._host and event.type() in (QEvent.Type.Resize,QEvent.Type.Show):
            self._fit();self.lower()
        return False

    def paintEvent(self,event):
        p=QPainter(self)
        fill=QLinearGradient(0,0,self.width()*.85,self.height())
        fill.setColorAt(0,QColor(T.MATTE_TOP))
        fill.setColorAt(.48,QColor(T.S_BG))
        fill.setColorAt(1,QColor(T.MATTE_BOTTOM))
        p.fillRect(self.rect(),fill)
        p.drawTiledPixmap(self.rect(),self._grain)
        p.setPen(QPen(QColor(255,255,255,35),1))
        p.drawLine(self.width()-1,1,self.width()-1,self.height()-1)
