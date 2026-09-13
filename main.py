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
QToolTip { background:#1A1816; color:#FFFFFF; border:1px solid #2A2824; padding:6px 10px; }
QMenu { background:#FBFDFC; border:1px solid #DDE7DF; border-radius:8px; padding:5px; }
QMenu::item { padding:8px 24px; }
QMenu::item:selected { background:#E3EEE6; color:#1A1A1A; }
"""

def create_tray(app, window, icon):
    """All UI actions stay on Qt's GUI thread."""
    tray = QSystemTrayIcon(icon, window)
    tray.setToolTip('Dryless')
    menu = build_menu(window)
    show_action = QAction(menu)
    pause_action = QAction(menu)
    pause_action.setCheckable(True)
    quit_action = QAction(menu)
    def show_window():
        window.showNormal()
        window.raise_()
        window.activateWindow()
    def refresh_labels():
        zh = config.LANGUAGE == 'zh'
        show_action.setText('打开 Dryless' if zh else 'Open Dryless')
        pause_action.setText('暂停提醒' if zh else 'Pause reminders')
        quit_action.setText('退出' if zh else 'Quit')
    show_action.triggered.connect(show_window)
    pause_action.triggered.connect(window.setPaused)
    window.pausedChanged.connect(pause_action.setChecked)
    quit_action.triggered.connect(window.close)
    menu.addAction(show_action)
    menu.addAction(pause_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    menu.aboutToShow.connect(refresh_labels)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: show_window() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    refresh_labels()
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
    window.setWindowIcon(icon)
    tray = create_tray(app, window, icon)
    app.aboutToQuit.connect(tray.hide)
    window.show()
    if "--stats" in sys.argv:
        window._on_nav("stats")
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
