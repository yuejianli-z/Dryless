"""Desktop rendering/interaction checks with synthetic data, never live camera data."""
import os, sys, json, tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
profile = tempfile.TemporaryDirectory(prefix='dryless-live-qa-')
os.environ['DRYLESS_DATA_DIR'] = profile.name
import ui, config
from main import GLOBAL_QSS
from PyQt6.QtWidgets import QApplication, QToolTip
from PyQt6.QtCore import QEvent, QPoint, Qt
from PyQt6.QtGui import QHelpEvent
from PyQt6.QtTest import QTest
from widgets.time_bubble_chart import TimeBubbleChart, _color, COLOR_HIGH

app=QApplication([]);app.setStyle('Fusion');ui.load_bundled_fonts();app.setStyleSheet(GLOBAL_QSS)
checks=[]
def check(name, value):
    checks.append({'name':name, 'pass':bool(value)})

w=ui.DrylessApp(start_worker=False);w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating,True);w.show();w.resize(1100,700)
w._set_camera_state('running');w._accept_camera=True
base=dict(face=True, eye_ratio=.8, eye_open=True, rate=45., rolling_rate=45., rolling_valid_seconds=60., no_blink=9., reminder_elapsed=9., total=900, session_sec=4000, alert_level=0, microbreak_presence=300., minute_history=[12, 22], minute_valid_seconds=[60,60])
screen=w.monitor;metrics=screen.metrics
try:
    w._on_stats(base);app.processEvents()
    check('uncapped rolling value',metrics.rate==45)
    check('arc expands its labelled scale',metrics._ring_scale==60)
    check('blink progress actual interval',metrics.blink_progress==.5)
    check('microbreak uses presence not runtime',metrics.break_progress==.25)
    w._on_stats(dict(base,no_blink=0,reminder_elapsed=0));check('blink resets progress',metrics.blink_progress==0)
    w._on_stats(dict(base,no_blink=80,reminder_elapsed=80));check('overdue saturates without looping',metrics.blink_progress==1)
    w._on_stats(dict(base,rolling_rate=None,rolling_valid_seconds=5));check('startup not fabricated zero',metrics.rate is None)
    w._on_stats(dict(base,rolling_rate=0));check('valid zero preserved',metrics.rate==0)
    w._on_stats(dict(base,face=False,eye_ratio=None));check('lost tracking neutral',metrics.rate is None and metrics.blink_progress==0)
    w.setPaused(True);w._on_stats(base);check('pause stops reminder bars but retains recording',metrics.rate==45 and metrics.blink_progress==0 and metrics.break_progress==0)
    w.setPaused(False);w._on_stats(dict(base,microbreak_active=True));check('break suppresses blink progress',metrics.blink_progress==0)
    w._set_camera_state('off');check('camera off disables live display',metrics.rate is None and metrics.blink_progress==0 and metrics.break_progress==0)
    w._set_camera_state('running');w._on_stats(dict(base,paused=False))
    geometries=[]
    for lang in ('zh','en'):
        config.LANGUAGE=lang;w._on_language_changed();app.processEvents()
        geometries.append((metrics.geometry().getRect(),screen._state_section.geometry().getRect()))
        check(lang+' ring fits',metrics.rect().contains(metrics._ring_rect.toAlignedRect()))
        check(lang+' ring clears break',metrics._ring_rect.bottom()<metrics._break_rect.top())
    check('language does not move metrics',geometries[0]==geometries[1])
    plot,_,points=screen.trend._geometry()
    with patch.object(QToolTip,'showText') as popup:
        QTest.mouseMove(screen.trend,points[-1].toPoint());QTest.qWait(850)
        app.sendEvent(screen.trend,QHelpEvent(QEvent.Type.ToolTip,points[-1].toPoint(),screen.trend.mapToGlobal(points[-1].toPoint())))
        check('rhythm hover has no popup',not popup.called and not QToolTip.isVisible())
        QTest.mouseClick(screen.trend,Qt.MouseButton.LeftButton,pos=points[-1].toPoint())
        check('exact minute remains available inline',screen.trend._selected==1 and not popup.called)
        c=TimeBubbleChart();c.show();app.processEvents()
        app.sendEvent(c.legend,QHelpEvent(QEvent.Type.ToolTip,QPoint(20,20),c.legend.mapToGlobal(QPoint(20,20))))
        check('statistics legend has no hover popup',not popup.called and not QToolTip.isVisible())
        c.close()
    check('shared high colour softened',_color(22,16).name()==COLOR_HIGH.lower() and _color(22,16).saturationF()<.20)
finally:
    w.close();app.processEvents();profile.cleanup()
out=ROOT/'qa-output/live';out.mkdir(parents=True,exist_ok=True)
(out/'report.json').write_text(json.dumps({'checks':checks,'hardware_used':False},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(checks),'failed':[c for c in checks if not c['pass']]},ensure_ascii=False))
sys.exit(1 if any(not c['pass'] for c in checks) else 0)
