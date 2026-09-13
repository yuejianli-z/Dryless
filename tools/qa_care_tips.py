"""Carousel behavior and bilingual global-control geometry using isolated data."""
import os, sys, tempfile, json, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
profile=tempfile.TemporaryDirectory();os.environ['DRYLESS_DATA_DIR']=profile.name
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QLabel
from PyQt6.QtGui import QEnterEvent, QFontMetrics
from PyQt6.QtCore import Qt,QEvent,QPointF,QPoint,QRect
from PyQt6.QtTest import QTest
import ui,config
from widgets.care_tips import TIPS
from main import GLOBAL_QSS
app=QApplication([]);app.setStyle('Fusion');ui.load_bundled_fonts();app.setFont(ui.fnt(13));app.setStyleSheet(GLOBAL_QSS)
report={'checks':[]}
def check(name,value):
 report['checks'].append({'name':name,'pass':bool(value)})
 if not value:raise AssertionError(name)
def settle():app.processEvents();QTest.qWait(80);app.processEvents()
w=ui.DrylessApp(start_worker=False);w.show();w.activateWindow();w.resize(1100,700);settle()
tips=w.monitor.tips
try:
 check('no carousel action buttons',not tips.findChildren(QPushButton) and not hasattr(w.monitor,'_tip_next'))
 check('separate sibling module',tips.parentWidget() is w.monitor._state_section.parentWidget())
 check('global sound control',w.titlebar.isAncestorOf(w.monitor._sound_button))
 check('camera and sound equal size',w.titlebar._camera_btn.size()==w.monitor._sound_button.size())
 check('production carousel interval',tips._timer.interval()==20000)
 tips.clearFocus();QApplication.sendEvent(tips,QEvent(QEvent.Type.Leave));settle()
 check('visible card schedules carousel',tips._timer.isActive())
 index=tips._index
 QTest.qWait(20500)
 check('real twenty-second automatic advance',tips._index==(index+1)%len(TIPS))
 # Subsequent timer edge cases run faster while exercising the same Qt callbacks.
 tips._timer.setInterval(40)
 QApplication.sendEvent(tips,QEnterEvent(QPointF(),QPointF(),QPointF()))
 index=tips._index;QTest.qWait(100)
 check('hover pauses timer and content',not tips._timer.isActive() and tips._index==index)
 QApplication.sendEvent(tips,QEvent(QEvent.Type.Leave));settle()
 check('leaving resumes timer',tips._timer.isActive())
 tips.setFocus();settle();index=tips._index;QTest.qWait(100)
 check('keyboard focus pauses',tips.hasFocus() and not tips._timer.isActive() and tips._index==index)
 QTest.keyClick(tips,Qt.Key.Key_Right)
 check('keyboard navigation without buttons',tips._index==(index+1)%len(TIPS))
 tips.clearFocus();settle();tips.setAlertActive(True);index=tips._index;QTest.qWait(100)
 check('active reminder holds content',not tips._timer.isActive() and tips._index==index)
 tips.setAlertActive(False);settle();check('reminder end resumes',tips._timer.isActive())
 w._on_nav('stats');settle();check('hidden page stops timer',not tips._timer.isActive())
 w._on_nav('monitor');settle();check('return resumes timer',tips._timer.isActive())
 tips._timer.setInterval(20000);tips.setAlertActive(True)
 positions={}
 for lang in ('zh','en'):
  config.LANGUAGE=lang;w._on_language_changed();settle()
  for width,height in ((1100,700),(1240,780)):
   w.resize(width,height);settle()
   for page in ('monitor','stats','settings'):
    w._on_nav(page);settle()
    widgets=[w.titlebar._camera_btn,w.monitor._sound_button,w.titlebar._lang_btn]
    rects=[x.rect().translated(x.mapTo(w.titlebar,QPoint())) for x in widgets]
    check(f'{lang}-{width}-{page}-top-contained',all(w.titlebar.rect().contains(r) for r in rects))
    check(f'{lang}-{width}-{page}-top-no-overlap',not any(a.intersects(b) for i,a in enumerate(rects) for b in rects[i+1:]))
    key=(width,page)
    if lang=='zh':positions[key]=rects
    else:check(f'{width}-{page}-language-fixed-top',rects==positions[key])
   w._on_nav('monitor');settle()
   bounds=tips.geometry()
   for index in range(len(TIPS)):
    tips._index=index;tips.retranslate();settle()
    check(f'{lang}-{width}-tip-{index}-fixed-height',tips.geometry()==bounds)
    body=tips._body;fm=QFontMetrics(body.font())
    needed=fm.boundingRect(QRect(0,0,body.width(),1000),Qt.TextFlag.TextWordWrap,body.text())
    check(f'{lang}-{width}-tip-{index}-readable',needed.height()<=body.height())
    for child in tips.findChildren(QWidget):
     if child.isVisible():check(f'{lang}-{width}-tip-{index}-child-contained',tips.rect().contains(child.rect().translated(child.mapTo(tips,QPoint()))))
 check('control click does not open camera',not w.worker.isRunning())
 w.monitor._sound_button.click();check('top mute persists',config.SOUND_ENABLED==w.monitor._sound_button.isChecked())
except BaseException:report['error']=traceback.format_exc()
finally:
 w.close();app.processEvents();out=ROOT/'qa-output/tips.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'checks':len(report['checks']),'failed':[c for c in report['checks'] if not c['pass']],'error':report.get('error')}))
sys.exit(1 if report.get('error') else 0)
