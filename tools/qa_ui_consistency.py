import os,sys,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
profile=tempfile.TemporaryDirectory();os.environ['DRYLESS_DATA_DIR']=profile.name
from PyQt6.QtWidgets import QApplication,QSystemTrayIcon
from PyQt6.QtGui import QIcon,QFontMetrics
from PyQt6.QtCore import Qt, QCoreApplication, QEvent
from PyQt6.QtTest import QTest
import ui,config,theme as T
from main import GLOBAL_QSS,create_tray
from widgets.soft_icon import SoftIcon,icon,_brand_eye_pixmap
app=QApplication([]);app.setStyle('Fusion');ui.load_bundled_fonts();app.setFont(ui.fnt(13));app.setStyleSheet(GLOBAL_QSS)
w=ui.DrylessApp(start_worker=False);w.show();app.processEvents();w.resize(1100,700)
checks=[]
def check(name,ok):
 checks.append({'name':name,'pass':bool(ok)})
 assert ok,name
def settle():app.processEvents();QTest.qWait(60)
def pixels(pm):
 im=pm.toImage();return bytes(im.constBits().asstring(im.sizeInBytes()))
out=r/'qa-output/consistency';out.mkdir(exist_ok=True)
with patch.object(QSystemTrayIcon,'show'):
 tray=create_tray(app,w,QIcon())
 for lang in ('zh','en'):
  config.LANGUAGE=lang;w._on_language_changed()
  for state in ('off','starting','running','stopping','error','off','running'):
   w._set_camera_state(state);settle()
   expected=icon('eye_open' if state=='running' else 'eye_closed',256)
   check(f'{lang}-{state}-window-state-icon',pixels(w.windowIcon().pixmap(64,64))==pixels(expected.pixmap(64,64)))
   check(f'{lang}-{state}-app-state-icon',pixels(app.windowIcon().pixmap(64,64))==pixels(expected.pixmap(64,64)))
   check(f'{lang}-{state}-navigation-state-icon',pixels(w.sidebar._buttons['monitor'].icon().pixmap(28,28))==pixels(icon('eye',28,tile=True).pixmap(28,28)))
   check(f'{lang}-{state}-tray-menu-state-icon',pixels(tray._actions['camera'].icon().pixmap(20,20))==pixels(icon('eye_open' if state=='running' else 'eye_closed',20).pixmap(20,20)))
   for button in (w.titlebar._camera_btn,w.monitor._sound_button):
    check(f'{lang}-{state}-no-control-tooltip',button.toolTip()=='')
    check(f'{lang}-{state}-icon-only',button.text()=='' and not button.icon().isNull())
    check(f'{lang}-{state}-accessible-state',('：' if lang=='zh' else ':') in button.accessibleName())
    check(f'{lang}-{state}-aligned-height',button.height()==w.titlebar._lang_btn.height())
    check(f'{lang}-{state}-icon-fits',button.iconSize().width()<button.width())
   check(f'{lang}-{state}-matching-control-style',w.titlebar._camera_btn.styleSheet()==w.monitor._sound_button.styleSheet())
   check(f'{lang}-{state}-no-tips-tooltip',w.monitor.tips.toolTip()=='')
   if state in ('off','running'):
    for page in ('monitor','stats','settings'):
     w._on_nav(page);settle();w.grab().save(str(out/f'{lang}-{state}-{page}.png'))
    w._on_nav('monitor')
 # Use the actual native widget render to review the three glyphs and text.
 w.monitor.tips.setAlertActive(True)
 for i in range(3):
  w.monitor.tips._index=i;w.monitor.tips.retranslate();settle();w.monitor.tips.grab().save(str(out/f'tip-{i}.png'))
 check('same source family differs across states',pixels(_brand_eye_pixmap(T.BRAND,128,False))!=pixels(_brand_eye_pixmap(T.BRAND,128,True)))
 for closed in (False,True):
  im=_brand_eye_pixmap(T.BRAND,128,closed).toImage()
  check('transparent state-icon corners',all(im.pixelColor(x,y).alpha()<4 for x,y in ((0,0),(127,0),(0,127),(127,127))))
 # Dispose native tray/menu/widgets while Qt and Python are both alive.
 # This script does not run app.exec(), so deferred deletion needs flushing.
 tray.hide();tray.setContextMenu(None);tray.deleteLater()
 w.requestQuit();w.deleteLater()
 QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
 app.processEvents()
(r/'qa-output/consistency.json').write_text(json.dumps({'checks':checks},indent=2),encoding='utf-8')
print(json.dumps({'checks':len(checks),'failed':[x for x in checks if not x['pass']]}))
