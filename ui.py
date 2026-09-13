"""
Dryless PyQt6 main window.

- Frameless desktop window with custom window controls
- Neutral workspace sidebar, white content area, and alert strip
- Monitor, stats, and settings screens
"""
from __future__ import annotations

import os
import sys
# Process-local Windows renderer: consistent gray text at fractional DPI.
# Keep an explicit caller platform override intact.
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "windows:fontengine=freetype")
import time
import math
import threading
from collections import deque

import cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QStackedWidget, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPoint, QRectF, QSize,
)
from PyQt6.QtGui import (
    QColor, QFontDatabase, QFont, QImage, QPainter, QPen, QPainterPath,
    QMouseEvent, QIcon,
)

import config
from blink_detector import BlinkDetector
from alert import AlertManager, AUDIO
from microbreak import MicrobreakController
from live_metrics import BlinkWindows
import history_store
from i18n import t

import theme as T
from widgets import Sidebar, TitleBar, AlertStrip
from widgets.window_frame import apply_window_shape
from widgets.interaction_policy import install_no_hover_popups
from screens.monitor import MonitorScreen
from screens.stats import StatsScreen
from screens.settings import SettingsScreen


# ═══════════════════════════════════════════════════════════════
# 字体加载
# ═══════════════════════════════════════════════════════════════
_FONT_LOADED = False


def _resource_base():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore
    return os.path.dirname(os.path.abspath(__file__))


def load_bundled_fonts():
    global _FONT_LOADED
    if _FONT_LOADED:
        return
    font_dir = os.path.join(_resource_base(), "assets", "fonts")
    if os.path.isdir(font_dir):
        for fname in os.listdir(font_dir):
            if fname.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(font_dir, fname))
    # Resolve the real Windows CJK bold face under the FreeType renderer.
    # Use installed system files; do not redistribute Microsoft fonts.
    if sys.platform == "win32":
        from PyQt6.QtGui import QTextLayout
        warmup = QTextLayout("监测", T.ui_font(24, 600))
        warmup.beginLayout()
        warmup.createLine()
        warmup.endLayout()
        warmup.glyphRuns()
        system_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        for filename in ("msyh.ttc", "msyhbd.ttc"):
            installed_font = os.path.join(system_fonts, filename)
            if os.path.isfile(installed_font):
                QFontDatabase.addApplicationFont(installed_font)
    _FONT_LOADED = True


def fnt(size, weight=400):
    f = T.ui_font()
    f.setFamilies([T.FONT_UI] + T.FONT_FB)
    f.setPixelSize(int(size))
    wmap = {
        300: QFont.Weight.Light, 400: QFont.Weight.Normal,
        500: QFont.Weight.Medium, 600: QFont.Weight.DemiBold,
        700: QFont.Weight.Bold,
    }
    f.setWeight(wmap.get(weight, QFont.Weight.Normal))
    return f


# ═══════════════════════════════════════════════════════════════
# 检测线程
# ═══════════════════════════════════════════════════════════════
class DetectorWorker(QThread):
    captureReady = pyqtSignal()
    frameReady = pyqtSignal(QImage)
    stats = pyqtSignal(dict)
    alertTriggered = pyqtSignal(int)  # level
    errorReported = pyqtSignal(str)
    alertErrorReported = pyqtSignal(str)
    minuteCommitted = pyqtSignal()    # 每完成一个分钟桶时触发，通知统计页刷新

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._stop_requested = threading.Event()
        self._paused = False
        self._sound_enabled = config.SOUND_ENABLED
        self._detector: BlinkDetector | None = None
        self._alert: AlertManager | None = None

        self._minute_history = deque(maxlen=60)
        self._minute_valid_history = deque(maxlen=60)
        self._session_start = time.time()
        self._reminder_elapsed = 0.0
        self._last_alert_round_seen = -1
        self._microbreak = MicrobreakController()
        self._blink_resume_at = None

    def _update_reminders(self, face, blinked, no_blink, now):
        micro = self._microbreak.update(face, now, self._paused)
        if micro['started'] or micro['ended']:
            self._blink_resume_at = now
            self._last_alert_round_seen = -1
            if self._alert:
                self._alert.stop()
                self._alert.reset()
                if micro['started']:
                    self._alert.play_microbreak()
        if blinked:
            self._blink_resume_at = None
            self._last_alert_round_seen = -1
            if self._alert:
                self._alert.reset()
                if not micro['active']:
                    self._alert.stop()
        if self._paused or not face:
            self._blink_resume_at = now
            self._last_alert_round_seen = -1
            if self._alert:
                self._alert.reset()
                if not micro['active']:
                    self._alert.stop()
        effective = no_blink
        if self._blink_resume_at is not None:
            effective = min(effective, max(0, now - self._blink_resume_at))
        self._reminder_elapsed = effective
        level = -1
        if face and not self._paused and not micro['active']:
            if effective >= config.NO_BLINK_ALERT_SEC:
                alert_round = int((effective - config.NO_BLINK_ALERT_SEC) // max(1, config.ALERT_INTERVAL_SEC))
                level = min(2, alert_round)
                if alert_round != self._last_alert_round_seen:
                    self._last_alert_round_seen = alert_round
                    self.alertTriggered.emit(level)
            if self._alert:
                self._alert.check_and_alert(effective)
        return level, micro

    def request_stop(self):
        self._stop_requested.set()
        self._running = False
        if self._alert:
            self._alert.stop()
        self.requestInterruption()

    def stop(self):
        self.request_stop()
        return self.wait(1500)

    def setPaused(self, paused: bool):
        self._paused = bool(paused)
        if self._alert:
            self._alert.enabled = self._sound_enabled and not self._paused
            if self._paused:
                self._alert.stop()

    def setSoundEnabled(self, enabled: bool):
        self._sound_enabled = bool(enabled)
        if self._alert:
            self._alert.enabled = bool(enabled) and not self._paused
            if not enabled:
                self._alert.stop()

    def run(self):
        cap = None
        try:
            if self._stop_requested.is_set():
                return
            try:
                self._detector = BlinkDetector()
            except Exception as e:
                self.errorReported.emit(t("err_detector", e=e))
                return
            try:
                self._alert = AlertManager(on_error=self.alertErrorReported.emit)
                self._alert.enabled = self._sound_enabled and not self._paused
            except Exception as e:
                self._alert = None
                self.alertErrorReported.emit(t("err_alert", e=e))

            if self._stop_requested.is_set():
                return
            cap = cv2.VideoCapture(config.CAMERA_INDEX)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            if not cap.isOpened():
                self.errorReported.emit(t("err_camera", index=config.CAMERA_INDEX))
                return

            self._running = not self._stop_requested.is_set() and not self.isInterruptionRequested()
            self._session_start = time.time()
            windows = BlinkWindows(time.monotonic())
            frame_count = 0
            read_failures = 0

            while self._running and not self._stop_requested.is_set() and not self.isInterruptionRequested():
                ok, frame = cap.read()
                if not ok:
                    read_failures += 1
                    if read_failures >= 90:
                        self.errorReported.emit(t("err_camera", index=config.CAMERA_INDEX))
                        break
                    self.msleep(30)
                    continue
                read_failures = 0
                frame_count += 1
                if frame_count == 1:
                    self.captureReady.emit()

                if frame_count % max(1, config.PROCESS_EVERY_N_FRAMES) == 0:
                    frame, blinked, no_blink_sec, _ = self._detector.process_frame(frame)
                    if self._stop_requested.is_set():
                        break

                    sample_time = time.monotonic()
                    sample_valid = (self._detector.face_detected and self._detector._ratio is not None
                                    and math.isfinite(self._detector._ratio))
                    live = windows.sample(sample_time, sample_valid, blinked)
                    level, micro = self._update_reminders(
                        self._detector.face_detected, blinked, no_blink_sec, sample_time)
                    for minute in live['completed']:
                        from datetime import datetime, timedelta
                        self._minute_history.append(float(minute.blinks))
                        self._minute_valid_history.append(minute.valid_seconds)
                        # Keep the legacy saved-minute schema; live exposure is separate.
                        stamp = datetime.fromtimestamp(self._session_start) + timedelta(minutes=minute.index+1)
                        history_store.append_minute(minute.blinks, minute.index, stamp.strftime("%H:%M"))
                        self.minuteCommitted.emit()

                    self.stats.emit({
                        "paused": self._paused,
                        "microbreak_active": micro["active"],
                        "microbreak_remaining": micro["remaining_seconds"],
                        "face": self._detector.face_detected,
                        "eye_open": self._detector._is_open,
                        "eye_ratio": float(self._detector._ratio) if self._detector._ratio is not None else None,
                        "rate": live["rate"],
                        "rolling_rate": live["rate"],
                        "rolling_valid_seconds": live["valid_seconds"],
                        "rolling_blinks": live["blinks"],
                        "reminder_elapsed": float(self._reminder_elapsed),
                        "microbreak_presence": micro["presence_seconds"],
                        "no_blink": float(no_blink_sec),
                        "total": int(self._detector.blink_count),
                        "alert_level": level,
                        "session_sec": int(time.time() - self._session_start),
                        "minute_history": list(self._minute_history),
                        "minute_valid_seconds": list(self._minute_valid_history),
                    })

                if frame_count % 3 == 0:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, _ = rgb.shape
                    img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
                    self.frameReady.emit(img)

                self.msleep(10)

        except Exception as error:
            if not self._stop_requested.is_set():
                self.errorReported.emit(str(error))
        finally:
            self._running = False
            if cap is not None:
                cap.release()
            if self._alert:
                self._alert.stop()
            if self._detector:
                self._detector.release()


# ═══════════════════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════════════════
class DrylessApp(QMainWindow):
    """无边框主窗口：1240×780。"""

    RESIZE_MARGIN = 6
    pausedChanged = pyqtSignal(bool)
    cameraStateChanged = pyqtSignal(str)
    soundChanged = pyqtSignal(bool)
    trayHidden = pyqtSignal()

    def __init__(self, start_worker=True):
        super().__init__()
        install_no_hover_popups()
        self.setWindowTitle("Dryless")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setMinimumSize(1100, 700)
        self.resize(1240, 780)

        central = QWidget(self)
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # root rounded card（无阴影 — 防止子控件文字抗锯齿出现色块）
        self._root = QWidget(central)
        self._root.setObjectName("RootCard")
        self._root.setStyleSheet(
            f"QWidget#RootCard{{background:{T.C_BG};"
            f"border:1px solid {T.C_BORDER}; border-radius:{T.R_WINDOW}px;}}"
        )
        outer.addWidget(self._root)

        lay = QHBoxLayout(self._root)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar(self._root)
        self.sidebar.closeClicked.connect(self._do_close)
        self.sidebar.minClicked.connect(self.showMinimized)
        self.sidebar.maxClicked.connect(self._toggle_max)
        self.sidebar.navChanged.connect(self._on_nav)
        self.sidebar.soundToggled.connect(self._on_sound)
        lay.addWidget(self.sidebar)

        # Content
        content = QWidget(self._root)
        content.setObjectName("Content")
        content.setStyleSheet(
            f"QWidget#Content{{background:{T.C_BG};"
            f"border-top-right-radius:{T.R_WINDOW}px;"
            f"border-bottom-right-radius:{T.R_WINDOW}px;}}"
        )
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        self.titlebar = TitleBar()
        self.titlebar.closeClicked.connect(self._do_close)
        self.titlebar.minClicked.connect(self.showMinimized)
        self.titlebar.maxClicked.connect(self._toggle_max)
        cv.addWidget(self.titlebar)

        # Stacked screens
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"QStackedWidget{{background:{T.C_BG};}}")

        # Every page owns a fixed viewport; no page scrolling or clipped scroll area.
        def _wrap(w):
            inner = QWidget()
            inner.setObjectName('PageContainer')
            inner.setStyleSheet(f'QWidget#PageContainer{{background:{T.C_BG};}}')
            il = QVBoxLayout(inner)
            il.setContentsMargins(24, 0, 24, 18)
            il.setSpacing(0)
            il.addWidget(w, 1)
            return inner

        self.monitor = MonitorScreen()
        self.stats = StatsScreen()
        self.settings = SettingsScreen()
        self.titlebar.setSoundControl(self.monitor._sound_button)
        for page in (self.monitor, self.stats, self.settings):
            self.titlebar.setPageHeader(page.page_header)
        self.titlebar.setPageHeader(self.monitor.page_header)
        self.settings.soundToggled.connect(self._on_sound_from_settings)
        self.settings.languageChanged.connect(self._on_language_changed)
        self.titlebar.languageChanged.connect(self._on_language_changed)
        self.monitor.statusChanged.connect(self.sidebar.setStatus)
        self.monitor._render_state()
        self.monitor.pauseToggled.connect(self.setPaused)
        self.monitor.previewToggled.connect(self.setPreviewVisible)
        self.monitor.soundToggled.connect(self._on_sound)
        self.monitor.settingsRequested.connect(lambda: self._on_nav("settings"))
        self.monitor.statisticsRequested.connect(lambda: self._on_nav("stats"))

        self.stack.addWidget(_wrap(self.monitor))
        self.stack.addWidget(_wrap(self.stats))
        self.stack.addWidget(_wrap(self.settings))

        cv.addWidget(self.stack, 1)
        lay.addWidget(content, 1)

        # Alerts never enter the content layout: the sidebar reserves a fixed slot.
        self.alert_strip = AlertStrip(self.sidebar.alert_host)
        self.alert_strip.dismissed.connect(self._dismiss_alert)
        self.sidebar.alert_host.layout().addWidget(self.alert_strip)


        # State
        self._dismissed_until_blink = False
        self._drag_pos: QPoint | None = None

        # Detector
        self._camera_state = "off"
        self._accept_camera = False
        self._tray_resident = False
        self._quit_requested = False
        self._worker_started = False
        self.worker = self._new_worker()
        self.titlebar.cameraToggled.connect(self.toggleCamera)
        self._paused = False
        self._closing = False
        self.sidebar.setStatus("waiting", t("status_waiting"))
        self._on_sound(config.SOUND_ENABLED)
        self.monitor.setPreviewVisible(config.SHOW_PREVIEW_ON_START)
        self._set_camera_state("off")
        apply_window_shape(self, T.R_WINDOW)
        if start_worker and config.CAMERA_ENABLED_ON_START:
            QTimer.singleShot(300, self._start_worker)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            self.sidebar.setFixedWidth(max(196,min(208,round(self.width()*.16))))

    # ── 窗口控制 ────────────────────────────────────
    def _new_worker(self):
        worker = DetectorWorker(self)
        # Queued events from a closed session must not revive the old UI.
        def forward(callback):
            return lambda *args: callback(*args) if worker is self.worker and self._accept_camera else None
        worker.captureReady.connect(forward(lambda: self._set_camera_state("running")))
        worker.frameReady.connect(forward(self._on_frame))
        worker.stats.connect(forward(self._on_stats))
        worker.alertTriggered.connect(forward(self.monitor.on_alert_triggered))
        worker.errorReported.connect(forward(self._camera_error))
        worker.alertErrorReported.connect(forward(self._on_alert_error))
        worker.minuteCommitted.connect(self.stats.update_stats)
        worker.finished.connect(lambda: self._camera_finished(worker))
        return worker

    def _set_camera_state(self, state):
        self._camera_state = state
        from widgets.soft_icon import set_camera_active, icon as state_icon
        set_camera_active(state == 'running')
        self.sidebar._buttons['monitor']._refresh()
        current_icon = state_icon('eye', 256)
        self.setWindowIcon(current_icon)
        QApplication.instance().setWindowIcon(current_icon)
        self.titlebar.setCameraState(state)
        self.monitor.setCameraState(state)
        self.cameraStateChanged.emit(state)

    def _start_worker(self):
        # A later startup callback cannot override an explicit stop click.
        if config.CAMERA_ENABLED_ON_START:
            self.setCameraEnabled(True, persist=False)

    def toggleCamera(self):
        self.setCameraEnabled(self._camera_state not in ("starting", "running"))

    def setCameraEnabled(self, enabled, persist=True):
        if self._closing or self._camera_state == "stopping":
            return
        if enabled and self._camera_state in ("running", "starting"):
            return
        if enabled and self.worker.isRunning():
            return
        if persist:
            config.CAMERA_ENABLED_ON_START = bool(enabled)
            config.save_config()
        if enabled:
            if self._worker_started or self.worker._stop_requested.is_set():
                previous = self.worker
                self.worker = self._new_worker()
                previous.deleteLater()
            self._worker_started = True
            self._accept_camera = True
            self._dismissed_until_blink = False
            self.monitor.resetSession()
            self.sidebar.setSession(_fmt_session(0))
            self.worker.setPaused(self._paused)
            self.worker.setSoundEnabled(config.SOUND_ENABLED)
            self._set_camera_state("starting")
            self.worker.start()
        else:
            self._accept_camera = False
            AUDIO.stop()
            self.alert_strip.setState(-1, 0)
            self.titlebar.setAlert(-1)
            self._set_camera_state("stopping" if self.worker.isRunning() else "off")
            self.worker.request_stop()

    def _camera_error(self, message):
        self._accept_camera = False
        AUDIO.stop()
        self._set_camera_state("error")
        self.titlebar._camera_btn.setEnabled(False)
        self._on_error(message)
        self.worker.request_stop()

    def _camera_finished(self, worker):
        if worker is not self.worker:
            return
        self._accept_camera = False
        if self._camera_state != "error":
            self._set_camera_state("off")
        else:
            self.titlebar.setCameraState("error")
        self.cameraStateChanged.emit(self._camera_state)

    def requestQuit(self):
        self._quit_requested = True
        self.close()

    def _do_close(self):
        self.close()

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def closeEvent(self, e):
        if self._tray_resident and not self._quit_requested:
            e.ignore()
            self.hide()
            self.trayHidden.emit()
            return
        self._closing = True
        self._accept_camera = False
        AUDIO.stop()
        try:
            if not self.worker.stop():
                e.ignore()
                QTimer.singleShot(200, self.close)
                return
        except Exception as ex:
            print(f"[ui] Failed to stop detector thread: {ex}", file=sys.stderr)
        super().closeEvent(e)
        if self._quit_requested:
            QApplication.instance().quit()

    # ── 拖拽移动（标题栏区域）────────────────────────
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            # The unified page heading is also the draggable window header.
            if e.position().y() < self.titlebar.height() and e.position().x() > self.sidebar.width():
                self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            if self.isMaximized():
                self.showNormal()
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    # ── 业务 ────────────────────────────────────────
    def _on_nav(self, name: str):
        titles = {
            "monitor": t("nav_monitor"),
            "stats": t("nav_stats"),
            "settings": t("nav_settings"),
        }
        self.sidebar.setActive(name)
        if name == "stats":
            self.stats.update_stats()
        if name == "settings":
            self.settings.retranslate()
        self.titlebar.setPageHeader({"monitor": self.monitor, "stats": self.stats, "settings": self.settings}[name].page_header)
        self.stack.setCurrentIndex({"monitor": 0, "stats": 1, "settings": 2}[name])

    def _on_sound(self, v):
        changed = config.SOUND_ENABLED != bool(v)
        config.SOUND_ENABLED = bool(v)
        if changed:
            config.save_config()
        self.sidebar.setSoundValue(v)
        self.settings.setSoundEnabled(v)
        self.monitor.setSoundEnabled(v)
        self.worker.setSoundEnabled(v)
        self.soundChanged.emit(bool(v))

    def _on_sound_from_settings(self, v):
        self._on_sound(v)

    def setPaused(self, paused):
        self._paused = bool(paused)
        self.worker.setPaused(paused)
        self.monitor.setPaused(paused)
        if paused:
            AUDIO.stop()
            self.titlebar.setAlert(-1)
            self.alert_strip.setState(-1, 0)
        self.pausedChanged.emit(self._paused)

    def setPreviewVisible(self, visible):
        config.SHOW_PREVIEW_ON_START = bool(visible)
        config.save_config()
        self.monitor.setPreviewVisible(visible)

    def _on_language_changed(self):
        """Retranslate all UI components when language switches."""
        self.sidebar.retranslate()
        self.settings.retranslate()
        self.monitor.retranslate()
        self.stats.retranslate()
        self.titlebar._refresh_lang_btn()
        self.alert_strip.retranslate()
        self.titlebar.setCameraState(self._camera_state)
        # Update current titlebar title
        idx = self.stack.currentIndex()
        names = ["monitor", "stats", "settings"]
        if idx < len(names):
            self._on_nav(names[idx])

    def _dismiss_alert(self):
        self._dismissed_until_blink = True
        self.alert_strip.setState(-1, 0)

    def _on_frame(self, img: QImage):
        self.monitor.camera.setFrame(img)

    def _on_stats(self, s: dict):
        level = s["alert_level"]
        self.sidebar.setSession(_fmt_session(s["session_sec"]))
        self.titlebar.setRate(s["rate"])
        self.monitor.camera.setStatus(s["face"], s["eye_open"])

        if self._dismissed_until_blink and s["no_blink"] < 1.0:
            self._dismissed_until_blink = False
        effective_level = -1 if (self._dismissed_until_blink or self._paused or s.get("microbreak_active") or not s["face"] or s.get("eye_ratio") is None) else level
        self.titlebar.setAlert(effective_level)
        self.alert_strip.setState(effective_level, s["no_blink"])

        # 让 monitor 使用"显示用"级别
        s2 = dict(s)
        s2["alert_level"] = effective_level
        s2["paused"] = self._paused
        self.monitor.update_state(s2)

    def _on_alert_error(self, msg: str):
        print(f"[ALERT ERROR] {msg}", file=sys.stderr)
        self.monitor.setAlertError(msg)

    def _on_error(self, msg: str):
        print(f"[ERROR] {msg}", file=sys.stderr)
        self.titlebar.setAlert(-1)
        self.alert_strip.setState(-1, 0)
        self.monitor.setError(msg)


def _fmt_session(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m {s}s"
