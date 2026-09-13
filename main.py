"""Dryless application entry point and native desktop tray."""
import os
import sys
# Test entry points must isolate the profile before importing config/ui.
_test_profile = None
if "--self-test" in sys.argv or "--camera-smoke" in sys.argv:
    import tempfile
    _test_profile = tempfile.TemporaryDirectory(prefix="dryless-check-")
    os.environ["DRYLESS_DATA_DIR"] = _test_profile.name
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
import config
from ui import DrylessApp, fnt, load_bundled_fonts
from widgets.selection_popup import build_menu

def _resource(rel):
    return os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(__file__)), rel)

GLOBAL_QSS = """
QWidget { color:#1A1A1A; }
QLabel { background:transparent; border:none; }
QPushButton, QToolButton, QComboBox { outline:none; }
QPushButton:focus { border-color:#8AA594; }
QScrollBar:vertical { background:transparent; width:6px; margin:0; }
QScrollBar::handle:vertical { background:rgba(0,0,0,36); border-radius:3px; min-height:20px; }
QScrollBar::handle:vertical:hover { background:rgba(0,0,0,64); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:none; border:none; height:0; }
QScrollBar:horizontal { height:0px; }
QMenu { background:#FBFDFC; border:1px solid #DDE7DF; border-radius:8px; padding:5px; }
QMenu::item { padding:8px 24px; }
QMenu::item:selected { background:#E3EEE6; color:#1A1A1A; }
"""

def create_tray(app, window, icon):
    """The tray and main window share the same camera and reminder state."""
    from widgets.soft_icon import icon as glyph_icon
    from PyQt6.QtGui import QPixmap, QPainter, QColor
    from PyQt6.QtCore import Qt, QRectF
    import theme as T
    tray = QSystemTrayIcon(icon, window)
    menu = build_menu(window)
    actions = {key: QAction(menu) for key in ('show', 'camera', 'pause', 'sound', 'quit')}
    tray._actions = actions
    actions['pause'].setCheckable(True)
    actions['sound'].setCheckable(True)
    def show_window():
        if window.isMinimized():
            window.showNormal()
        else:
            window.show()
        window.raise_()
        window.activateWindow()
    def refresh(*_args):
        zh = config.LANGUAGE == 'zh'
        state = window._camera_state
        signature = (state, window._paused, config.SOUND_ENABLED, config.LANGUAGE,
                     window.monitor._status_lbl.text(), window.titlebar._camera_btn.isEnabled())
        if signature == getattr(tray, '_last_signature', None):
            return
        tray._last_signature = signature
        active = state in ('running', 'starting')
        labels = {
            'show': ('打开 Dryless', 'Open Dryless'),
            'camera': ('关闭摄像头', 'Stop camera') if active else ('开启摄像头', 'Start camera'),
            'pause': ('恢复提醒', 'Resume reminders') if window._paused else ('暂停提醒', 'Pause reminders'),
            'sound': ('声音提醒', 'Reminder sounds'),
            'quit': ('退出', 'Quit'),
        }
        for key, action in actions.items():
            action.setText(labels[key][0 if zh else 1])
        actions['camera'].setText(window.titlebar._camera_btn.accessibleName())
        actions['camera'].setEnabled(window.titlebar._camera_btn.isEnabled())
        actions['pause'].setEnabled(state == 'running')
        actions['pause'].setChecked(window._paused)
        actions['sound'].setChecked(config.SOUND_ENABLED)
        actions['sound'].setText(window.monitor._sound_button.accessibleName())
        actions['camera'].setIcon(glyph_icon('eye_open' if state == 'running' else 'eye_closed', 20))
        pix = QPixmap(32, 32); pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        glyph_icon('eye_open' if state == 'running' else 'eye_closed', 32).paint(painter, 0, 0, 32, 32)
        if state != 'off' and (window._paused or state != 'running'):
            color = T.C_TEXT3 if window._paused else (T.DANGER if state == 'error' else T.WARN)
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(color))
            painter.drawEllipse(QRectF(20, 20, 12, 12))
            if window._paused:
                painter.setBrush(QColor('#FFFFFF'))
                painter.drawRect(23, 23, 2, 6); painter.drawRect(27, 23, 2, 6)
        painter.end(); tray.setIcon(QIcon(pix))
        tray.setToolTip('')
    actions['show'].triggered.connect(show_window)
    actions['camera'].triggered.connect(window.toggleCamera)
    actions['pause'].triggered.connect(lambda: window.setPaused(not window._paused))
    actions['sound'].triggered.connect(window._on_sound)
    actions['quit'].triggered.connect(window.requestQuit)
    for key in ('show', 'camera', 'pause', 'sound'):
        menu.addAction(actions[key])
    menu.addSeparator(); menu.addAction(actions['quit'])
    menu.aboutToShow.connect(refresh)
    window.cameraStateChanged.connect(refresh)
    window.pausedChanged.connect(refresh)
    window.soundChanged.connect(refresh)
    window.monitor.statusChanged.connect(refresh)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: show_window() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    def explain_background():
        if getattr(tray, '_explained', False):
            return
        tray._explained = True
        tray.showMessage('Dryless', '仍在后台运行。右键托盘图标可控制摄像头或退出。' if config.LANGUAGE == 'zh' else 'Still running. Right-click the tray icon to control the camera or quit.')
    window.trayHidden.connect(explain_background)
    refresh()
    tray.show()
    return tray

def main():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('dryless.desktop')
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    icon = QIcon(_resource('icon.ico'))
    app.setWindowIcon(icon)
    load_bundled_fonts()
    app.setFont(fnt(13))
    app.setStyleSheet(GLOBAL_QSS)
    if "--self-test" in sys.argv or "--camera-smoke" in sys.argv:
        from release_checks import run
        flag = "--camera-smoke" if "--camera-smoke" in sys.argv else "--self-test"
        index = sys.argv.index(flag)
        if index + 1 >= len(sys.argv):
            return 2
        return run(app, sys.argv[index + 1], camera=(flag == "--camera-smoke"))
    window = DrylessApp()
    # DrylessApp applies the current camera-state icon to the window/taskbar.
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = create_tray(app, window, icon)
        window._tray_resident = True
        app.setQuitOnLastWindowClosed(False)
        app.aboutToQuit.connect(tray.hide)
    window.show()
    if "--stats" in sys.argv:
        window._on_nav("stats")
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
