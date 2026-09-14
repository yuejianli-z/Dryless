"""Ensure reminders never shift page content, navigation, or sidebar status."""
import os, sys, tempfile, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
profile=tempfile.TemporaryDirectory(prefix='dryless-alert-layout-')
os.environ['DRYLESS_DATA_DIR']=profile.name
import config,ui
from main import GLOBAL_QSS
from PyQt6.QtWidgets import QApplication,QWidget,QLabel,QPushButton
from PyQt6.QtCore import QPoint,Qt
from PyQt6.QtTest import QTest
app=QApplication([]);app.setStyle('Fusion');ui.load_bundled_fonts();app.setStyleSheet(GLOBAL_QSS)
w=ui.DrylessApp(start_worker=False);w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating,True);w.show();w._set_camera_state('running')
checks=[]
def check(name,result):checks.append({'name':name,'pass':bool(result)})
def settle():app.processEvents();QTest.qWait(30);app.processEvents()
def geometry():
    targets=[w.titlebar,w.stack,w.monitor.camera,w.monitor.metrics,w.monitor.trend,w.sidebar.alert_host,w.sidebar._status_tile,w.sidebar._project_button,*w.sidebar._buttons.values()]
    return [(x.mapTo(w,QPoint()).x(),x.mapTo(w,QPoint()).y(),x.width(),x.height()) for x in targets]
def state(level=-1,**extra):
    s=dict(face=True,eye_open=True,eye_ratio=.8,no_blink=2.4 if level<0 else 8+level*5,reminder_elapsed=2.4 if level<0 else 8+level*5,
           rate=18.,rolling_rate=18.,rolling_valid_seconds=60.,total=75,session_sec=240,alert_level=level,microbreak_presence=240,minute_history=[18,20,21],minute_valid_seconds=[60]*3)
    s.update(extra);w._on_stats(s);settle()
try:
    for lang in ('zh','en'):
        config.LANGUAGE=lang;w._on_language_changed()
        for size in ((1100,700),(1240,780)):
            w.resize(*size);settle()
            for page in ('monitor','stats','settings'):
                w._on_nav(page);state();before=geometry();prefix=f'{lang}-{size[0]}-{page}'
                check(prefix+' hidden',not w.alert_strip.isVisible())
                for level in (0,1,2,-1,2,-1):
                    state(level)
                    check(prefix+f' level {level} no movement',geometry()==before)
                    check(prefix+f' level {level} visibility',w.alert_strip.isVisible()==(level>=0))
                state(1)
                children=w.alert_strip.findChildren(QWidget)
                check(prefix+' reminder controls inside',all(w.alert_strip.rect().contains(x.rect().translated(x.mapTo(w.alert_strip,QPoint()))) for x in children if isinstance(x,(QLabel,QPushButton))))
                check(prefix+' no reminder tooltip',all(not x.toolTip() for x in children))
                w.alert_strip._btn.click();settle()
                check(prefix+' dismissed without movement',not w.alert_strip.isVisible() and geometry()==before)
                state(2);check(prefix+' dismissal persists until blink',not w.alert_strip.isVisible())
                state(no_blink=0);state(1);check(prefix+' next blink allows new reminder',w.alert_strip.isVisible())
                w.setPaused(True);settle();check(prefix+' pause without movement',not w.alert_strip.isVisible() and geometry()==before)
                w.setPaused(False);state(1,microbreak_active=True);check(prefix+' break without movement',not w.alert_strip.isVisible() and geometry()==before)
                state(1);state(face=False,eye_ratio=None);check(prefix+' lost face without movement',not w.alert_strip.isVisible() and geometry()==before)
    w._on_nav('monitor');w.resize(1100,700);state(1)
    before=geometry();config.LANGUAGE='zh';w._on_language_changed();settle()
    check('active card translates immediately',w.alert_strip._btn.text()=='收起')
    check('translation does not change geometry',geometry()==before)
finally:
    w.requestQuit();app.processEvents();profile.cleanup()
out=ROOT/'qa-output/alert-layout';out.mkdir(parents=True,exist_ok=True)
(out/'report.json').write_text(json.dumps({'checks':checks,'hardware_used':False},indent=2),encoding='utf-8')
failed=[x for x in checks if not x['pass']]
print(json.dumps({'checks':len(checks),'failed':failed},ensure_ascii=False))
sys.exit(bool(failed))
