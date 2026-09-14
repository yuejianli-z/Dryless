"""Exercise hover suppression and retained information in native Qt widgets."""
import ast
import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
profile = tempfile.TemporaryDirectory(prefix='dryless-hover-qa-')
os.environ['DRYLESS_DATA_DIR'] = profile.name
import ui
import config
from main import GLOBAL_QSS, create_tray
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QHelpEvent, QIcon, QMouseEvent
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QSystemTrayIcon, QToolTip, QWidget
from PyQt6.QtTest import QTest
from widgets.selection_popup import build_menu

app = QApplication([])
app.setStyle('Fusion')
app.setQuitOnLastWindowClosed(False)
ui.load_bundled_fonts()
app.setFont(ui.fnt(13))
app.setStyleSheet(GLOBAL_QSS)
checks = []
exceptions = []
def record_exception(kind, value, tb):
    exceptions.append(str(value))
    traceback.print_exception(kind, value, tb)
sys.excepthook = record_exception

def check(name, passed, detail=None):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))

def settle():
    app.processEvents()
    QTest.qWait(50)

def no_popup():
    return not QToolTip.isVisible() and not any(
        w.isVisible() and w.windowType() == Qt.WindowType.ToolTip for w in app.topLevelWidgets())

def hover(widget):
    point = widget.rect().center()
    QTest.mouseMove(widget, point)
    app.sendEvent(widget, QHelpEvent(QEvent.Type.ToolTip, point, widget.mapToGlobal(point)))
    app.processEvents()
    return no_popup()

window = ui.DrylessApp(start_worker=False)
window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
window.show()
window.resize(1100, 700)
base = dict(face=True, eye_open=True, eye_ratio=.8, no_blink=4., reminder_elapsed=4.,
            rate=16., rolling_rate=16., rolling_valid_seconds=60., total=123, session_sec=700,
            alert_level=-1, microbreak_presence=700., minute_history=[12, 18, 16],
            minute_valid_seconds=[60, 60, 60])
try:
    # Audit every current desktop source used by the shipped entry point.
    sources = [ROOT / 'main.py', ROOT / 'ui.py'] + list((ROOT / 'screens').glob('*.py')) + list((ROOT / 'widgets').glob('*.py'))
    entries = []
    for path in sources:
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr == 'setToolTip' and node.args:
                if not (isinstance(node.args[0], ast.Constant) and node.args[0].value == ''):
                    entries.append(f'{path.relative_to(ROOT)}:{node.lineno}')
            if node.func.attr == 'showText' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'QToolTip':
                entries.append(f'{path.relative_to(ROOT)}:{node.lineno}')
    check('no active desktop hover popup source', not entries, entries)
    with patch.object(QSystemTrayIcon, 'show'):
        tray = create_tray(app, window, QIcon())
    for lang in ('zh', 'en'):
        config.LANGUAGE = lang
        window._on_language_changed()
        for state in ('running', 'off', 'error', 'running'):
            window._set_camera_state(state)
            window._on_stats(base)
            for paused in (False, True):
                window.setPaused(paused)
                window._on_stats(base)
                settle()
                tag = f'{lang}-{state}-{paused}'
                check(tag + ' pause has no tooltip', not window.monitor._pause_button.toolTip())
                check(tag + ' pause hover', hover(window.monitor._pause_button))
                check(tag + ' native tray has no tooltip', tray.toolTip() == '')
        window.setPaused(False)
        for page in ('monitor', 'stats', 'settings'):
            window._on_nav(page)
            indexes = range(3) if page == 'settings' else (0,)
            for index in indexes:
                if page == 'settings':
                    window.settings._tabs[index].click()
                settle()
                owned = [w for w in window.findChildren(QWidget) if w.isVisibleTo(window)]
                tips = [(type(w).__name__, w.toolTip()) for w in owned if w.toolTip()]
                check(f'{lang}-{page}-{index} no widget tooltip', not tips, tips)
                check(f'{lang}-{page}-{index} hover sweep', all(hover(w) for w in owned))
    window._on_nav('monitor')
    window._set_camera_state('running')
    window._on_stats(base)
    QTest.mouseMove(window.monitor._pause_button, window.monitor._pause_button.rect().center())
    QTest.qWait(1200)
    check('pause real dwell beyond tooltip delay', no_popup())

    # A future component can accidentally set a tooltip: the policy must still
    # prevent it, including an explicit showText which bypasses help events.
    future = QPushButton('Future control', window)
    future.setToolTip('Must never appear')
    future.show()
    check('new dynamic component blocked', hover(future))
    QToolTip.showText(window.mapToGlobal(QPoint(450, 80)), 'Must never appear', future)
    settle()
    check('explicit tooltip window blocked', no_popup())
    future.hide()

    menu = build_menu(window)
    action = menu.addAction('Normal menu item')
    triggered = []
    action.triggered.connect(lambda: triggered.append(True))
    menu.popup(window.mapToGlobal(QPoint(430, 90)))
    settle()
    check('explicit menu still opens', menu.isVisible())
    QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
    check('explicit menu still selects', triggered == [True])

    window._on_nav('stats')
    chart = window.stats._chart
    start = datetime(2026, 9, 1)
    points = [dict(start=start + timedelta(days=i), end=start + timedelta(days=i+1),
                   minutes=60*(i+1), average=12.+i, total=(12+i)*60*(i+1),
                   recorded_days=1, calendar_days=1, partial=False) for i in range(4)]
    window.stats._empty.hide()
    chart.show()
    for lang in ('zh', 'en'):
        chart.set_language(lang)
        chart.set_data(points, 'day')
        settle()
        before = (chart.geometry().getRect(), chart.canvas.geometry().getRect())
        index, point, radius = chart.canvas._hits[0]
        QTest.mouseMove(chart.canvas, QPoint(1, 1))
        settle()
        QTest.mouseMove(chart.canvas, point.toPoint())
        app.sendEvent(chart.canvas, QMouseEvent(QEvent.Type.MouseMove, point,
                      QPointF(chart.canvas.mapToGlobal(point.toPoint())),
                      Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        settle()
        check(lang + ' bubble values inline', all(s in chart.detail.text() for s in ('2026-09-01', '12.0', '720', '1/1')),
              chart.detail.text())
        check(lang + ' bubble no popup', no_popup())
        chart.canvas.setFocus()
        QTest.keyClick(chart.canvas, Qt.Key.Key_End)
        settle()
        check(lang + ' keyboard reads last record inline', '2026-09-04' in chart.detail.text())
        check(lang + ' hover never shifts chart', before == (chart.geometry().getRect(), chart.canvas.geometry().getRect()))
        check(lang + ' inline text fits', all(chart.detail.fontMetrics().horizontalAdvance(line) <= chart.detail.width()
                                              for line in chart.detail.text().splitlines()))
        out = ROOT / 'qa-output/no-hover'
        out.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(out / (lang + '-statistics.png')))
    chart.set_data([], 'month')
    check('empty period clears old readout', chart.detail.text() == 'No records yet')
    window.settings._preview_failed('Audio device unavailable')
    check('audio error remains accessible', window.settings._audio_note.accessibleDescription() == 'Audio device unavailable'
          and bool(window.settings._audio_note.text()) and not window.settings._audio_note.toolTip())
    window.monitor.camera.setError('Camera unavailable')
    check('camera error remains accessible', window.monitor.camera.accessibleDescription() == 'Camera unavailable')
finally:
    window.requestQuit()
    app.processEvents()
    profile.cleanup()

out = ROOT / 'qa-output/no-hover'
out.mkdir(parents=True, exist_ok=True)
report = dict(checks=checks, exceptions=exceptions, hardware_used=False)
(out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
failed = [c for c in checks if not c['passed']]
print(json.dumps(dict(checks=len(checks), failed=failed, exceptions=exceptions), ensure_ascii=False))
sys.exit(1 if failed or exceptions else 0)
