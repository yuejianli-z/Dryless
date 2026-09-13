from pathlib import Path
import sys, os, tempfile, json, time, wave, hashlib, threading
from unittest.mock import patch, Mock
ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'qa-output/reminders'
HERE.mkdir(parents=True, exist_ok=True)
profile = tempfile.TemporaryDirectory(dir=HERE)
os.environ['DRYLESS_DATA_DIR'] = profile.name
sys.path.insert(0, str(ROOT))
import config, alert, ui
from microbreak import MicrobreakController
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from main import GLOBAL_QSS
report = []
def check(name, value):
    report.append(dict(name=name, passed=bool(value)))
    assert value, name

def feed(controller, start, end, face=True):
    events=[]
    for second in range(start, end + 1):
        value=controller.update(face, second)
        if value['started'] or value['ended']: events.append((second,value))
    return value, events

c=MicrobreakController()
state, events=feed(c,0,1499)
check('no early microbreak',not state['active'] and not events)
state=c.update(True,1500)
check('exactly 25 minutes triggers once',state['active'] and state['started'])
state,events=feed(c,1501,1529)
check('prompt holds without replaying',state['active'] and not events)
state=c.update(True,1530)
check('30 second prompt ends',state['ended'] and not state['active'])
state,events=feed(c,1531,3029)
check('no repeat until another 25 minutes',not events)
check('next 25 minute interval',c.update(True,3030)['started'])
c=MicrobreakController();feed(c,0,1500)
state,events=feed(c,1501,1519,False)
check('short absence does not dismiss break early',state['active'])
check('20 second absence dismisses break',c.update(False,1520)['ended'])
c=MicrobreakController();feed(c,0,1000);feed(c,1001,1003,False);c.update(True,1004)
check('brief face loss preserves prior presence',c.presence==1000)
feed(c,1005,1010,False);c.update(True,1011)
check('longer absence breaks continuity',c.presence==0)
c=MicrobreakController();feed(c,0,1499)
check('camera stall cannot trigger a false break',not c.update(True,1600)['started'] and c.presence==0)
feed(c,1601,1610);c.update(True,1611,paused=True)
check('pause clears pending presence',c.presence==0 and not c.previous_face)

manifest=[]
resource_hashes=json.loads((ROOT/'release-assets.json').read_text())
for family in alert.SOUND_THEMES:
    for level in range(3):
        path=alert.sound_file(level,family)
        with wave.open(str(path),'rb') as sound:
            duration=sound.getnframes()/sound.getframerate()
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        check(f'{family}/{level} approved resource hash',digest==resource_hashes[path.relative_to(ROOT).as_posix()])
        manifest.append(dict(theme=family,duration=duration,sha256=digest))
check('four families with three distinct stages',len(manifest)==12 and all(len({x['sha256'] for x in manifest if x['theme']==family})==3 for family in alert.SOUND_THEMES))
for family in ('polite','sharp'):
    durations=[x['duration'] for x in manifest if x['theme']==family]
    check(f'{family} duration grows',durations[0]<durations[1]<durations[2])
for i in range(3):
    check(f'original {i} bytes unchanged',alert.sound_file(i,'original').read_bytes()==(ROOT/'sounds'/f'alert{i}.wav').read_bytes())
    check(f'Blip {i} audition bytes unchanged',hashlib.sha256(alert.sound_file(i,'blip').read_bytes()).hexdigest()==resource_hashes[f'sounds/blip/alert{i}.wav'])
check('stage clamps to third',alert.sound_file(99).name=='alert2.wav')
check('original logo unchanged',hashlib.sha256((ROOT/'icon.ico').read_bytes()).hexdigest().upper()=='20D830EF12FCF7B9B346EB820B8ED6001F075A6C59B4BCF3632E885F1076646C')
check('detector unchanged',hashlib.sha256((ROOT/'blink_detector.py').read_bytes()).hexdigest().upper()=='1E551F4334095EE4EDEF9C6761FF44894E142170479E016289CC6FAD967C0E0F')

# Drive the actual worker's arbitration with simulated camera time, not the camera.
worker=ui.DetectorWorker();worker._alert=Mock();worker._alert.enabled=True
levels=[];worker.alertTriggered.connect(levels.append)
for second in range(1501):
    level,micro=worker._update_reminders(True, second%3==0, second%3, second)
check('worker triggers one fixed microbreak',micro['started'] and worker._alert.play_microbreak.call_count==1)
worker._alert.check_and_alert.reset_mock();levels.clear()
for second in range(1501,1530):worker._update_reminders(True,False,200,second)
check('blink sounds and visual levels held during break',not worker._alert.check_and_alert.called and not levels)
level,micro=worker._update_reminders(True,False,200,1530)
check('first resumed frame has no catch-up alert',level==-1 and worker._alert.check_and_alert.call_args.args==(0,))
for second in range(1531,1538):worker._update_reminders(True,False,200,second)
level,_=worker._update_reminders(True,False,200,1538)
check('fresh first-stage wait after microbreak',level==0 and levels==[0])
for second in range(1539,1560):worker._update_reminders(True,False,200,second)
check('worker never emits fourth stage',max(levels)==2 and levels[-1]==2)

short=HERE/'qa-short.wav'
with wave.open(str(short),'wb') as wav:
    wav.setparams((1,2,44100,4410,'NONE','not compressed'));wav.writeframes(b'\0'*8820)
with patch.object(alert.winsound,'PlaySound') as playback:
    channel=alert.AudioChannel();seen=[];done=threading.Event()
    token=channel.play([short]*3,'preview',priority=2,gap=.08,on_stage=lambda t,i:seen.append((i,time.monotonic())),on_finished=lambda t:done.set())
    check('sequence finishes',done.wait(3))
    check('all three cues ordered with gap',[i for i,t in seen]==[0,1,2] and all(seen[i+1][1]-seen[i][1]>=.20 for i in (0,1)))
    seen=[];done.clear()
    channel.play([short]*3,'preview',priority=2,gap=.08,on_stage=lambda t,i:seen.append(i),on_finished=lambda t:done.set())
    time.sleep(.03);channel.stop('preview');done.wait(1);time.sleep(.25)
    check('cancel prevents later cues',seen==[0])
    channel.play([short]*3,'blink',priority=0,gap=.1)
    high=channel.play([short]*3,'microbreak',priority=3,gap=.1)
    check('microbreak preempts blink',high is not None)
    check('blink cannot interrupt microbreak',channel.play([short],'blink') is None)
    check('preview cannot interrupt microbreak',channel.play([short],'preview',priority=2) is None)
    time.sleep(.06)
    check('cancelled low priority cannot stop new cue',channel.current['owner']=='microbreak')
    channel.stop()
    manager=alert.AlertManager();manager.enabled=False;manager.play_microbreak()
    check('muted microbreak is silent',alert.AUDIO.current is None)

app=QApplication([]);app.setStyle('Fusion');ui.load_bundled_fonts();app.setFont(ui.fnt(13));app.setStyleSheet(GLOBAL_QSS)
window=ui.DrylessApp(start_worker=False);window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating,True);window.show()
def settle():app.processEvents();QTest.qWait(50)
try:
    window.resize(1100,700);window._on_nav('settings');settle();settings=window.settings
    check('four equal selector widths',max(b.width() for b in settings._theme_buttons.values())-min(b.width() for b in settings._theme_buttons.values())<=1)
    for family in alert.SOUND_THEMES:
        settings._select_sound(family)
        check(f'{family} selection persists',json.loads((Path(profile.name)/'config.json').read_text())['SOUND_THEME']==family and sum(b.isChecked() for b in settings._theme_buttons.values())==1)
    rects=[]
    for language in ('zh','en'):
        config.LANGUAGE=language;window._on_language_changed();settle()
        rects.append([b.geometry().getRect() for b in settings._theme_buttons.values()]+[settings._preview_button.geometry().getRect()])
        window.grab().save(str(HERE/f'settings-{language}.png'))
    check('language does not move sound controls',rects[0]==rects[1])
    check('summary has exactly three stages',len(settings._stage_names)==3 and '+' in settings._stage_times[-1].text())
    with patch.object(alert.winsound,'PlaySound'):
        settings._toggle_preview();settle()
        check('native play-all starts',settings._preview_token is not None)
        settings._select_sound('polite');settle()
        check('selecting another sound stops audition',settings._preview_token is None and alert.AUDIO.current is None)
        settings._toggle_preview();settle();settings._show_tab(1);settle()
        check('changing settings tab stops audition',settings._preview_token is None)
        settings._show_tab(0);settings._toggle_preview();settle();window._on_nav('monitor');settle()
        check('leaving settings stops audition',settings._preview_token is None)
    base=dict(face=True,eye_open=True,eye_ratio=.85,no_blink=25,rate=12,total=42,alert_level=2,session_sec=1500,minute_history=[12,18],minute_valid_seconds=[60,60],microbreak_active=True)
    for language in ('zh','en'):
        config.LANGUAGE=language;window._on_language_changed();window._on_stats(base);settle()
        check(f'{language} microbreak visible in status',window.monitor._status_lbl.text() in ('该起来活动一下了','Time to move'))
        check(f'{language} microbreak suppresses blink strip',not window.alert_strip.isVisible())
        check(f'{language} microbreak guidance retained',('25' in window.monitor._message_body.text()))
        window.grab().save(str(HERE/f'microbreak-{language}.png'))
finally:
    alert.AUDIO.stop();window.close();app.processEvents();profile.cleanup()
(HERE/'qa-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=len(report),failed=[r for r in report if not r['passed']]),ensure_ascii=False))
