"""Dryless application entry point."""

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from tray import TrayManager
from ui import DrylessApp, fnt, load_bundled_fonts


def _resource(rel):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)


GLOBAL_QSS = """
QLabel { background: transparent; border: none; }
QWidget { outline: none; }
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(0,0,0,36);
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: rgba(0,0,0,64); }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical { background: none; border: none; height: 0; }
QScrollBar:horizontal { height: 0px; }
QToolTip {
    background:#1A1816; color:#E4DFD8;
    border:1px solid #2A2824; padding:4px 8px;
    border-radius:5px;
}
"""


if __name__ == "__main__":
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dryless.app")

    app = QApplication(sys.argv)
    icon = QIcon(_resource("icon.ico"))
    app.setWindowIcon(icon)
    load_bundled_fonts()
    app.setFont(fnt(13, 400))
    app.setStyleSheet(GLOBAL_QSS)
    window = DrylessApp()
    window.setWindowIcon(icon)

    tray = TrayManager(
        on_toggle_pause=lambda paused: window.worker.setPaused(paused),
        on_toggle_preview=lambda visible: window.show() if visible else window.hide(),
        on_quit=lambda: app.quit(),
        icon_path=_resource("icon.png"),
    )
    tray.start()

    window.show()
    sys.exit(app.exec())
