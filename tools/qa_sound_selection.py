"""Actual sound-selector clicks with a recorded playback adapter, no hardware."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
profile=tempfile.TemporaryDirectory(prefix='dryless-sound-select-')
os.environ['DRYLESS_DATA_DIR']=profile.name
import ui,config,alert
from main import GLOBAL_QSS
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication,QEvent,Qt
from PyQt6.QtTest import QTest
app=QApplication([]);app.setStyle('Fusion');ui.load_bundled_fonts();app.setFont(ui.fnt(13));app.setStyleSheet(GLOBAL_QSS)
w=ui.DrylessApp(start_worker=False);w.show();w.resize(1100,700);w._on_nav('settings')
s=w.settings;checks=[];calls=[]
def check(name,ok):checks.append(dict(name=name,passed=bool(ok)))
def play(paths,owner,**kwargs):
    token=len(calls)+1
    calls.append(dict(token=token,paths=list(paths),owner=owner,**kwargs))
    return token
try:
    config.SOUND_ENABLED=False
    with patch.object(alert.AUDIO,'play',side_effect=play),patch.object(alert.AUDIO,'stop') as stop:
        for lang in ('zh','en'):
            config.LANGUAGE=lang;w._on_language_changed();app.processEvents()
            check(lang+' public sound name',s._theme_buttons['original'].text()=='Ding')
            for key,button in s._theme_buttons.items():
                QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
                check(lang+key+' exactly one first cue',calls[-1]['paths']==[alert.sound_file(0,key)])
                check(lang+key+' saves selection',config.SOUND_THEME==key)
                check(lang+key+' stays in single mode',not s._preview_sequence)
                check(lang+key+' play-all button remains available',s._preview_button.text() in ('试听三档','Play all 3'))
            count=len(calls)
            QTest.mouseClick(s._theme_buttons['blip'],Qt.MouseButton.LeftButton)
            check(lang+' same selection auditions again',len(calls)==count+1)
            old_token=s._preview_token
            QTest.mouseClick(s._preview_button,Qt.MouseButton.LeftButton)
            check(lang+' single upgrades to all three',calls[-1]['paths']==[alert.sound_file(i,'blip') for i in range(3)] and s._preview_sequence)
            new_token=s._preview_token
            s._preview_finished(old_token)
            check(lang+' old completion cannot stop new cue',s._preview_token==new_token)
            QTest.mouseClick(s._preview_button,Qt.MouseButton.LeftButton)
            check(lang+' stop button cancels sequence',s._preview_token is None)
            QTest.mouseClick(s._theme_buttons['original'],Qt.MouseButton.LeftButton)
            check(lang+' switch cancels previous owner',stop.call_args.args==(s,))
            s._show_tab(1)
            check(lang+' leaving sound tab cancels cue',s._preview_token is None)
            s._show_tab(0)
            check(lang+' preview does not unmute alerts',config.SOUND_ENABLED is False)
            check(lang+' preview does not start camera',w._camera_state=='off')
        s._stop_preview()
        config.LANGUAGE='zh';w._on_language_changed();app.processEvents()
        out=ROOT/'qa-output/sound-selection';out.mkdir(parents=True,exist_ok=True)
        w.grab().save(str(out/'settings-zh.png'))
finally:
    w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents();profile.cleanup()
out=ROOT/'qa-output/sound-selection';out.mkdir(parents=True,exist_ok=True)
(out/'report.json').write_text(json.dumps(dict(checks=checks,hardware_used=False),indent=2),encoding='utf-8')
failed=[c for c in checks if not c['passed']]
print(json.dumps(dict(checks=len(checks),failed=failed)))
sys.exit(1 if failed else 0)
