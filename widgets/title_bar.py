"""Top title bar with screen title, alert chip, and window controls."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QStackedWidget, QPushButton, QStyleOptionButton, QStyle, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QActionGroup, QFontMetrics, QFontMetrics
import config
from config import save_config
import theme as T
from i18n import t, _STRINGS, _STRINGS
from widgets.soft_icon import icon
from widgets.selection_popup import build_menu


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
        font = T.ui_font()
        font.setFamilies([T.FONT_UI] + T.FONT_FB)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Normal)
        metrics = QFontMetrics(font)
        labels = [_STRINGS[lang][f"alert_l{level}"] for lang in ("zh", "en") for level in range(3)]
        self._stable_width = max(metrics.horizontalAdvance(label) for label in labels) + 30
        self.setFixedSize(self._stable_width, 22)
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
        return QSize(self._stable_width, 22)

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
        f = T.ui_font(); f.setFamilies([T.FONT_UI] + T.FONT_FB)
        f.setPixelSize(11); f.setWeight(QFont.Weight.Normal)
        p.setFont(f)
        p.drawText(QRectF(20, 0, self.width() - 24, self.height()),
                   int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                   info["label"])


class _LanguageButton(QPushButton):
    """Quiet title-bar control with one antialiased rounded boundary."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._keyboard_focus = False

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() in (
            Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason,
            Qt.FocusReason.ShortcutFocusReason)
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        focused = self.hasFocus() and self._keyboard_focus
        fill = T.BRAND_SOFT if self.isDown() else (T.C_SURFACE if self.underMouse() else T.C_CARD)
        painter.setBrush(QColor(fill))
        painter.setPen(QPen(QColor(T.CONTROL_FOCUS), 1) if focused else QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), T.R_SM, T.R_SM)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.state &= ~QStyle.StateFlag.State_HasFocus
        self.style().drawControl(QStyle.ControlElement.CE_PushButtonLabel, option, painter, self)


class TitleBar(QFrame):
    closeClicked = pyqtSignal()
    minClicked   = pyqtSignal()
    maxClicked   = pyqtSignal()
    languageChanged = pyqtSignal()
    cameraToggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setObjectName("TitleBar")
        self.setStyleSheet("QFrame#TitleBar{background:transparent;border:none;}")
        header_layout = QHBoxLayout(self)
        header_layout.setContentsMargins(24, 18, 10, 18)
        header_layout.setSpacing(12)
        self._page_headers = QStackedWidget()
        self._page_headers.setFixedHeight(36)
        self._page_headers.setStyleSheet("QStackedWidget{background:transparent;border:none;}")
        header_layout.addWidget(self._page_headers, 1)
        self._controls = QWidget()
        self._controls.setFixedHeight(36)
        lay = QHBoxLayout(self._controls)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        header_layout.addWidget(self._controls)

        self._chip = _Chip(self)
        self._chip.hide()  # Current alerts already have a status and reminder strip.
        self._control_layout = lay

        self._camera_btn = QPushButton()
        self._camera_btn.setFont(T.ui_font(T.TYPE_CONTROL, 500))
        self._camera_btn.setFixedSize(148, 34)
        self._camera_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._camera_btn.clicked.connect(self.cameraToggled.emit)
        lay.addWidget(self._camera_btn)
        self.setCameraState("off")

        # 语言切换按钮
        self._lang_btn = _LanguageButton()
        self._lang_btn.setFixedHeight(28)
        language_font = T.ui_font()
        language_font.setFamilies([T.FONT_UI] + T.FONT_FB)
        language_font.setPixelSize(11)
        language_font.setWeight(QFont.Weight.Medium)
        self._lang_btn.setFont(language_font)
        self._lang_btn.setIcon(icon("globe", size=16))
        self._lang_btn.setIconSize(QSize(16, 16))
        self._language_menu = None
        self._language_actions = {}
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
        """Compatibility entry point: open choices without changing language."""
        self._open_language_menu()

    def _open_language_menu(self):
        if self._language_menu is None:
            menu_font = T.ui_font()
            menu_font.setFamilies([T.FONT_UI] + T.FONT_FB)
            menu_font.setPixelSize(13)
            menu_font.setWeight(QFont.Weight.Normal)
            self._language_menu = build_menu(self, font=menu_font)
            self._language_menu.setMinimumWidth(170)
            self._language_menu.aboutToShow.connect(lambda: self._lang_btn.setDown(True))
            self._language_menu.aboutToHide.connect(lambda: self._lang_btn.setDown(False))
            self._language_menu.setAccessibleName("语言 / Language")
            self._language_group = QActionGroup(self._language_menu)
            self._language_group.setExclusive(True)
            for language, label in (("zh", "简体中文"), ("en", "English")):
                action = self._language_menu.addAction(label)
                action.setCheckable(True)
                self._language_group.addAction(action)
                action.triggered.connect(lambda _checked=False, value=language: self._set_language(value))
                self._language_actions[language] = action
        self._refresh_lang_btn()
        if self._language_menu.isVisible():
            self._language_menu.hide()
            return
        self._language_menu.popup_below(self._lang_btn)

    def _set_language(self, language):
        if language not in ("zh", "en"):
            return
        current = "zh" if str(getattr(config, "LANGUAGE", "en")).lower().startswith("zh") else "en"
        if language == current:
            self._refresh_lang_btn()
            return
        config.LANGUAGE = language
        save_config()
        self._refresh_lang_btn()
        self.languageChanged.emit()

    def _refresh_lang_btn(self):
        lang = "zh" if str(getattr(config, "LANGUAGE", "en")).lower().startswith("zh") else "en"
        label = "Language"
        self._lang_btn.setText(label)
        self._lang_btn.setToolTip("")
        self._lang_btn.setAccessibleName("界面语言：简体中文" if lang == "zh" else "Interface language: English")
        self._lang_btn.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;outline:none;"
            f"border-radius:8px;font-size:11px;font-weight:500;"
            f"color:{T.C_TEXT2};padding:2px 6px;text-align:center;}}"

        )
        self._lang_btn.setFixedWidth(92)
        for language, action in self._language_actions.items():
            action.setChecked(language == lang)
        if self._chip._level >= 0:
            self._chip.setAlert(self._chip._level)
            self._chip.updateGeometry()

    def setSoundControl(self, button):
        self._sound_btn = button
        self._control_layout.insertWidget(1, button)
        button.setFixedSize(148, 34)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(self._control_style())
        button.setToolTip("")
        button.show()

    def setCameraState(self, state):
        zh = config.LANGUAGE == "zh"
        labels = {
            "off": ("摄像头：关", "Camera: off"),
            "starting": ("摄像头：启动中", "Camera: starting"),
            "running": ("摄像头：开", "Camera: on"),
            "stopping": ("摄像头：关闭中", "Camera: stopping"),
            "error": ("摄像头：故障", "Camera: error"),
        }
        self._camera_btn.setText(labels[state][0 if zh else 1])
        self._camera_btn.setAccessibleName(self._camera_btn.text())
        self._camera_btn.setAccessibleDescription(("点击切换；启动中点击可取消。" if zh else "Click to toggle; click during startup to cancel."))
        self._camera_btn.setEnabled(state != "stopping")
        self._camera_btn.setToolTip("")
        self._camera_btn.setStyleSheet(self._control_style())

    @staticmethod
    def _control_style():
        return (f"QPushButton{{background:{T.C_CARD};color:{T.C_TEXT};border:1px solid {T.C_BORDER};"
                "border-radius:8px;padding:4px 8px;text-align:center;}"
                f"QPushButton:hover{{background:{T.C_SURFACE};}}"
                f"QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}"
                f"QPushButton:disabled{{color:{T.C_TEXT3};background:{T.C_SURFACE};}}")

    def setPageHeader(self, header):
        if self._page_headers.indexOf(header) < 0:
            self._page_headers.addWidget(header)
        self._page_headers.setCurrentWidget(header)

    def setRate(self, r: float):
        pass

    def setAlert(self, level: int):
        self._chip.setAlert(-1)
