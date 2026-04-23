"""Dark sidebar with branding, navigation, and footer status."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QFont
import theme as T
from .toggle import Toggle
from i18n import t


def _icon(name: str, active: bool) -> QPixmap:
    """生成 18×18 线性图标（monitor/stats/settings）。"""
    pix = QPixmap(18, 18)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(T.BRAND) if active else QColor(255, 255, 255, 115)
    pen = QPen(c)
    pen.setWidthF(1.4)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if name == "monitor":
        p.drawEllipse(QRectF(1, 4, 16, 10))
        p.setBrush(c)
        p.drawEllipse(QRectF(6.5, 6.5, 5, 5))
    elif name == "stats":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(2, 10, 3, 5), 1, 1)
        p.drawRoundedRect(QRectF(7.5, 7, 3, 8), 1, 1)
        p.drawRoundedRect(QRectF(13, 4, 3, 11), 1, 1)
    elif name == "settings":
        p.drawEllipse(QRectF(6, 6, 6, 6))
        for (x1, y1, x2, y2) in [
            (9, 1.5, 9, 3.5), (9, 14.5, 9, 16.5),
            (1.5, 9, 3.5, 9), (14.5, 9, 16.5, 9),
        ]:
            p.drawLine(int(x1), int(y1), int(x2), int(y2))
    p.end()
    return pix


class _NavButton(QPushButton):
    def __init__(self, name, label, parent=None):
        super().__init__(parent)
        self._name = name
        self._active = False
        self._label = label
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setIconSize(QSize(16, 16))
        self._refresh()

    def setActive(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._refresh()

    def _refresh(self):
        self.setIcon(QIcon(_icon(self._name, self._active)))
        self.setText(f"  {self._label}")
        bg = T.S_ACTIVE if self._active else "transparent"
        text = "#F2EFE9" if self._active else T.S_TEXT_DIM
        weight = 600 if self._active else 400
        self.setStyleSheet(
            f"QPushButton{{"
            f"  background:{bg};"
            f"  border:none; border-radius:7px;"
            f"  text-align:left; padding-left:10px;"
            f"  color:{text}; font-size:13px; font-weight:{weight};"
            f"}}"
            f"QPushButton:hover{{background:{T.S_HOVER};}}"
        )


class Sidebar(QWidget):
    navChanged = pyqtSignal(str)
    closeClicked = pyqtSignal()
    minClicked = pyqtSignal()
    maxClicked = pyqtSignal()
    soundToggled = pyqtSignal(bool)

    NAV = [("monitor", "nav_monitor"), ("stats", "nav_stats"), ("settings", "nav_settings")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(190)
        self.setObjectName("Sidebar")
        self.setStyleSheet(
            f"QWidget#Sidebar{{background:{T.S_BG}; border-right:1px solid {T.S_BORDER};}}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Logo / identity
        idt = QWidget(self)
        idt.setObjectName("SidebarIdent")
        idt.setStyleSheet(
            f"QWidget#SidebarIdent{{background:{T.S_BG};"
            f"border-bottom:1px solid {T.S_BORDER};}}"
        )
        idt_lay = QVBoxLayout(idt)
        idt_lay.setContentsMargins(18, 28, 18, 28)
        idt_lay.setSpacing(7)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        logo = QLabel("")
        logo.setPixmap(_eye_logo())
        logo.setFixedSize(22, 22)
        row.addWidget(logo)
        self._title_lbl = QLabel(t("app_name"))
        f = QFont(T.FONT_UI); f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(17); f.setWeight(QFont.Weight.Bold)
        self._title_lbl.setFont(f)
        self._title_lbl.setStyleSheet(f"color:{T.S_TEXT}; background:transparent; border:none;")
        row.addWidget(self._title_lbl)
        row.addStretch(1)
        idt_lay.addLayout(row)

        self._subtitle_lbl = QLabel(t("subtitle"))
        self._subtitle_lbl.setObjectName("SidebarSubtitle")
        self._subtitle_lbl.setStyleSheet(f"color:{T.S_TEXT_DIM}; font-size:12px; padding-left:32px; background:transparent; border:none;")
        idt_lay.addWidget(self._subtitle_lbl)
        root.addWidget(idt)

        # Nav area
        nav = QWidget(self)
        nav.setObjectName("SidebarNav")
        nav.setStyleSheet(f"QWidget#SidebarNav{{background:{T.S_BG};}}")
        nav_lay = QVBoxLayout(nav)
        nav_lay.setContentsMargins(8, 12, 8, 8)
        nav_lay.setSpacing(2)

        self._menu_lbl = QLabel(t("main_menu"))
        self._menu_lbl.setStyleSheet(
            f"color:{T.S_TEXT_DIM}; font-size:10px; letter-spacing:1px; background:transparent; border:none;"
            f"padding:0 10px 8px 10px; font-weight:500;"
        )
        nav_lay.addWidget(self._menu_lbl)

        self._buttons = {}
        for name, label_key in self.NAV:
            btn = _NavButton(name, t(label_key))
            btn.clicked.connect(lambda _c=False, n=name: self._select(n))
            nav_lay.addWidget(btn)
            self._buttons[name] = btn

        nav_lay.addStretch(1)
        root.addWidget(nav, 1)

        # Bottom status
        bot = QWidget(self)
        bot.setObjectName("SidebarBot")
        bot.setStyleSheet(
            f"QWidget#SidebarBot{{background:{T.S_BG};"
            f"border-top:1px solid {T.S_BORDER};}}"
        )
        bot_lay = QVBoxLayout(bot)
        bot_lay.setContentsMargins(14, 12, 14, 14)
        bot_lay.setSpacing(8)

        face_row = QHBoxLayout(); face_row.setSpacing(7)
        self._face_dot = QLabel("●")
        self._face_dot.setStyleSheet(f"color:{T.BRAND}; font-size:12px; background:transparent; border:none;")
        face_row.addWidget(self._face_dot)
        self._face_label = QLabel(t("face_locked"))
        self._face_label.setStyleSheet(f"color:{T.S_TEXT_DIM}; font-size:11px; background:transparent; border:none;")
        face_row.addWidget(self._face_label)
        face_row.addStretch(1)
        bot_lay.addLayout(face_row)

        self._session_lbl = QLabel(t("session_usage", t="0m"))
        self._session_lbl.setStyleSheet(f"color:{T.S_TEXT_DIM}; font-size:11px; background:transparent; border:none;")
        bot_lay.addWidget(self._session_lbl)

        sound_row = QHBoxLayout(); sound_row.setSpacing(0)
        self._sound_lbl = QLabel(t("sound_toggle"))
        self._sound_lbl.setStyleSheet(f"color:{T.S_TEXT_DIM}; font-size:10.5px; background:transparent; border:none;")
        sound_row.addWidget(self._sound_lbl)
        sound_row.addStretch(1)
        self._sound = Toggle(value=True, small=True)
        self._sound.toggled.connect(self.soundToggled)
        sound_row.addWidget(self._sound)
        bot_lay.addLayout(sound_row)

        root.addWidget(bot)

        self.setActive("monitor")

    # ── API ───────────────────────────────────────────────
    def setActive(self, name: str):
        for k, b in self._buttons.items():
            b.setActive(k == name)

    def _select(self, name: str):
        self.setActive(name)
        self.navChanged.emit(name)

    def setFace(self, detected: bool):
        if detected:
            self._face_dot.setStyleSheet(f"color:{T.BRAND}; font-size:12px; background:transparent; border:none;")
            self._face_label.setText(t("face_locked"))
        else:
            self._face_dot.setStyleSheet(f"color:{T.WARN}; font-size:12px; background:transparent; border:none;")
            self._face_label.setText(t("face_none"))

    def setSession(self, text: str):
        self._session_lbl.setText(t("session_usage", t=text))

    def soundValue(self):
        return self._sound.value()

    def setSoundValue(self, v):
        self._sound.setValue(v, emit=False)

    def retranslate(self):
        """Update all labels to current language."""
        self._title_lbl.setText(t("app_name"))
        self._subtitle_lbl.setText(t("subtitle"))
        self._menu_lbl.setText(t("main_menu"))
        for name, label_key in self.NAV:
            self._buttons[name]._label = t(label_key)
            self._buttons[name]._refresh()
        self._face_label.setText(t("face_locked"))
        self._sound_lbl.setText(t("sound_toggle"))


def _eye_logo() -> QPixmap:
    pix = QPixmap(18, 18)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(T.BRAND))
    pen.setWidthF(1.2)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(1.5, 4.5, 15, 9))
    p.setBrush(QColor(T.BRAND))
    p.drawEllipse(QRectF(6.5, 6.5, 5, 5))
    p.setBrush(QColor("#FFFFFF"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(8, 8, 2, 2))
    p.end()
    return pix
