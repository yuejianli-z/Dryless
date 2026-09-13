"""Compact native settings with a live reminder-rule summary."""
import math

import math

from PyQt6.QtCore import Qt, QRectF, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QLineEdit, QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QCheckBox, QSizePolicy, QStackedWidget,
)

import config
import theme as T
from config import save_config
from widgets import Card
from widgets.soft_icon import SoftIcon, icon


class _CaretEditor(QLineEdit):
    """A numeric editor with a caret and no text-selection rendering."""
    def selectAll(self):
        self.deselect()

    def paintEvent(self, event):
        self.deselect()
        super().paintEvent(event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.deselect()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.deselect()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.deselect()


class _StepInteraction:
    """Numeric editing uses a caret; stepping never leaves selected text."""
    def validate(self, text, position):
        from PyQt6.QtGui import QValidator
        import re
        result = super().validate(text, position)
        if result[0] == QValidator.State.Invalid:
            candidate = text
            if self.suffix() and candidate.endswith(self.suffix()):
                candidate = candidate[:-len(self.suffix())]
            candidate = candidate.strip()
            pattern = r"[+-]?\d*(?:\.\d{0,2})?" if isinstance(self, QDoubleSpinBox) else r"[+-]?\d*"
            if re.fullmatch(pattern, candidate):
                # Permit temporary out-of-range text while deleting/retyping.
                # The spinbox applies its range when the edit is committed.
                return QValidator.State.Intermediate, text, position
        return result

    def stepBy(self, steps):
        super().stepBy(steps)
        self.lineEdit().deselect()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.lineEdit().deselect()


class _IntegerInput(_StepInteraction, QSpinBox):
    pass


class _DecimalInput(_StepInteraction, QDoubleSpinBox):
    pass


def _tr(zh, en):
    return zh if getattr(config, "LANGUAGE", "en") == "zh" else en


def _font(size, weight=400):
    font = T.ui_font()
    font.setFamilies([T.FONT_UI] + T.FONT_FB)
    font.setPixelSize(size)
    font.setWeight({
        400: QFont.Weight.Normal, 500: QFont.Weight.Medium,
        600: QFont.Weight.DemiBold, 700: QFont.Weight.Bold,
    }.get(weight, QFont.Weight.Normal))
    return font


def _label(text="", size=T.TYPE_BODY, color=None, weight=400, wrap=False):
    label = QLabel(text)
    label.setFont(_font(size, weight))
    # Reserve the CJK/Latin line envelope, independent of the selected text.
    label.setFixedHeight(math.ceil(size * 1.5))
    # Reserve the CJK/Latin line envelope, independent of the selected text.
    label.setFixedHeight(math.ceil(size * 1.5))
    label.setStyleSheet(
        f"color:{color or T.C_TEXT}; background:transparent; border:none;"
    )
    label.setWordWrap(wrap)
    if wrap:
        label.setMinimumWidth(0)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return label


def _button_style():
    return (
        f"QPushButton{{background:{T.C_CARD};color:{T.C_TEXT};border:1px solid {T.C_BORDER};"
        f"border-radius:{T.R_SM}px;padding:5px 10px;font-size:{T.TYPE_CONTROL}px;font-weight:400;}}"
        f"QPushButton:hover{{background:{T.C_SURFACE};border-color:{T.S_ACTIVE};}}"
        f"QPushButton:checked{{background:{T.BRAND_SOFT};color:{T.BRAND_MID};border-color:{T.S_ACTIVE};}}"
        f"QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}"
        f"QPushButton:disabled{{color:{T.C_TEXT3};background:{T.C_SURFACE};}}"
    )


class _Switch(QCheckBox):
    """A painted switch retaining native checkbox keyboard/accessibility behavior."""

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 26)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def hitButton(self, point):
        return self.rect().contains(point)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(T.BRAND_MID if self.isChecked() else T.S_ACTIVE))
        painter.drawRoundedRect(QRectF(0, 3, 40, 20), 10, 10)
        painter.setBrush(QColor(T.C_CARD))
        painter.drawEllipse(QRectF(23 if self.isChecked() else 3, 6, 14, 14))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(T.BRAND_MID), 1))
            painter.drawRoundedRect(QRectF(0.5, 0.5, 39, 25), 11, 11)


class SettingsScreen(QWidget):
    soundPreviewFailed = pyqtSignal(str)
    previewStage = pyqtSignal(int, int)
    previewFinished = pyqtSignal(int)
    soundToggled = pyqtSignal(bool)
    languageChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._copy = []
        self._steppers = []
        self._preview_token = None
        self._preview_stage = 0
        self._preview_error = False
        self._res = f"{config.CAMERA_WIDTH}×{config.CAMERA_HEIGHT}"
        self._advanced_open = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)
        self.page_header = QWidget(self)
        self.page_header.setFixedHeight(36)
        heading = QHBoxLayout(self.page_header)
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(10)
        heading.addWidget(SoftIcon("settings", size=26, glyph_size=15), alignment=Qt.AlignmentFlag.AlignVCenter)
        title = _label(size=24, weight=600)
        self._bind(title, "设置", "Settings")
        heading.addWidget(title)
        heading.addStretch(1)
        self._local_note = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
        self._bind(self._local_note, "更改自动保存", "Changes saved automatically")
        self._local_note.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._local_note.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        heading.addWidget(self._local_note, alignment=Qt.AlignmentFlag.AlignVCenter)

        tab_bar = QFrame()
        tab_bar.setObjectName("SettingsTabs")
        tab_bar.setStyleSheet(f"QFrame#SettingsTabs{{background:{T.C_SURFACE};border:none;border-radius:12px;}}")
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)
        self._tabs = []
        self._tab_stack = QStackedWidget()
        self._tab_stack.setStyleSheet("QStackedWidget{background:transparent;border:none;}")
        for index, (zh, en) in enumerate((("提醒", "Reminders"), ("设备与语言", "Device and language"), ("高级检测", "Advanced detection"))):
            button = QPushButton()
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(36)
            button.setIcon(icon(("bell", "camera", "settings")[index], size=16))
            button.setIconSize(QSize(16, 16))
            button.setStyleSheet(
                f"QPushButton{{background:transparent;color:{T.C_TEXT2};border:1px solid transparent;"
                f"border-radius:{T.R_SM}px;padding:5px 12px;font-size:{T.TYPE_CONTROL}px;font-weight:500;text-align:center;}}"
                f"QPushButton:hover{{background:{T.BRAND_SOFT};color:{T.BRAND_MID};}}"
                f"QPushButton:checked{{background:{T.S_ACTIVE};color:{T.BRAND_MID};}}"
                f"QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}"
            )
            self._bind(button, zh, en, fixed_width=False)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            button.setMinimumWidth(0)
            button.clicked.connect(lambda _checked=False, i=index: self._show_tab(i))
            self._tabs.append(button)
            tab_layout.addWidget(button, 1)
        root.addWidget(tab_bar)
        self._form_card = Card(padding=(18, 18, 18, 18))
        self._form_card.setObjectName("SettingsForm")
        self._form_card.setStyleSheet(
            f"QFrame#SettingsForm{{background:{T.C_CARD};border:none;"
            f"border-radius:{T.R_CARD}px;}}"
        )
        self._form_card.layout().addWidget(self._tab_stack, 1)
        root.addWidget(self._form_card, 1)
        self._advanced_button = self._tabs[2]

        reminders = QWidget()
        reminder_layout = QVBoxLayout(reminders)
        reminder_layout.setContentsMargins(0, 0, 0, 0)
        reminder_layout.setSpacing(12)
        self._wait = self._int_input(config.NO_BLINK_ALERT_SEC, 5, 60)
        self._setting_row(reminder_layout, "首次提醒", "First reminder",
                          "连续未眨眼多久后开始提醒", "Time without a blink before reminders begin", self._wait)
        self._divider(reminder_layout)
        self._interval = self._int_input(config.ALERT_INTERVAL_SEC, 3, 30)
        self._setting_row(reminder_layout, "后续提醒间隔", "Repeat interval",
                          "仍未眨眼时，逐档加强提示", "Increase the level if no blink is detected", self._interval)
        self._divider(reminder_layout)
        self._sound = _Switch(getattr(config, "SOUND_ENABLED", True))
        self._setting_row(reminder_layout, "声音提醒", "Reminder sounds",
                          "关闭声音后，屏幕提示继续", "Screen reminders stay on when sound is off", self._sound)
        # One persistent sound family; preview buttons below play its three levels.
        self._theme_buttons = {}
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        for key, zh, en in (("polite", "Polite", "Polite"), ("sharp", "Sharp", "Sharp"), ("original", "原版", "Original"), ("blip", "Blip", "Blip")):
            button = self._button(checkable=True)
            button.setFixedHeight(38)
            self._bind(button, zh, en, fixed_width=False)
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda checked=False, value=key: self._select_sound(value))
            self._theme_buttons[key] = button
            theme_row.addWidget(button, 1)
        reminder_layout.addLayout(theme_row)
        self.soundPreviewFailed.connect(self._preview_failed)
        audio_row = QHBoxLayout()
        audio_row.setSpacing(6)
        self._audio_note = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2, wrap=True)
        self._bind(self._audio_note, "三档依次试听 · 档位间停顿 0.8 秒", "Three stages · 0.8 s between cues")
        audio_row.addWidget(self._audio_note, 1)
        self._preview_button = self._button()
        self._preview_button.setFixedWidth(146)
        self._preview_button.clicked.connect(self._toggle_preview)
        audio_row.addWidget(self._preview_button)
        self.previewStage.connect(self._preview_progress)
        self.previewFinished.connect(self._preview_finished)
        reminder_layout.addLayout(audio_row)
        self._divider(reminder_layout)
        rule_title = _label(size=13, weight=500)
        self._bind(rule_title, "当前提醒节奏", "Current reminder rhythm")
        reminder_layout.addWidget(rule_title)
        self._summary = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2, wrap=True)
        reminder_layout.addWidget(self._summary)
        stages = QHBoxLayout()
        stages.setSpacing(0)
        self._stage_names, self._stage_times = [], []
        for level in range(3):
            cell = QVBoxLayout()
            cell.setSpacing(4)
            name = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2)
            timing = _label(size=18, weight=500)
            cell.addWidget(name)
            cell.addWidget(timing)
            self._stage_names.append(name)
            self._stage_times.append(timing)
            stages.addLayout(cell, 1)
        reminder_layout.addLayout(stages)
        self._summary_sound = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2, wrap=True)
        reminder_layout.addWidget(self._summary_sound)
        reminder_layout.addStretch(1)
        self._tab_stack.addWidget(reminders)

        device = QWidget()
        device_layout = QVBoxLayout(device)
        device_layout.setContentsMargins(0, 0, 0, 0)
        device_layout.setSpacing(18)
        resolution_choices = QWidget()
        resolution_row = QHBoxLayout(resolution_choices)
        resolution_row.setContentsMargins(0, 0, 0, 0)
        resolution_row.setSpacing(6)
        self._res_buttons = {}
        resolutions = ["640×480", "1280×720", "1920×1080"]
        if self._res not in resolutions:
            resolutions.append(self._res)
        for resolution in resolutions:
            button = self._button(resolution, checkable=True)
            button.clicked.connect(lambda checked=False, r=resolution: self._set_res(r))
            self._res_buttons[resolution] = button
            resolution_row.addWidget(button)
        self._setting_row(device_layout, "摄像头分辨率", "Camera resolution",
                          "下次开启摄像头时生效", "Applies next time you start the camera", resolution_choices)
        self._restart = _label()
        self._restart.setParent(self)
        self._restart.hide()
        self._divider(device_layout)
        language_choices = QWidget()
        language_row = QHBoxLayout(language_choices)
        language_row.setContentsMargins(0, 0, 0, 0)
        language_row.setSpacing(6)
        self._lang_buttons = {}
        for language, name in (("zh", "简体中文"), ("en", "English")):
            button = self._button(name, checkable=True)
            button.clicked.connect(lambda checked=False, c=language: self._set_language(c))
            self._lang_buttons[language] = button
            language_row.addWidget(button)
        self._setting_row(device_layout, "界面语言", "Interface language",
                          "选择后立即切换", "Changes apply immediately", language_choices)
        self._divider(device_layout)
        privacy_title = _label(size=13, weight=500)
        self._bind(privacy_title, "只在本机处理", "Processed on this device")
        device_layout.addWidget(privacy_title)
        privacy_note = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2, wrap=True)
        self._bind(privacy_note, "摄像头画面用于实时检测。历史记录保存眨眼数据，不保存视频。",
                   "Camera frames are used for live detection. History stores blink data, not video.")
        device_layout.addWidget(privacy_note)
        device_layout.addStretch(1)
        self._tab_stack.addWidget(device)

        self._advanced_body = QWidget()
        advanced_layout = QVBoxLayout(self._advanced_body)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(18)
        advanced_note = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2, wrap=True)
        self._bind(advanced_note, "通常无需调整。这里保留你当前使用的检测参数。",
                   "Changes are usually unnecessary. Your current detection values are preserved.")
        advanced_layout.addWidget(advanced_note)
        self._sensitivity = _DecimalInput()
        self._sensitivity.setDecimals(2)
        self._sensitivity.setRange(min(0.4, float(config.BLINK_RATIO_THRESHOLD)), max(0.8, float(config.BLINK_RATIO_THRESHOLD)))
        self._sensitivity.setSingleStep(0.05)
        self._sensitivity.setValue(config.BLINK_RATIO_THRESHOLD)
        self._style_input(self._sensitivity)
        self._setting_row(advanced_layout, "闭眼比例阈值", "Eye-closure threshold",
                          "用于判断眼睛是否闭合", "The ratio used to detect eye closure", self._sensitivity)
        self._divider(advanced_layout)
        self._frames = self._int_input(config.PROCESS_EVERY_N_FRAMES, 1, 5)
        self._setting_row(advanced_layout, "检测帧间隔", "Frame interval",
                          "每隔多少帧执行一次检测", "Run detection once every N frames", self._frames)
        advanced_layout.addStretch(1)
        self._tab_stack.addWidget(self._advanced_body)

        # Connect only after restoring values: opening settings never rewrites them.
        self._wait.valueChanged.connect(self._on_wait)
        self._interval.valueChanged.connect(self._on_interval)
        self._sound.toggled.connect(self._on_sound)
        self._sensitivity.valueChanged.connect(self._on_sensitivity)
        self._frames.valueChanged.connect(self._on_frames)
        self._advanced_button.toggled.connect(self._toggle_advanced)
        self._show_tab(0)
        self.retranslate()

    def _show_tab(self, index):
        if index != 0:
            self._stop_preview()
        self._tab_stack.setCurrentIndex(index)
        self._advanced_open = index == 2
        for tab_index, button in enumerate(self._tabs):
            blocked = button.blockSignals(True)
            button.setChecked(index == tab_index)
            button.blockSignals(blocked)


    def _fix_button_width(self, button, labels):
        """Measure both translations once; language changes never resize controls."""
        previous = button.text()
        button.ensurePolished()
        widths = []
        for label in labels:
            button.setText(label)
            widths.append(button.sizeHint().width())
        button.setText(previous)
        button.setFixedWidth(max(widths) + 2)

    def _fix_button_width(self, button, labels):
        """Measure both translations once; language changes never resize controls."""
        previous = button.text()
        button.ensurePolished()
        widths = []
        for label in labels:
            button.setText(label)
            widths.append(button.sizeHint().width())
        button.setText(previous)
        button.setFixedWidth(max(widths) + 2)

    def _bind(self, widget, zh, en, fixed_width=True):
        self._copy.append((widget, zh, en))
        widget.setText(_tr(zh, en))
        if isinstance(widget, QPushButton) and fixed_width:
            self._fix_button_width(widget, (zh, en))
        elif isinstance(widget, QLabel) and not widget.wordWrap():
            width = max(widget.fontMetrics().horizontalAdvance(value) for value in (zh, en))
            widget.setFixedWidth(width + 2)

    def _button(self, text="", checkable=False):
        button = QPushButton(text)
        button.setCheckable(checkable)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(_button_style())
        button.setFixedHeight(32)
        if text:
            self._fix_button_width(button, (text,))
        return button

    def _card(self, zh, en, zh_hint, en_hint):
        card = Card(padding=(0, 0, 0, 0))
        layout = card.layout()
        layout.setSpacing(8)
        title = _label(size=17, weight=600)
        self._bind(title, zh, en)
        layout.addWidget(title)
        hint = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2, wrap=True)
        self._bind(hint, zh_hint, en_hint)
        layout.addWidget(hint)
        return card, layout

    def _setting_row(self, layout, zh, en, zh_hint, en_hint, control):
        row = QHBoxLayout()
        row.setSpacing(16)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        title = _label(size=T.TYPE_BODY, weight=500, wrap=True)
        self._bind(title, zh, en)
        copy.addWidget(title)
        hint = _label(size=T.TYPE_CAPTION, color=T.C_TEXT2, wrap=True)
        self._bind(hint, zh_hint, en_hint)
        copy.addWidget(hint)
        row.addLayout(copy, 1)
        field = self._stepper(control) if isinstance(control, (QSpinBox, QDoubleSpinBox)) else control
        row.addWidget(field, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(row)

    def _divider(self, layout):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{T.C_BORDER}; border:none;")
        layout.addWidget(line)

    def _style_input(self, widget):
        widget.setLineEdit(_CaretEditor(widget))
        widget.setFixedWidth(76)
        widget.setFixedHeight(34)
        widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setKeyboardTracking(False)
        # Numeric fields deliberately use caret-only editing in this UI.
        # This also clears native spinbox selection on focus, drag and Ctrl+A.
        editor = widget.lineEdit()
        editor.selectionChanged.connect(editor.deselect)
        widget.setCorrectionMode(QAbstractSpinBox.CorrectionMode.CorrectToNearestValue)
        widget.setStyleSheet(
            f"QSpinBox,QDoubleSpinBox{{background:transparent; color:{T.C_TEXT};"
            f"border:none; border-radius:{T.R_SM}px; padding:3px 0; font-size:13px; font-weight:500;}}"
            f"QSpinBox,QDoubleSpinBox{{selection-background-color:{T.BRAND_SOFT};selection-color:{T.C_TEXT};}}"
        )

    def _stepper(self, control):
        """Keep the editable spinbox API inside a compact native-button stepper."""
        shell = QFrame()
        shell.setObjectName("SettingStepper")
        shell.setFixedSize(134, 36)
        shell.setStyleSheet(
            f"QFrame#SettingStepper{{background:{T.C_SURFACE}; border:1px solid {T.C_BORDER};"
            f"border-radius:{T.R_SM}px;}}"
            f"QFrame#SettingStepper:hover{{border-color:{T.S_ACTIVE};}}"
        )
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        decrement = QPushButton("−")
        increment = QPushButton("+")
        for button in (decrement, increment):
            button.setFixedSize(28, 34)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(400)
            button.setAutoRepeatInterval(100)
            button.setStyleSheet(
                f"QPushButton{{background:transparent; color:{T.C_TEXT2}; border:none;"
                f"border-radius:{T.R_SM - 2}px; padding:0; font-size:17px; font-weight:500;}}"
                f"QPushButton:hover{{background:transparent;color:{T.BRAND_MID};}}"
                f"QPushButton:focus{{border:1px solid {T.CONTROL_FOCUS};}}"
                f"QPushButton:pressed{{background:{T.C_BORDER};}}"
                f"QPushButton:disabled{{color:{T.C_BORDER};}}"
            )
        decrement.clicked.connect(control.stepDown)
        increment.clicked.connect(control.stepUp)
        layout.addWidget(decrement)
        layout.addWidget(control)
        layout.addWidget(increment)

        def refresh_limits(*_):
            decrement.setEnabled(control.value() > control.minimum())
            increment.setEnabled(control.value() < control.maximum())

        control.valueChanged.connect(refresh_limits)
        refresh_limits()
        self._steppers.append((control, decrement, increment))
        return shell

    def _int_input(self, value, minimum, maximum):
        widget = _IntegerInput()
        widget.setRange(min(minimum, int(value)), max(maximum, int(value)))
        widget.setValue(int(value))
        self._style_input(widget)
        return widget

    def _on_wait(self, value):
        config.NO_BLINK_ALERT_SEC = int(value)
        save_config()
        self._refresh_preview()

    def _on_interval(self, value):
        config.ALERT_INTERVAL_SEC = int(value)
        save_config()
        self._refresh_preview()

    def _on_sensitivity(self, value):
        config.BLINK_RATIO_THRESHOLD = float(value)
        save_config()

    def _on_frames(self, value):
        config.PROCESS_EVERY_N_FRAMES = int(value)
        save_config()

    def _on_sound(self, enabled):
        config.SOUND_ENABLED = bool(enabled)
        save_config()
        self._refresh_preview()
        self.soundToggled.emit(bool(enabled))

    def setSoundEnabled(self, enabled):
        """Synchronize external sound changes without emitting or saving again."""
        previous = self._sound.blockSignals(True)
        self._sound.setChecked(bool(enabled))
        self._sound.blockSignals(previous)
        self._refresh_preview()

    def _set_res(self, resolution):
        width, height = resolution.split("×")
        config.CAMERA_WIDTH, config.CAMERA_HEIGHT = int(width), int(height)
        self._res = resolution
        save_config()
        self._refresh_choices()

    def _set_language(self, language):
        if language == getattr(config, "LANGUAGE", "en"):
            self._refresh_choices()
            return
        config.LANGUAGE = language
        save_config()
        self.retranslate()
        self.languageChanged.emit()

    def _refresh_choices(self):
        for theme, button in self._theme_buttons.items():
            chosen = theme == config.SOUND_THEME
            button.setChecked(chosen)
            button.setAccessibleDescription(_tr("当前提示音" if chosen else "选择此提示音", "Selected sound" if chosen else "Choose this sound"))
        for resolution, button in self._res_buttons.items():
            button.setChecked(resolution == self._res)
        for language, button in self._lang_buttons.items():
            button.setChecked(language == getattr(config, "LANGUAGE", "en"))

    def _toggle_advanced(self, expanded):
        if expanded:
            self._show_tab(2)
        elif self._tab_stack.currentIndex() == 2:
            self._show_tab(0)

    def _update_advanced_label(self):
        self._advanced_button.setText(_tr("高级检测", "Advanced detection"))
        self._advanced_button.setAccessibleDescription(_tr("切换到高级检测设置", "Show advanced detection settings"))

    def _select_sound(self, theme):
        self._stop_preview()
        config.SOUND_THEME = theme
        save_config()
        self._refresh_choices()

    def _preview_failed(self, message):
        self._preview_error = True
        self._audio_note.setText(_tr("试听失败，请检查声音输出", "Preview failed. Check audio output"))
        self._audio_note.setToolTip(message)

    def _toggle_preview(self):
        if self._preview_token is not None:
            self._stop_preview()
            return
        from alert import AUDIO, sound_file
        self._preview_error = False
        try:
            self._preview_token = AUDIO.play(
                [sound_file(i) for i in range(3)], self, priority=2,
                on_stage=self.previewStage.emit, on_finished=self.previewFinished.emit,
                on_error=self.soundPreviewFailed.emit)
            if self._preview_token is None:
                self._audio_note.setText(_tr("微休息提示结束后可试听", "Preview after the break cue ends"))
            self._preview_button.setText(_tr("停止试听", "Stop preview") if self._preview_token else _tr("试听三档", "Play all 3"))
        except Exception as error:
            self._preview_failed(str(error))

    def _preview_progress(self, token, stage):
        if token == self._preview_token:
            self._preview_stage = stage
            self._audio_note.setText(_tr(
                ("首次提示", "第二次提示", "第三次提示")[stage],
                ("First reminder", "Second reminder", "Third reminder")[stage]))

    def _preview_finished(self, token):
        if token == self._preview_token:
            self._preview_token = None
            self._refresh_audio_copy()

    def _stop_preview(self):
        from alert import AUDIO
        self._preview_token = None
        AUDIO.stop(self)
        self._refresh_audio_copy()

    def _refresh_audio_copy(self):
        self._preview_button.setText(_tr("停止试听", "Stop preview") if self._preview_token else _tr("试听三档", "Play all 3"))
        if self._preview_error:
            return
        if self._preview_token:
            self._preview_progress(self._preview_token, self._preview_stage)
        else:
            self._audio_note.setText(_tr("三档依次试听 · 档位间停顿 0.8 秒", "Three stages · 0.8 s between cues"))

    def hideEvent(self, event):
        self._stop_preview()
        super().hideEvent(event)

    def _refresh_preview(self):
        first = int(config.NO_BLINK_ALERT_SEC)
        interval = int(config.ALERT_INTERVAL_SEC)
        self._summary.setText(_tr(
            f"连续 {first} 秒未眨眼时开始提醒，每隔 {interval} 秒升级，第三档后保持。",
            f"Start after {first}s; advance every {interval}s, then repeat stage 3.",
        ))
        stages = (
            ("轻声提醒", "Gentle"),
            ("再次提醒", "A little clearer"),
            ("加强提醒", "More noticeable"),
        )
        for level, (name, timing) in enumerate(zip(self._stage_names, self._stage_times)):
            name.setText(_tr(*stages[level]))
            seconds = first + level * interval
            timing.setText(f"{seconds}{'+' if level == 2 else ''}" + _tr(" 秒", " s"))
        self._summary_sound.setText(
            _tr("声音与屏幕提示均已开启", "Sound and screen reminders are on")
            if self._sound.isChecked()
            else _tr("声音已关闭 · 屏幕提示保留", "Sound is off · screen reminders remain on")
        )

    def retranslate(self):
        """Refresh all local copy without rebuilding controls or changing values."""
        for widget, zh, en in self._copy:
            widget.setText(_tr(zh, en))
        self._wait.setSuffix(_tr(" 秒", " s"))
        self._interval.setSuffix(_tr(" 秒", " s"))
        self._frames.setSuffix(_tr(" 帧", " frames"))
        for control, zh, en in (
            (self._wait, "首次提醒等待秒数", "Seconds before the first reminder"),
            (self._interval, "后续提醒间隔秒数", "Seconds between reminder levels"),
            (self._sound, "声音提醒", "Reminder sounds"),
            (self._sensitivity, "闭眼比例阈值", "Eye-closure ratio threshold"),
            (self._frames, "检测帧间隔", "Detection frame interval"),
        ):
            control.setAccessibleName(_tr(zh, en))
        for control, decrement, increment in self._steppers:
            field_name = control.accessibleName()
            decrement.setAccessibleName(_tr("减少", "Decrease ") + field_name)
            increment.setAccessibleName(_tr("增加", "Increase ") + field_name)
            decrement.setToolTip(decrement.accessibleName())
            increment.setToolTip(increment.accessibleName())
        self._refresh_audio_copy()
        if self._preview_error:
            self._audio_note.setText(_tr(
                "声音试听不可用，请检查应用内的声音文件。",
                "Sound preview is unavailable. Check the bundled sound files.",
            ))
        self._refresh_choices()
        self._update_advanced_label()
        self._refresh_preview()
