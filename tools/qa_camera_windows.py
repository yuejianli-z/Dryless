"""Real Qt/thread lifecycle with synthetic camera data; never opens hardware."""
import os, sys, tempfile, json, time, threading
from pathlib import Path
from unittest.mock import patch, MagicMock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
profile=tempfile.TemporaryDirectory(prefix='dryless-camera-qa-')
os.environ['DRYLESS_DATA_DIR']=profile.name
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QIcon
import numpy as np
import ui, config
from main import GLOBAL_QSS, create_tray
report={'checks':[], 'hardware_used':False}
def check(name, value):
 report['checks'].append({'name':name,'pass':bool(value)})
 if not value: raise AssertionError(name)
app=QApplication([]);app.setStyle('Fusion');app.setQuitOnLastWindowClosed(False)
ui.load_bundled_fonts();app.setFont(ui.fnt(13));app.setStyleSheet(GLOBAL_QSS)
def until(predicate):
 end=time.monotonic()+5
 while not predicate() and time.monotonic()<end:
  app.processEvents();QTest.qWait(10)
 check('async completion within 5 seconds',predicate())
class Capture:
 instances=[]
 def __init__(self,*args):
  self.released=False;self.instances.append(self)
 def set(self,*a):pass
 def isOpened(self):return True
 def read(self):return True,np.zeros((480,640,3),dtype=np.uint8)
 def release(self):self.released=True
class Detector:
 fail=False;gate=None;instances=[]
 def __init__(self):
  if self.gate:self.gate.wait(3)
  self.released=False;self.blink_count=0;self.face_detected=True;self._ratio=.8;self._is_open=True
  self.instances.append(self)
 def process_frame(self,frame):
  if self.fail:raise RuntimeError('Injected detector failure')
  self.blink_count+=1
  return frame,True,.1,None
 def release(self):self.released=True
window=None;tray=None
try:
 with patch.object(ui,'BlinkDetector',Detector),patch.object(ui.cv2,'VideoCapture',Capture),patch.object(ui,'AlertManager',side_effect=lambda **k:MagicMock()),patch.object(ui.AUDIO,'stop') as stop_audio,patch.object(QSystemTrayIcon,'show'),patch.object(QSystemTrayIcon,'showMessage'):
  config.SOUND_ENABLED=False
  window=ui.DrylessApp(start_worker=False);window.show()
  check('first install camera off',window._camera_state=='off' and not Capture.instances)
  window.setCameraEnabled(False);window._start_worker()
  check('late startup honors explicit off',window._camera_state=='off' and not Capture.instances)
  window.setCameraEnabled(True)
  first=window.worker
  window.setCameraEnabled(True)
  check('double start keeps one worker',window.worker is first)
  until(lambda:window._camera_state=='running' and window.monitor._last_state is not None)
  check('only one capture',len(Capture.instances)==1)
  window.setPreviewVisible(False)
  check('hide keeps hardware',first.isRunning() and not Capture.instances[-1].released)
  window.setPaused(True)
  check('pause keeps capture running',first.isRunning() and window.monitor._paused)
  tray=create_tray(app,window,QIcon())
  check('tray mirrors pause',tray._actions['pause'].isChecked())
  window._tray_resident=True;window.close();app.processEvents()
  check('close hides instead of stopping',not window.isVisible() and first.isRunning())
  tray._actions['show'].trigger();app.processEvents()
  check('tray restores window',window.isVisible())
  snapshot=dict(window.monitor._last_state)
  tray._actions['camera'].trigger()
  check('stop immediately clears frame',window.monitor.camera._frame is None)
  check('stop disables parallel restart',window._camera_state=='stopping')
  window.setCameraEnabled(True)
  check('stopping does not create second worker',window.worker is first)
  first.stats.emit(dict(snapshot,total=99999))
  until(lambda:window._camera_state=='off')
  check('hardware and detector released',Capture.instances[-1].released and Detector.instances[-1].released)
  check('late frame data ignored',window.monitor._last_state['total']!=99999)
  check('closed session summary frozen',window.monitor._last_state['total']==snapshot['total'])
  check('off pause unavailable',not tray._actions['pause'].isEnabled() and not window.monitor._pause_button.isEnabled())
  app.processEvents();QTest.qWait(80);app.processEvents()
  old_geometry={w:w.geometry() for w in (window.titlebar._camera_btn,window.titlebar._lang_btn,window.monitor._pause_button,window.monitor._sound_button,window.monitor._settings_button)}
  for language in ('zh','en'):
   config.LANGUAGE=language;window._on_language_changed();app.processEvents();QTest.qWait(80);app.processEvents()
   check('language never restarts camera '+language,window._camera_state=='off' and len(Capture.instances)==1)
   report['geometry_'+language]=[(w.text(),rect.getRect(),w.geometry().getRect()) for w,rect in old_geometry.items()]
   check('stable control geometry '+language,all(w.geometry()==rect for w,rect in old_geometry.items()))
   for page in ('settings','stats','monitor'):window._on_nav(page)
  check('navigation never restarts camera',len(Capture.instances)==1)
  window.setCameraEnabled(True)
  check('new session clears counters immediately',window.monitor._last_state is None and sum(window.monitor._alert_counts)==0 and window.monitor.trend._data==[])
  until(lambda:window._camera_state=='running')
  check('new worker with pause preference',window.worker is not first and window.worker._paused)
  window.setCameraEnabled(False);until(lambda:window._camera_state=='off')
  # Cancel during detector initialization, before a camera handle exists.
  before=len(Capture.instances);Detector.gate=threading.Event()
  window.setCameraEnabled(True);QTest.qWait(30);window.setCameraEnabled(False);Detector.gate.set()
  until(lambda:window._camera_state=='off');Detector.gate=None
  check('startup cancellation cannot acquire camera',len(Capture.instances)==before)
  Detector.fail=True;window.setCameraEnabled(True)
  until(lambda:window._camera_state=='error' and not window.worker.isRunning())
  app.processEvents()
  check('exception releases capture',Capture.instances[-1].released)
  check('exception releases detector',Detector.instances[-1].released)
  check('retry exposed after cleanup',window.titlebar._camera_btn.isEnabled())
  Detector.fail=False;window.setCameraEnabled(True)
  until(lambda:window._camera_state=='running')
  check('retry actually starts new session',not Capture.instances[-1].released)
  window.requestQuit();app.processEvents()
  check('quit releases capture',all(c.released for c in Capture.instances))
  check('quit stops worker',not window.worker.isRunning())
  check('stop cancels shared audio',stop_audio.call_count>=4)
except BaseException:
 import traceback;report['error']=traceback.format_exc()
finally:
 if window:
  window._tray_resident=False;window._quit_requested=False;window.close();app.processEvents()
 if tray:tray.hide()
 out=ROOT/'qa-output'/'camera-controls.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
sys.exit(1 if report.get('error') or any(not c['pass'] for c in report['checks']) else 0)
