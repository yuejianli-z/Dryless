"""Home: monitoring, reminder control, and a clearly scoped recent trend."""
from __future__ import annotations

import math
from PyQt6.QtCore import Qt, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QStackedWidget, QSizePolicy, QStylePainter, QStyleOptionComboBox, QStyle,
)
import config
from microbreak import PRESENCE_MINUTES
import theme as T
from widgets import CameraView, TrendChart
from widgets.selection_popup import StyledComboBox
from widgets.status_light import StatusLight, state_color
from widgets.camera_sim import AspectRatioHost
from widgets.soft_icon import SoftIcon
from widgets.care_tips import CareTips


def _tr(zh, en):
    return zh if str(config.LANGUAGE).lower().startswith("zh") else en


def _font(size=13, bold=False, weight=None):
    font = T.ui_font()
    font.setFamilies([T.FONT_UI] + T.FONT_FB)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight if weight is not None else (600 if bold else 400)))
    return font


def _label(size=13, color=T.C_TEXT, bold=False, wrap=False, weight=None):
    label = QLabel()
    label.setFont(_font(size, bold, weight))
    label.setWordWrap(wrap)
    label.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return label


def _button(primary=False):
    button = QPushButton()
    button.setFont(_font(T.TYPE_CONTROL, weight=500))
    button.setMinimumHeight(34)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setStyleSheet(
        f"QPushButton{{background:{T.BRAND_MID if primary else T.C_CARD};"
        f"color:{'#FFFFFF' if primary else T.C_TEXT};border:1px solid "
        f"{T.BRAND_MID if primary else T.C_BORDER};border-radius:8px;padding:5px 10px;}}"
        f"QPushButton:hover{{background:{T.BRAND_HOVER if primary else T.C_BG};}}"
        f"QPushButton:focus{{border-color:{T.CONTROL_FOCUS};}}"
        f"QPushButton:disabled{{background:{T.C_SURFACE};color:{T.C_TEXT3};border-color:{T.C_BORDER};}}"
    )
    return button


def _separator():
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{T.C_BORDER};border:none;")
    return line


class _WindowCombo(StyledComboBox):
    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
        painter.setFont(self.font())
        painter.setPen(QColor(T.C_TEXT))
        painter.drawText(self.rect().adjusted(24, 0, -24, 0), Qt.AlignmentFlag.AlignCenter, self.currentText())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(T.C_TEXT2), 1.4))
        x, y = self.width() - 13, self.height() / 2
        painter.drawLine(QPointF(x - 4, y - 2), QPointF(x, y + 2))
        painter.drawLine(QPointF(x, y + 2), QPointF(x + 4, y - 2))


class _CameraHero(QWidget):
    """Fit the camera column to the source, with the status beside its real edge."""
    def bind(self, column, heading):
        self._column = column
        self._heading = heading
        self._ratio = 4 / 3
        QTimer.singleShot(0, self._reflow)

    def setAspectRatio(self, ratio):
        self._ratio = ratio
        self._reflow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_column'):
            self._reflow()

    def _reflow(self):
        if not hasattr(self, '_column'):
            return
        margins = self.layout().contentsMargins()
        image_height = max(1, self.height() - margins.top() - margins.bottom() - self._heading.height() - 8 - 32)
        available = self.width() - margins.left() - margins.right() - 24
        width = max(1, min(round(image_height * self._ratio) + 32, int(available * .56), available - 408))
        if self._column.width() != width or self._column.minimumWidth() != width:
            self._column.setFixedWidth(width)


class MonitorScreen(QWidget):
    statusChanged = pyqtSignal(str, str)
    previewToggled = pyqtSignal(bool)
    pauseToggled = pyqtSignal(bool)
    soundToggled = pyqtSignal(bool)
    settingsRequested = pyqtSignal()
    statisticsRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
        self._preview_visible = True
        self._sound_enabled = bool(config.SOUND_ENABLED)
        self._camera_state = "off"
        self._last_state = None
        self._error = None
        self._alert_error = None
        self._alert_counts = [0, 0, 0]
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        self.page_header = QWidget(self)
        self.page_header.setFixedHeight(36)
        header = QHBoxLayout(self.page_header)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        header.addWidget(SoftIcon("eye",size=26,glyph_size=15))
        self._page_title = _label(24, T.C_TEXT, True)
        header.addWidget(self._page_title)
        header.addStretch()

        hero = _CameraHero()
        hero.setMinimumHeight(280)
        hero.setObjectName("MonitorHero")
        hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        hero.setStyleSheet(f"QWidget#MonitorHero{{background:transparent;border:none;}}")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(24)
        camera_column = QWidget()
        camera_column.setObjectName("CameraPanel")
        camera_column.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        camera_column.setStyleSheet(f"QWidget#CameraPanel{{background:{T.C_CARD};border:none;border-radius:{T.R_CARD}px;}}")
        camera_layout = QVBoxLayout(camera_column)
        camera_layout.setContentsMargins(16, 16, 16, 16)
        camera_layout.setSpacing(8)
        camera_header = QWidget()
        camera_header.setFixedHeight(34)
        camera_heading = QHBoxLayout(camera_header)
        camera_heading.setContentsMargins(0, 0, 0, 0)
        self._camera_title = _label(T.TYPE_SECTION, T.C_TEXT, True)
        camera_heading.addWidget(self._camera_title)
        camera_heading.addStretch()
        self._preview_button = _button()
        self._preview_button.setFixedHeight(32)
        self._preview_button.clicked.connect(self._toggle_preview)
        camera_heading.addWidget(self._preview_button)
        camera_layout.addWidget(camera_header)
        self._camera_stack = QStackedWidget()
        self._camera_stack.setStyleSheet("QStackedWidget{background:transparent;border:none;}")
        self._camera_stack.setMinimumSize(0, 0)
        self.camera = CameraView()
        self.camera.setMinimumSize(0, 0)
        self._camera_stack.addWidget(self.camera)
        hidden = QFrame()
        hidden.setObjectName('HiddenCamera')
        hidden.setStyleSheet(f'QFrame#HiddenCamera{{background:{T.S_BG};border:1px solid {T.C_BORDER};border-radius:10px;}}')
        hidden_layout = QVBoxLayout(hidden)
        self._preview_hidden_title = _label(15, T.C_TEXT, True)
        self._preview_hidden_text = _label(T.TYPE_CAPTION, T.C_TEXT2, wrap=True)
        for label in (self._preview_hidden_title, self._preview_hidden_text):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hidden_layout.addStretch()
        hidden_layout.addWidget(self._preview_hidden_title)
        hidden_layout.addWidget(self._preview_hidden_text)
        hidden_layout.addStretch()
        self._camera_stack.addWidget(hidden)
        self._camera_host = AspectRatioHost(self._camera_stack)
        self.camera.frameAspectRatioChanged.connect(self._camera_host.setAspectRatio)
        self.camera.frameAspectRatioChanged.connect(hero.setAspectRatio)
        camera_layout.addWidget(self._camera_host, 1)
        hero_layout.addWidget(camera_column)
        hero.bind(camera_column, camera_header)

        self._state_section = QWidget()
        self._state_section.setObjectName("StatePanel")
        self._state_section.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self._state_section.setStyleSheet(f"QWidget#StatePanel{{background:{T.C_CARD};border:none;border-radius:{T.R_CARD}px;}}")
        self._state_section.setMinimumWidth(408)
        state_layout = QVBoxLayout(self._state_section)
        state_layout.setContentsMargins(14, 12, 14, 12)
        state_layout.setSpacing(5)
        self._status_lbl = _label(19, T.C_TEXT, True)
        self._status_lbl.setWordWrap(False)
        self._status_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        status_header = QWidget()
        status_header.setFixedHeight(34)
        status_header.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        status_row = QHBoxLayout(status_header)
        status_row.setContentsMargins(0,0,0,0)
        status_row.setSpacing(9)
        self._status_dot = StatusLight(size=18)
        status_row.addWidget(self._status_dot)
        status_row.addWidget(self._status_lbl, 1)
        self._pause_button = _button()
        self._pause_button.clicked.connect(self._toggle_pause)
        status_row.addWidget(self._pause_button)
        state_layout.addWidget(status_header)
        self._message_body = _label(T.TYPE_BODY, T.C_TEXT2, wrap=True)
        state_layout.addWidget(self._message_body)
        self._timer_row = QWidget()
        numbers = QHBoxLayout(self._timer_row)
        numbers.setContentsMargins(0, 0, 0, 0)
        numbers.setSpacing(24)
        self._since_lbl = _label(T.TYPE_CAPTION, T.C_TEXT2)
        self._secs_lbl = _label(26, T.C_TEXT, weight=500)
        self._total_label = _label(T.TYPE_CAPTION, T.C_TEXT2)
        self._total_value = _label(26, T.C_TEXT, weight=500)
        for name, label, value in (("clock", self._since_lbl, self._secs_lbl), ("eye", self._total_label, self._total_value)):
            column = QVBoxLayout()
            column.setSpacing(4)
            metric_heading = QHBoxLayout()
            metric_heading.setSpacing(6)
            metric_heading.addWidget(SoftIcon(name,size=22,glyph_size=14))
            metric_heading.addWidget(label,1)
            column.addLayout(metric_heading)
            column.addWidget(value)
            numbers.addLayout(column, 1)
        state_layout.addWidget(self._timer_row)
        self._reminder_status_lbl = _label(T.TYPE_SECTION, T.C_TEXT, True)
        self._rule_lbl = _label(T.TYPE_CAPTION, T.C_TEXT2, wrap=True)
        self._reminder_status_lbl.setParent(self)
        self._reminder_status_lbl.hide()
        self._run_summary = QWidget()
        self._run_summary.setFixedHeight(60)
        run_layout = QHBoxLayout(self._run_summary)
        run_layout.setContentsMargins(0, 0, 0, 0)
        run_layout.setSpacing(24)
        self._run_alerts_label = _label(T.TYPE_CAPTION, T.C_TEXT2)
        self._run_alerts_value = _label(26, T.C_TEXT, weight=500)
        self._run_time_label = _label(T.TYPE_CAPTION, T.C_TEXT2)
        self._run_time_value = _label(26, T.C_TEXT, weight=500)
        for name, label, value in (("bell", self._run_alerts_label, self._run_alerts_value),
                             ("clock", self._run_time_label, self._run_time_value)):
            column = QVBoxLayout()
            column.setSpacing(4)
            label.setFixedHeight(22)
            value.setFixedHeight(34)
            metric_heading = QHBoxLayout()
            metric_heading.setSpacing(6)
            metric_heading.addWidget(SoftIcon(name, size=22, glyph_size=14))
            metric_heading.addWidget(label, 1)
            column.addLayout(metric_heading)
            column.addWidget(value)
            run_layout.addLayout(column, 1)
        state_layout.addWidget(self._run_summary)
        state_layout.addWidget(self._rule_lbl)
        state_layout.addStretch(1)
        # The sound control is reparented into the shared title bar by DrylessApp.
        self._sound_button = _button()
        self._sound_button.setCheckable(True)
        self._sound_button.clicked.connect(self._toggle_sound)
        self._sound_button.hide()
        self.tips = CareTips()
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.addWidget(self._state_section, 1)
        right_layout.addWidget(self.tips)
        hero_layout.addWidget(right_column, 1)
        root.addWidget(hero, 4)

        recent = QWidget()
        recent.setObjectName("RecentPanel")
        recent.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        recent.setStyleSheet(f"QWidget#RecentPanel{{background:{T.C_CARD};border:none;border-radius:{T.R_CARD}px;}}")
        recent.setFixedHeight(152)
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(20, 10, 20, 10)
        recent_layout.setSpacing(5)
        trend_heading = QHBoxLayout()
        trend_heading.setSpacing(8)
        trend_heading.addWidget(SoftIcon("activity",size=24,glyph_size=15))
        self._trend_title = _label(T.TYPE_SECTION, T.C_TEXT, True)
        trend_heading.addWidget(self._trend_title)
        trend_heading.addSpacing(16)
        self._frequency_value = _label(20, T.C_TEXT, weight=500)
        self._frequency_unit = _label(T.TYPE_CAPTION, T.C_TEXT2)
        for label in (self._frequency_value, self._frequency_unit):
            trend_heading.addWidget(label)
        trend_heading.addStretch()
        self._window_combo = _WindowCombo()
        self._window_combo.setProperty("centerMenuText", True)
        self._window_combo.setFont(_font(T.TYPE_CONTROL))
        self._window_combo.setFixedSize(138, 32)
        self._window_combo.setStyleSheet(
            f'QComboBox{{background:{T.C_CARD};color:{T.C_TEXT};border:1px solid {T.C_BORDER};border-radius:8px;padding:4px 8px;}}'
            'QComboBox::drop-down{border:none;width:23px;}QComboBox::down-arrow{image:none;}'
            f'QComboBox QAbstractItemView{{background:{T.C_CARD};color:{T.C_TEXT};selection-background-color:{T.BRAND_SOFT};}}')
        self._window_combo.currentIndexChanged.connect(self._change_window)
        trend_heading.addWidget(self._window_combo)
        self._stats_button = _button()
        self._stats_button.setMinimumHeight(30)
        self._stats_button.clicked.connect(self.statisticsRequested.emit)
        trend_heading.addWidget(self._stats_button)
        recent_layout.addLayout(trend_heading)
        self._trend_caption = _label(T.TYPE_CAPTION, T.C_TEXT2)
        recent_layout.addWidget(self._trend_caption)
        self.trend = TrendChart()
        self.trend.setMinimumHeight(72)
        self.trend.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        recent_layout.addWidget(self.trend, 1)
        root.addWidget(recent, 2)

        self._reserve_language_slots()
        self.retranslate()

    def _reserve_language_slots(self):
        """Reserve both translations once, before any visible layout is drawn."""
        heights = {
            self._page_title: 35,
            self._camera_title: 34,
            self._status_lbl: 34,
            self._message_body: 36,
            self._since_lbl: 22,
            self._secs_lbl: 34,
            self._total_label: 22,
            self._total_value: 34,
            self._reminder_status_lbl: 24,
            self._rule_lbl: 20,
            self._trend_title: 30,
            self._frequency_value: 30,
            self._frequency_unit: 30,
            self._trend_caption: 20,
            self._preview_hidden_title: 24,
            self._preview_hidden_text: 38,
        }
        for label, height in heights.items():
            label.setFixedHeight(height)
        self._message_body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._timer_row.setFixedHeight(60)
        self._secs_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self._total_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        for button in (self._pause_button, self._sound_button):
            button.setFixedHeight(36)
        self._preview_button.setFixedHeight(32)
        self._stats_button.setFixedHeight(32)

        def reserve(widget, texts, padding=0):
            metrics = widget.fontMetrics()
            widget.setFixedWidth(max(metrics.horizontalAdvance(text) for text in texts) + padding)

        reserve(self._page_title, ("监测", "Monitor"), 2)
        reserve(self._camera_title, ("实时画面", "Live camera"), 2)
        reserve(self._trend_title, ("眨眼节律", "Blink rhythm"), 2)
        reserve(self._frequency_unit, ("次/分 · 均值", "/min · avg"), 2)
        reserve(self._frequency_value, ("999.9", "—"), 2)
        reserve(self._preview_button, ("隐藏预览", "显示预览", "Hide", "Show"), 24)
        reserve(self._pause_button, ("恢复提醒", "暂停提醒", "Resume alerts", "Pause alerts"), 24)
        reserve(self._sound_button, ("声音：开", "声音：关", "声音不可用", "Sound: on", "Sound: off", "Sound unavailable"), 24)
        for button in (self._pause_button, self._sound_button):
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        reserve(self._stats_button, ("更多统计", "More statistics"), 24)
        self._pause_button.setFixedSize(128, 30)
        self._pause_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def resetSession(self):
        self._last_state = None
        self._error = None
        self._alert_error = None
        self._alert_counts = [0, 0, 0]
        self._live_samples = []
        self.trend.setData([])

    def setCameraState(self, state):
        self._camera_state = state
        if state != "running":
            self.camera.setFrame(None)
        self._refresh_controls()
        self._render_state()

    def _toggle_preview(self):
        self.setPreviewVisible(not self._preview_visible)
        self.previewToggled.emit(self._preview_visible)

    def _toggle_pause(self):
        self.setPaused(not self._paused)
        self.pauseToggled.emit(self._paused)

    def _toggle_sound(self, enabled):
        self.setSoundEnabled(enabled)
        self.soundToggled.emit(self._sound_enabled)

    def _change_window(self):
        self.trend.setWindow(self._window_combo.currentData())
        self._refresh_trend_caption()
        self._render_state()

    def setPaused(self, paused):
        self._paused = bool(paused)
        self._refresh_controls()
        self._render_state()

    def setPreviewVisible(self, visible):
        self._preview_visible = bool(visible)
        self._refresh_controls()

    def setSoundEnabled(self, enabled):
        self._sound_enabled = bool(enabled)
        self._sound_button.setChecked(self._sound_enabled)
        self._refresh_controls()

    def setError(self, message):
        self._error = str(message)
        self.camera.setError(message)
        self._render_state()

    def setAlertError(self, message):
        # Audio initialization failures persist while camera updates continue.
        self._alert_error = str(message)
        self._refresh_controls()
        self._render_state()

    def on_alert_triggered(self, level):
        if not self._paused and 0 <= level < 3:
            self._alert_counts[level] += 1
            self._render_state()

    def update_state(self, state):
        self._camera_state = "running"
        self._last_state = dict(state)
        self._error = None
        if "paused" in state:
            self._paused = bool(state["paused"])
            self._refresh_controls()
        counts = list(state.get("minute_history") or [])
        exposure = list(state.get("minute_valid_seconds") or [])
        self._live_samples = [
            (float(count), float(exposure[i])) if i < len(exposure) and exposure[i] >= 30 else None
            for i, count in enumerate(counts)
        ]
        values = [count * 60 / seconds if item is not None else None
                  for item in self._live_samples
                  for count, seconds in [item or (0, 1)]]
        self.trend.setData(values)
        self._refresh_trend_caption()
        self._render_state()

    def _refresh_trend_caption(self):
        window = self.trend.windowMinutes()
        self._trend_caption.setText(_tr(
            f"最近 {window} 分钟 · 每格 1 分钟",
            f"Last {window} minutes · 1 minute per tile",
        ))

    def _refresh_controls(self):
        running = self._camera_state == "running"
        self._pause_button.setEnabled(running)
        self._preview_button.setEnabled(running)
        self._camera_stack.setCurrentIndex(0 if running and self._preview_visible else 1)
        self._preview_hidden_title.setText(_tr("预览已隐藏", "Preview hidden") if running else _tr("摄像头未开启", "Camera is off"))
        self._preview_hidden_text.setText(_tr("隐藏画面不会停止检测。", "Hiding the image does not stop detection.") if running else _tr("点击右上角开启摄像头。", "Use Start camera above to begin."))
        if self._camera_state in ("starting", "stopping"):
            self._preview_hidden_title.setText(_tr("正在连接…", "Connecting…") if self._camera_state == "starting" else _tr("正在关闭…", "Stopping…"))
            self._preview_hidden_text.setText(_tr("请稍候。", "Please wait."))
        if self._camera_state == "error":
            self._preview_hidden_title.setText(_tr("摄像头不可用", "Camera unavailable"))
            self._preview_hidden_text.setText(_tr("检查设备后，点击右上角重试。", "Check your device, then use Retry camera above."))
        self._preview_button.setText(_tr("隐藏预览", "Hide") if self._preview_visible else _tr("显示预览", "Show"))
        self._pause_button.setText(_tr("恢复提醒", "Resume alerts") if self._paused else _tr("暂停提醒", "Pause alerts"))
        self._sound_button.setText(_tr("声音：开", "Sound: on") if self._sound_enabled else _tr("声音：关", "Sound: off"))
        if self._alert_error:
            self._sound_button.setText(_tr("声音故障", "Audio error"))
        self._sound_button.setEnabled(not self._alert_error)
        self._preview_button.setToolTip(_tr("仅隐藏画面，摄像头检测继续运行。", "Hide the image only. Camera detection keeps running."))
        self._pause_button.setToolTip(_tr("暂停声音和界面提醒，检测与计数继续。", "Pause sound and visual alerts. Detection and counts continue."))
        self._sound_button.setToolTip(self._alert_error or _tr("关闭声音后，界面提醒仍然保留。", "Visual alerts remain available when sound is off."))

    def _error_message(self, message, audio=False):
        """Keep a readable reason in the status area and the full error in its tooltip."""
        text = " ".join(str(message).split())
        lower = text.lower()
        if any(word in lower for word in ("permission", "access denied", "权限", "denied")):
            return _tr("无法访问设备，请在系统设置中允许摄像头或音频权限。", "Device access is blocked. Allow camera or audio access in system settings.")
        if audio:
            return _tr("无法播放提醒声音，请检查音频设备。界面提醒仍可用。", "Audio is unavailable. Check your sound device; visual alerts still work.")
        if any(word in lower for word in ("camera", "摄像头", "video capture", "videocapture")):
            return _tr("无法连接摄像头，请检查连接，或关闭占用摄像头的应用。", "Camera unavailable. Check its connection or close other apps using it.")
        if any(word in lower for word in ("detector", "mediapipe", "检测器", "初始化")):
            return _tr("眨眼识别未能启动，请重新打开应用后重试。", "Blink detection could not start. Reopen the app to try again.")
        # Unknown errors retain their concrete reason; wrapping and elision stay in two lines.
        metrics = self._message_body.fontMetrics()
        return metrics.elidedText(text, Qt.TextElideMode.ElideRight,
                                  max(240, self._message_body.width() * 2 - 30))

    def _render_state(self):
        state = self._last_state or {}
        face = bool(state.get("face")) and not self._error
        ratio = state.get("eye_ratio")
        ready = face and ratio is not None
        level = max(-1, min(2, int(state.get("alert_level", -1)))) if ready and not self._paused else -1
        base = float(config.NO_BLINK_ALERT_SEC)
        interval = float(config.ALERT_INTERVAL_SEC)
        seconds = max(0., float(state.get("no_blink", 0)))
        if self._error:
            status, status_color = _tr("监测异常", "Monitoring error"), T.DANGER
            body = self._error_message(self._error)
        elif self._last_state is None:
            status, status_color = _tr("正在连接摄像头", "Connecting camera"), T.C_TEXT2
            body = _tr("检测就绪后开始记录眨眼。", "Blink recording starts when detection is ready.")
        elif not face:
            status, status_color = _tr("未识别到人脸", "No face detected"), T.C_TEXT2
            body = _tr("请正对摄像头，识别人脸后继续监测。", "Face the camera to resume monitoring.")
        elif not ready:
            status, status_color = _tr("正在校准", "Calibrating"), T.C_TEXT2
            body = _tr("请自然睁眼，正在准备监测。", "Keep your eyes open naturally while monitoring gets ready.")
        else:
            status, status_color = _tr("监测中", "Monitoring"), T.C_TEXT
            if self._paused:
                body = _tr("眨眼检测与记录继续进行。", "Blink detection and recording continue.")
            elif level >= 0:
                body = _tr(f"已连续 {seconds:.1f} 秒未检测到眨眼。", f"No blink detected for {seconds:.1f} seconds.")
            else:
                body = _tr("持续未眨眼时会提醒你。", "You’ll be reminded when no blink is detected for a while.")
            if self._alert_error and not self._paused and level < 0:
                body = self._error_message(self._alert_error, audio=True)
        if self._error:
            status_key = "error"
        elif self._last_state is None:
            status_key = "waiting"
        elif not face:
            status_key = "no_face"
        elif not ready:
            status_key = "waiting"
        elif self._paused:
            status_key = "paused"
            status = _tr("提醒已暂停", "Alerts paused")
        elif level >= 0:
            status_key = f"alert_{level}"
            status = _tr("记得眨一下眼", "Time for a blink")
        else:
            status_key = "detected"
        micro_active = bool(state.get("microbreak_active")) and not self._paused and not self._error
        if micro_active:
            level = -1
            status_key = "detected"
            status = _tr("该起来活动一下了", "Time to move")
            body = _tr(f"已连续在场 {PRESENCE_MINUTES} 分钟，起来活动一下吧。", f"You’ve been here for {PRESENCE_MINUTES} minutes. Take a short walk.")
        self._status_key = status_key
        self._status_lbl.setText(status)
        self._status_dot.setState(status_key)
        self._status_lbl.setStyleSheet(f"color:{state_color(status_key).name()};background:transparent;border:none;")
        reminder_text = _tr("提醒已暂停", "Alerts paused") if self._paused else (
            _tr("等待检测就绪", "Waiting for detection") if not ready else
            _tr("正在提醒", "Alert active") if level >= 0 else _tr("提醒已开启", "Alerts enabled")
        )
        if self._alert_error and not self._paused:
            reminder_text = _tr("声音故障", "Audio error")
        if micro_active and not self._alert_error:
            reminder_text = _tr("微休息 · 眨眼提醒暂缓", "Break · blink alerts on hold")
        self._reminder_status_lbl.setText(reminder_text)
        self._message_body.setText(body)
        self._message_body.setToolTip("\n".join(message for message in (self._error, self._alert_error) if message))
        self._secs_lbl.setText(f"{seconds:.1f}s" if ready else "—")
        self._timer_row.setVisible(True)
        urgency = T.ALERT_LEVELS[level]["c"] if level >= 0 else T.C_TEXT
        self._secs_lbl.setStyleSheet(f"color:{urgency};background:transparent;border:none;")
        self._rule_lbl.setText(_tr(
            f"{base:g} 秒开始提醒 · 间隔 {interval:g} 秒",
            f"Alert at {base:g}s · repeat every {interval:g}s",
        ))
        if micro_active:
            self._rule_lbl.setText(_tr("提示结束后恢复眨眼提醒", "Blink alerts resume after this reminder"))
        samples = getattr(self, '_live_samples', [])[-self.trend.windowMinutes():]
        available = [item for item in samples if item is not None]
        duration = sum(item[1] for item in available)
        frequency = sum(item[0] for item in available) * 60 / duration if duration else None
        self._frequency_value.setText(f'{frequency:.1f}' if frequency is not None else '—')
        self._frequency_value.setStyleSheet(f'color:{T.C_TEXT};background:transparent;border:none;')
        self._frequency_unit.setVisible(bool(available))
        self._frequency_value.setVisible(bool(available))
        self._message_body.setText(body)
        if ready and level < 0 and not self._paused and not self._alert_error and not micro_active:
            self._message_body.setText(_tr("已识别人脸，正在记录眨眼。", "Face detected. Blink recording is active."))
        total = f"{int(state.get('total', 0)):,}" if self._last_state else "—"
        alerts = sum(self._alert_counts)
        self._total_value.setText(total)
        self._run_alerts_value.setText(f"{alerts:,}")
        elapsed = max(0, int(state.get("session_sec", 0)))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self._run_time_value.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}" if self._last_state else "—")
        if self._camera_state in ("off", "stopping", "starting"):
            stopped = self._camera_state == "off"
            status_key = "off" if stopped else "waiting"
            status = _tr("摄像头已关闭", "Camera is off") if stopped else (
                _tr("正在关闭摄像头", "Stopping camera") if self._camera_state == "stopping" else _tr("正在连接摄像头", "Connecting camera"))
            self._status_lbl.setText(status)
            self._status_lbl.setStyleSheet(f"color:{state_color(status_key).name()};background:transparent;border:none;")
            self._status_dot.setState(status_key)
            self._status_key = status_key
            self._secs_lbl.setText("—")
            self._message_body.setText(_tr("本次已结束。开启摄像头可开始新的记录。", "Session ended. Start the camera for a new session.") if self._last_state else _tr("开启摄像头后，开始检测与记录。", "Start the camera to begin tracking and recording."))
            if not stopped:
                self._message_body.setText(_tr("正在准备摄像头，检测就绪后开始记录。", "Preparing the camera. Recording starts when tracking is ready.") if self._camera_state == "starting" else _tr("正在释放设备，画面与提醒已停止。", "Releasing the device. Preview and reminders have stopped."))
            self._rule_lbl.setText(_tr("检测与提醒均已停止", "Detection and reminders are stopped") if stopped else _tr("检测就绪后开始提醒", "Reminders start when tracking is ready"))
        self.tips.setAlertActive(self._camera_state == "running" and (level >= 0 or micro_active))
        self.statusChanged.emit(status_key, status)

    def retranslate(self):
        self._page_title.setText(_tr("监测", "Monitor"))
        self._camera_title.setText(_tr("实时画面", "Live camera"))
        self._total_label.setText(_tr("本次眨眼", "Blinks this run"))
        self._run_alerts_label.setText(_tr("本次提醒", "Alerts this run"))
        self._run_time_label.setText(_tr("本次运行", "Running time"))
        self._run_alerts_value.setToolTip(_tr("按进入提醒级别计数，重启后归零。", "Counts entries into reminder levels; resets on restart."))
        self._run_time_value.setToolTip(_tr("本次启动后的运行时长（时:分:秒）。", "Time since this run started (hours:minutes:seconds)."))
        self._since_lbl.setText(_tr("距上次眨眼", "Since last blink"))
        self._secs_lbl.setToolTip(_tr("检测到眨眼或重新识别人脸时重新计时。", "Resets after a detected blink or when your face is detected again."))
        self._preview_hidden_title.setText(_tr("预览已隐藏", "Preview hidden"))
        self._preview_hidden_text.setText(_tr("隐藏画面不会停止检测。", "Hiding the image does not stop detection."))
        self._stats_button.setText(_tr("更多统计", "More statistics"))
        self._trend_title.setText(_tr("眨眼节律", "Blink rhythm"))
        self._frequency_unit.setText(_tr("次/分 · 均值", "/min · avg"))
        self._frequency_value.setToolTip(_tr("按图中时间窗口加权；单分钟有效识别不足30秒时留空。", "Weighted over the chart window. Minutes with under 30 seconds of valid tracking are left blank."))
        selected = self._window_combo.currentData()
        self._window_combo.blockSignals(True)
        self._window_combo.clear()
        for text, value in [(_tr("自动窗口", "Auto window"), None), (_tr("15 分钟", "15 minutes"), 15), (_tr("30 分钟", "30 minutes"), 30), (_tr("60 分钟", "60 minutes"), 60)]:
            self._window_combo.addItem(text, value)
        self._window_combo.setCurrentIndex(max(0, self._window_combo.findData(selected)))
        self._window_combo.blockSignals(False)
        self._window_combo.setAccessibleName(_tr("趋势时间窗口", "Trend time window"))
        self.tips.retranslate()
        self._refresh_controls()
        self._refresh_trend_caption()
        self._render_state()
        self.trend.setAccessibleName(_tr("近期完整分钟眨眼趋势", "Recent completed-minute blink trend"))
        self.trend.setAccessibleDescription(_tr("左右方向键查看各分钟数值。", "Use left and right arrows to inspect minute values."))
        self.trend._show_value(-1)
        self.trend.update()
