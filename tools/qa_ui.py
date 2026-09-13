import os,sys,json,math,tempfile,traceback
from pathlib import Path
from datetime import date,timedelta
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'qa-output/ui';OUT.mkdir(parents=True,exist_ok=True)
profile=tempfile.TemporaryDirectory(prefix='isolated-',dir=OUT);os.environ['DRYLESS_DATA_DIR']=profile.name;sys.path.insert(0,str(ROOT))
Path(profile.name,'config.json').write_text(json.dumps({'LANGUAGE':'zh','SOUND_ENABLED':False,'SHOW_PREVIEW_ON_START':False}),encoding='utf8')
history={'days':{}}
for i in range(30):
 if i%9==3:continue
 history['days'][(date.today()-timedelta(days=i)).isoformat()]=[{'minute':j,'time':f'{9+j//60:02}:{j%60:02}','blinks':max(0,round(16+8*math.sin(i/3)+j%3))} for j in range(25+i*6)]
Path(profile.name,'blink_data.json').write_text(json.dumps(history),encoding='utf8')
from PyQt6.QtCore import Qt,QPoint,qInstallMessageHandler
from PyQt6.QtWidgets import QApplication,QAbstractScrollArea,QLabel,QPushButton,QComboBox,QWidget
from PyQt6.QtGui import QImage,QColor,QPainter,QFont
from PyQt6.QtTest import QTest
import config,ui
from main import GLOBAL_QSS
report={'checks':[],'screens':[],'exceptions':[],'qt_messages':[]}
sys.excepthook=lambda k,v,t:report['exceptions'].append(''.join(traceback.format_exception(k,v,t)))
qInstallMessageHandler(lambda k,c,m:report['qt_messages'].append(m))
app=QApplication([]);app.setStyle('Fusion');app.setQuitOnLastWindowClosed(False);ui.load_bundled_fonts();app.setFont(ui.fnt(13));app.setStyleSheet(GLOBAL_QSS)
def check(n,v,d=None):report['checks'].append({'name':n,'pass':bool(v),'detail':d})
def settle():app.processEvents();QTest.qWait(65);app.processEvents()
def shot(name,width=None,height=None):
 settle();page=window.stack.currentWidget();screen=(window.monitor,window.stats,window.settings)[window.stack.currentIndex()]
 path=OUT/(name+'.png');window.grab().save(str(path));report['screens'].append({'name':name,'path':str(path),'size':[window.width(),window.height()],'screen':[screen.width(),screen.height()]})
 if width:check(name+'-window-size',(window.width(),window.height())==(width,height),(window.width(),window.height()))
 check(name+'-plain-page',not isinstance(page,QAbstractScrollArea))
 scroll=[(type(w).__name__,w.verticalScrollBar().maximum()) for w in screen.findChildren(QAbstractScrollArea) if w.isVisible()]
 check(name+'-no-vertical-range',all(v==0 for _,v in scroll),scroll)
 outside=[]
 for w in screen.findChildren(QWidget):
  if not w.isVisibleTo(screen) or w.isWindow() or w.window()!=window or not isinstance(w,(QLabel,QPushButton,QComboBox)):continue
  p=w.mapTo(screen,QPoint(0,0));r=w.rect().translated(p)
  if not screen.rect().adjusted(-1,-1,1,1).contains(r):outside.append((type(w).__name__,getattr(w,'text',lambda:'' )()[:45],r.getRect()))
 check(name+'-all-controls-inside',not outside,outside)
window=None
try:
 with patch.object(ui.cv2,'VideoCapture',side_effect=AssertionError('QA no camera')) as cam,patch.object(ui.DetectorWorker,'start',side_effect=AssertionError('QA no worker')) as worker:
  window=ui.DrylessApp(start_worker=False);window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating,True);window.show();screen=window.monitor
  preview=QImage(640,480,QImage.Format.Format_RGB32);preview.fill(QColor('#373737'));p=QPainter(preview);p.setPen(QColor('#FFFFFF'));p.setFont(QFont('Segoe UI',18));p.drawText(preview.rect(),Qt.AlignmentFlag.AlignCenter,'CAMERA TEST FRAME\n640 × 480');p.end();window._on_frame(preview)
  base=dict(face=True,eye_open=True,eye_ratio=.85,no_blink=2.4,rate=7.3,total=191,alert_level=-1,session_sec=676,minute_history=[12,18,16,20,19,14,18,17,22,18,16],minute_valid_seconds=[60]*11)
  check('preview-preference-restored',not screen._preview_visible)
  check('camera-default-off',window._camera_state=='off' and not window._accept_camera)
  window._set_camera_state('running');window.setPreviewVisible(True)
  for lang in ('zh','en'):
   window._camera_state='running';config.LANGUAGE=lang;window._on_language_changed()
   for width,height in ((1240,780),(1100,700)):
    window.resize(width,height);window._on_nav('monitor')
    for tag,extra in [('normal',{}),('no-face',dict(face=False,eye_ratio=None,minute_history=[0]*11,minute_valid_seconds=[0]*11)),('alert',dict(no_blink=14.2,alert_level=1))]:
     window._on_stats(dict(base,**extra));shot(f'{lang}-{width}-home-{tag}',width,height)
     # A 320x240 visible image is the minimum preview in the smallest window
     # with the alert strip visible; the rounded panel retains all its padding.
     check(f'{lang}-{width}-{tag}-camera-large',screen.camera.width()>=320 and screen.camera.height()>=240,[screen.camera.width(),screen.camera.height()])
    for page in ('stats','settings'):
     window._on_nav(page)
     if page=='settings':
      for index in range(3):
       window.settings._tabs[index].click();shot(f'{lang}-{width}-settings-{index}',width,height)
     else:
      for key in ('30','year','custom'):
       window.stats._range_changed(key);shot(f'{lang}-{width}-stats-{key}',width,height)
    window._on_stats(base)
  window._on_nav('monitor');window.resize(1100,700)
  check('no-session-dialog',not hasattr(screen,'_details_body') and not hasattr(screen,'_details_toggle'))
  window._on_stats(base);check('inline-run-time',screen._run_time_value.text()=='00:11:16')
  window.monitor.on_alert_triggered(0);check('inline-alert-count',int(screen._run_alerts_value.text())==sum(screen._alert_counts))
  screen._preview_button.click();shot('en-hidden-camera',1100,700);check('hide-does-not-stop',not screen._preview_visible and screen.camera._frame is not None);screen._preview_button.click()
  screen._pause_button.click();check('pause-propagates',window.worker._paused);shot('en-paused',1100,700);screen._pause_button.click()
  window._on_stats(dict(base,minute_history=[0],minute_valid_seconds=[60]));check('real-zero',screen.trend._data==[0])
  window._on_stats(dict(base,minute_history=[10,20,99],minute_valid_seconds=[30,60,20]));check('weighted-and-gap',screen._frequency_value.text()=='20.0' and screen.trend._data==[20,20,None])
  window._on_alert_error('Audio test error');window._on_stats(base);check('persistent-audio-error',not screen._sound_button.isEnabled());shot('en-audio-error',1100,700)
  window._on_error('Camera test unavailable');shot('en-camera-error',1100,700)
  font_failures=[]
  for page in ('monitor','stats','settings'):
   window._on_nav(page);settle()
   for widget in window.findChildren(QWidget):
    if not widget.isVisibleTo(window) or widget is window.sidebar._title_lbl:continue
    if isinstance(widget,(QLabel,QPushButton,QComboBox)) and widget.font().hintingPreference()!=QFont.HintingPreference.PreferVerticalHinting:font_failures.append([page,type(widget).__name__,getattr(widget,'text',lambda:'')()])
  check('consistent-visible-font-rendering',not font_failures,font_failures)
  check('history-preserved',json.loads(Path(profile.name,'blink_data.json').read_text(encoding='utf8'))==history)
  check('no-camera-worker',not cam.call_count and not worker.call_count)
except BaseException:report['exceptions'].append(traceback.format_exc())
finally:
 if window:window.close();app.processEvents()
 failed=[x for x in report['checks'] if not x['pass']]
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'checks':len(report['checks']),'failed':failed,'exceptions':report['exceptions'],'qt_messages':report['qt_messages'][-12:]},ensure_ascii=False));profile.cleanup()
print(json.dumps({'final_exceptions':report['exceptions'],'final_qt_messages':report['qt_messages'][-12:]},ensure_ascii=False))
sys.exit(1 if failed or report['exceptions'] else 0)
