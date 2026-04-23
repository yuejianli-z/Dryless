"""Slider and toggle rows used on the settings screen."""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import theme as T
from .toggle import Toggle


_SLIDER_QSS = f"""
QSlider::groove:horizontal {{
    height: 3px;
    background: #E4DFD8;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {T.BRAND};
    border-radius: 2px;
    height: 3px;
}}
QSlider::handle:horizontal {{
    background: {T.BRAND};
    width: 14px; height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {T.BRAND_MID};
}}
"""


class SliderRow(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, label, hint, mn, mx, step, unit="", decimals=0, parent=None):
        super().__init__(parent)
        self._mn, self._mx, self._step = mn, mx, step
        self._unit = unit
        self._decimals = decimals

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        top = QHBoxLayout(); top.setSpacing(8)
        self._lbl = QLabel(label)
        f = QFont(T.FONT_UI); f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(13); f.setWeight(QFont.Weight.Medium)
        self._lbl.setFont(f)
        self._lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        top.addWidget(self._lbl)
        self._hint_lbl = None
        if hint:
            self._hint_lbl = QLabel(hint)
            self._hint_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:11px; background:transparent; border:none;")
            top.addWidget(self._hint_lbl)
        top.addStretch(1)

        self._val_lbl = QLabel("")
        f2 = QFont(T.FONT_UI); f2.setFamilies([T.FONT_UI] + T.FONT_FB)
        f2.setPixelSize(13); f2.setWeight(QFont.Weight.DemiBold)
        self._val_lbl.setFont(f2)
        self._val_lbl.setStyleSheet(f"color:{T.BRAND}; background:transparent; border:none;")
        top.addWidget(self._val_lbl)
        root.addLayout(top)

        # scale slider to int (step granularity)
        self._scale = 1
        if decimals:
            self._scale = 10 ** decimals
        self._sl = QSlider(Qt.Orientation.Horizontal)
        self._sl.setRange(int(mn * self._scale), int(mx * self._scale))
        self._sl.setSingleStep(int(step * self._scale))
        self._sl.setPageStep(int(step * self._scale))
        self._sl.setStyleSheet(_SLIDER_QSS)
        self._sl.valueChanged.connect(self._on_val)
        root.addWidget(self._sl)

        bot = QHBoxLayout()
        m1 = QLabel(f"{mn}{unit}")
        m2 = QLabel(f"{mx}{unit}")
        for m in (m1, m2):
            m.setStyleSheet(f"color:{T.C_TEXT3}; font-size:11px; background:transparent; border:none;")
        bot.addWidget(m1)
        bot.addStretch(1)
        bot.addWidget(m2)
        root.addLayout(bot)

    def _on_val(self, iv):
        v = iv / self._scale
        if self._decimals:
            self._val_lbl.setText(f"{v:.{self._decimals}f}{self._unit}")
        else:
            self._val_lbl.setText(f"{int(v)}{self._unit}")
        self.valueChanged.emit(float(v))

    def setValue(self, v):
        self._sl.setValue(int(v * self._scale))

    def setTexts(self, label: str, hint: str = ""):
        self._lbl.setText(label)
        if self._hint_lbl and hint:
            self._hint_lbl.setText(hint)


class ToggleRow(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, label, hint, value=True, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        left = QVBoxLayout(); left.setSpacing(2)
        self._lbl = QLabel(label)
        f = QFont(T.FONT_UI); f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(13); f.setWeight(QFont.Weight.Medium)
        self._lbl.setFont(f)
        self._lbl.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        left.addWidget(self._lbl)
        self._hint_lbl = None
        if hint:
            self._hint_lbl = QLabel(hint)
            self._hint_lbl.setStyleSheet(f"color:{T.C_TEXT3}; font-size:12px; background:transparent; border:none;")
            left.addWidget(self._hint_lbl)
        row.addLayout(left, 1)
        self._tg = Toggle(value=value)
        self._tg.toggled.connect(self.toggled)
        row.addWidget(self._tg, alignment=Qt.AlignmentFlag.AlignVCenter)

    def value(self):
        return self._tg.value()

    def setTexts(self, label: str, hint: str = ""):
        self._lbl.setText(label)
        if self._hint_lbl and hint:
            self._hint_lbl.setText(hint)
