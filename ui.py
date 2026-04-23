"""
Dryless PyQt6 main window.

- Frameless desktop window with custom window controls
- Dark sidebar with a light content area and alert strip
- Monitor, stats, and settings screens
"""
from __future__ import annotations

import os
import sys
import time
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
from alert import AlertManager
import history_store
from i18n import t

import theme as T
from widgets import Sidebar, TitleBar, AlertStrip
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
    _FONT_LOADED = True


def fnt(size, weight=400):
    f = QFont(T.FONT_UI)
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
    frameReady = pyqtSignal(QImage)
    stats = pyqtSignal(dict)
    alertTriggered = pyqtSignal(int)  # level
    errorReported = pyqtSignal(str)
    minuteCommitted = pyqtSignal()    # 每完成一个分钟桶时触发，通知统计页刷新

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._paused = False
        self._sound_enabled = True
        self._detector: BlinkDetector | None = None
        self._alert: AlertManager | None = None

        self._minute_history = deque(maxlen=60)
        self._session_start = time.time()
        self._last_minute_bucket = -1
        self._minute_blinks = 0
        self._last_alert_round_seen = -1

    def stop(self):
        self._running = False
        self.wait(1500)

    def setPaused(self, paused: bool):
        self._paused = bool(paused)
        if self._detector:
            self._detector.reset()

    def setSoundEnabled(self, enabled: bool):
        self._sound_enabled = bool(enabled)
        if self._alert:
            self._alert.enabled = bool(enabled) and not self._paused

    def run(self):
        try:
            self._detector = BlinkDetector()
        except Exception as e:
            self.errorReported.emit(t("err_detector", e=e))
            return
        try:
            self._alert = AlertManager()
            self._alert.enabled = self._sound_enabled
        except Exception as e:
            self._alert = None
            self.errorReported.emit(t("err_alert", e=e))

        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        if not cap.isOpened():
            self.errorReported.emit(t("err_camera", index=config.CAMERA_INDEX))
            return

        self._running = True
        frame_count = 0

        while self._running:
            ok, frame = cap.read()
            if not ok:
                self.msleep(30)
                continue
            frame_count += 1

            if frame_count % max(1, config.PROCESS_EVERY_N_FRAMES) == 0:
                frame, blinked, no_blink_sec, _ = self._detector.process_frame(frame)

                if blinked:
                    self._minute_blinks += 1
                    if self._alert:
                        self._alert.reset()
                    self._last_alert_round_seen = -1

                if self._alert and not self._paused and self._detector.face_detected:
                    prev_round = -1
                    if no_blink_sec >= config.NO_BLINK_ALERT_SEC:
                        overtime = no_blink_sec - config.NO_BLINK_ALERT_SEC
                        prev_round = int(overtime // max(1, config.ALERT_INTERVAL_SEC))
                    self._alert.check_and_alert(no_blink_sec)
                    if prev_round >= 0 and prev_round != self._last_alert_round_seen:
                        self._last_alert_round_seen = prev_round
                        self.alertTriggered.emit(min(3, prev_round))
                elif not self._detector.face_detected and self._alert:
                    self._alert.reset()

                # 分钟聚合
                cur_min = int((time.time() - self._session_start) / 60)
                if cur_min != self._last_minute_bucket:
                    if self._last_minute_bucket >= 0:
                        from datetime import datetime
                        self._minute_history.append(float(self._minute_blinks))
                        history_store.append_minute(
                            self._minute_blinks,
                            self._last_minute_bucket,
                            datetime.now().strftime("%H:%M"),
                        )
                        self.minuteCommitted.emit()
                    self._minute_blinks = 0
                    self._last_minute_bucket = cur_min

                # rate 估算，clamp 到生理上限 30次/分钟
                elapsed_min = max(1 / 60.0, (time.time() - self._session_start) / 60.0)
                rate = self._detector.blink_count / elapsed_min
                if cur_min >= 0:
                    sec_in = max(1.0, (time.time() - self._session_start) - cur_min * 60.0)
                    near = self._minute_blinks / sec_in * 60.0
                    rate = (rate + near) / 2.0
                rate = min(rate, 30.0)

                level = -1
                base = config.NO_BLINK_ALERT_SEC
                iv = config.ALERT_INTERVAL_SEC
                if no_blink_sec >= base + 3 * iv:
                    level = 3
                elif no_blink_sec >= base + 2 * iv:
                    level = 2
                elif no_blink_sec >= base + iv:
                    level = 1
                elif no_blink_sec >= base:
                    level = 0

                self.stats.emit({
                    "face": self._detector.face_detected,
                    "eye_open": self._detector._is_open,
                    "eye_ratio": float(self._detector._ratio) if self._detector._ratio is not None else None,
                    "rate": float(rate),
                    "no_blink": float(no_blink_sec),
                    "total": int(self._detector.blink_count),
                    "alert_level": level,
                    "session_sec": int(time.time() - self._session_start),
                    "minute_history": list(self._minute_history),
                })

            if frame_count % 3 == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, _ = rgb.shape
                img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
                self.frameReady.emit(img)

            self.msleep(10)

        cap.release()
        if self._detector:
            self._detector.release()


# ═══════════════════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════════════════
class DrylessApp(QMainWindow):
    """无边框主窗口：1240×780。"""

    RESIZE_MARGIN = 6

    def __init__(self):
        super().__init__()
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
            f"border:1px solid #000000; border-radius:0px;}}"
        )
        outer.addWidget(self._root)

        lay = QHBoxLayout(self._root)
        lay.setContentsMargins(0, 0, 0, 0)
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

        # scroll wrapper helper
        from PyQt6.QtWidgets import QScrollArea

        def _wrap(w):
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.Shape.NoFrame)
            sa.setStyleSheet(f"QScrollArea{{background:{T.C_BG};}}")
            inner = QWidget()
            inner.setStyleSheet(f"background:{T.C_BG};")
            il = QVBoxLayout(inner)
            il.setContentsMargins(16, 14, 16, 18)
            il.addWidget(w)
            il.addStretch(1)
            sa.setWidget(inner)
            return sa

        self.monitor = MonitorScreen()
        self.stats = StatsScreen()
        self.settings = SettingsScreen()
        self.settings.soundToggled.connect(self._on_sound_from_settings)
        self.settings.languageChanged.connect(self._on_language_changed)
        self.titlebar.languageChanged.connect(self._on_language_changed)

        self.stack.addWidget(_wrap(self.monitor))
        self.stack.addWidget(_wrap(self.stats))
        self.stack.addWidget(_wrap(self.settings))

        cv.addWidget(self.stack, 1)
        lay.addWidget(content, 1)

        # AlertStrip 悬浮在内容区底部，不参与布局
        self.alert_strip = AlertStrip(content)
        self.alert_strip.dismissed.connect(self._dismiss_alert)
        self.alert_strip.raise_()
        content.installEventFilter(self)


        # State
        self._dismissed_until_blink = False
        self._drag_pos: QPoint | None = None

        # Detector
        self.worker = DetectorWorker(self)
        self.worker.frameReady.connect(self._on_frame)
        self.worker.stats.connect(self._on_stats)
        self.worker.alertTriggered.connect(self.monitor.on_alert_triggered)
        self.worker.errorReported.connect(self._on_error)
        self.worker.minuteCommitted.connect(self.stats.update_stats)
        QTimer.singleShot(300, self.worker.start)

    # ── 窗口控制 ────────────────────────────────────
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Resize:
            w = obj.width()
            h = obj.height()
            self.alert_strip.setGeometry(0, h - 56, w, 56)
        return super().eventFilter(obj, event)

    def _do_close(self):
        self.close()

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def closeEvent(self, e):
        try:
            self.worker.stop()
        except Exception as ex:
            print(f"[ui] Failed to stop detector thread: {ex}", file=sys.stderr)
        super().closeEvent(e)

    # ── 拖拽移动（标题栏区域）────────────────────────
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            # 只有落在顶部 42px（titlebar + 上方留白）内才允许拖动
            if e.position().y() < 60 and e.position().x() > 200:
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
        self.titlebar.setTitle(titles.get(name, name))
        self.stack.setCurrentIndex({"monitor": 0, "stats": 1, "settings": 2}[name])

    def _on_sound(self, v):
        self.worker.setSoundEnabled(v)

    def _on_sound_from_settings(self, v):
        self.sidebar.setSoundValue(v)
        self.worker.setSoundEnabled(v)

    def _on_language_changed(self):
        """Retranslate all UI components when language switches."""
        self.sidebar.retranslate()
        self.settings.retranslate()
        self.monitor.retranslate()
        self.stats.retranslate()
        self.titlebar._refresh_lang_btn()
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
        self.sidebar.setFace(s["face"])
        self.sidebar.setSession(_fmt_session(s["session_sec"]))
        self.titlebar.setRate(s["rate"])
        self.monitor.camera.setStatus(s["face"], s["eye_open"])

        if self._dismissed_until_blink and s["no_blink"] < 1.0:
            self._dismissed_until_blink = False
        effective_level = -1 if self._dismissed_until_blink else level
        self.titlebar.setAlert(effective_level)
        self.alert_strip.setState(effective_level, s["no_blink"])

        # 让 monitor 使用"显示用"级别
        s2 = dict(s)
        s2["alert_level"] = effective_level
        self.monitor.update_state(s2)

    def _on_error(self, msg: str):
        print(f"[ERROR] {msg}", file=sys.stderr)
        self.monitor.camera.setError(msg)


def _fmt_session(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m {s}s"
