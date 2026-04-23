"""Top title bar with screen title, alert chip, and window controls."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
import config
from config import save_config
import theme as T
from i18n import t


class _WinBtn(QWidget):
    clicked = pyqtSignal()

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self._kind = kind   # "min" | "max" | "close"
        self._hover = False
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def enterEvent(self, e):
        self._hover = True; self.update()

    def leaveEvent(self, e):
        self._hover = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        r = 4.5

        if self._hover:
            bg = QColor(T.C_BORDER)
            p.setBrush(bg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(3, 3, W - 6, H - 6), 4, 4)

        # 图标颜色：关闭时 hover 变红，其余始终用 C_TEXT2
        if self._kind == "close" and self._hover:
            icon_c = QColor("#C05050")
        else:
            icon_c = QColor(T.C_TEXT2)

        pen = QPen(icon_c)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        if self._kind == "min":
            p.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))

        elif self._kind == "max":
            p.drawLine(int(cx - r), int(cy - r), int(cx + r), int(cy - r))
            p.drawLine(int(cx + r), int(cy - r), int(cx + r), int(cy + r))
            p.drawLine(int(cx + r), int(cy + r), int(cx - r), int(cy + r))
            p.drawLine(int(cx - r), int(cy + r), int(cx - r), int(cy - r))

        elif self._kind == "close":
            p.drawLine(int(cx - r), int(cy - r), int(cx + r), int(cy + r))
            p.drawLine(int(cx + r), int(cy - r), int(cx - r), int(cy + r))


class _Chip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = -1
        self._text = ""
        self.setFixedHeight(22)
        self.hide()

    def setAlert(self, level: int):
        self._level = level
        if level < 0:
            self.hide()
            return
        info = T.alert_levels()[level]
        self._text = info["label"]
        self.show()
        self.update()

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        w = self.fontMetrics().horizontalAdvance(self._text) + 28
        return QSize(w, 22)

    def paintEvent(self, _e):
        if self._level < 0:
            return
        info = T.alert_levels()[self._level]
        c = QColor(info["c"])
        bg = QColor(c); bg.setAlphaF(0.14)
        border = QColor(c); border.setAlphaF(0.4)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(border)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(0, 0, self.width() - 1, self.height() - 1), 11, 11)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(QRectF(9, 8.5, 5, 5))
        p.setPen(c)
        f = QFont(T.FONT_UI); f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(11); f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.drawText(QRectF(20, 0, self.width() - 24, self.height()),
                   int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                   info["label"])


class TitleBar(QFrame):
    closeClicked = pyqtSignal()
    minClicked   = pyqtSignal()
    maxClicked   = pyqtSignal()
    languageChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(42)
        self.setObjectName("TitleBar")
        self.setStyleSheet(
            f"QFrame#TitleBar{{background:{T.C_TITLEBAR};"
            f"border-bottom:1px solid {T.C_BORDER};}}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 10, 0)
        lay.setSpacing(10)

        self._title = QLabel(t("nav_monitor"))
        f = QFont(T.FONT_UI); f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(13); f.setWeight(QFont.Weight.DemiBold)
        self._title.setFont(f)
        self._title.setStyleSheet(f"color:{T.C_TEXT}; background:transparent; border:none;")
        lay.addWidget(self._title)
        lay.addStretch(1)

        self._chip = _Chip()
        lay.addWidget(self._chip)

        # 语言切换按钮
        self._lang_btn = QPushButton()
        self._lang_btn.setFixedSize(32, 24)
        self._lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_btn.clicked.connect(self._toggle_lang)
        self._refresh_lang_btn()
        lay.addWidget(self._lang_btn)

        # 窗口控制按钮
        for kind, sig_name in [("min", "minClicked"), ("max", "maxClicked"), ("close", "closeClicked")]:
            btn = _WinBtn(kind)
            btn.clicked.connect(getattr(self, sig_name))
            lay.addWidget(btn)

    def _toggle_lang(self):
        config.LANGUAGE = "en" if getattr(config, "LANGUAGE", "en") == "zh" else "zh"
        save_config()
        self._refresh_lang_btn()
        self.languageChanged.emit()

    def _refresh_lang_btn(self):
        lang = getattr(config, "LANGUAGE", "en")
        self._lang_btn.setText("EN" if lang == "en" else "CN")
        self._lang_btn.setToolTip(t("tooltip_lang_switch_zh") if lang == "en" else t("tooltip_lang_switch_en"))
        self._lang_btn.setStyleSheet(
            f"QPushButton{{background:transparent; border:1px solid {T.C_BORDER};"
            f"border-radius:5px; font-size:11px; font-weight:600;"
            f"color:{T.C_TEXT2}; padding-bottom:2px;}}"
            f"QPushButton:hover{{background:{T.C_BORDER};}}"
        )

    def setTitle(self, t: str):
        self._title.setText(t)

    def setRate(self, r: float):
        pass

    def setAlert(self, level: int):
        self._chip.setAlert(level)
