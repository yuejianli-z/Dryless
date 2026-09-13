"""No automatic hover popups in Dryless; explicit menus remain interactive."""
from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import QApplication, QWidget


class _NoHoverPopups(QObject):
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ToolTip:
            event.accept()
            return True
        # Covers explicit QToolTip.showText calls and tooltip windows created
        # by platform widgets, which can bypass the initial help event.
        if (event.type() == QEvent.Type.Show and isinstance(watched, QWidget)
                and watched.windowType() == Qt.WindowType.ToolTip):
            watched.hide()
            event.accept()
            return True
        return False


def install_no_hover_popups():
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("Create QApplication before installing interaction policy")
    if not hasattr(app, '_dryless_hover_policy'):
        app._dryless_hover_policy = _NoHoverPopups(app)
        app.installEventFilter(app._dryless_hover_policy)
    return app._dryless_hover_policy
