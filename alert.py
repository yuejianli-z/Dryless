"""Three-stage sounds and a single, cancellable desktop audio channel."""
from pathlib import Path
import threading
import wave
import winsound
import config

SOUND_THEMES = ('polite', 'sharp', 'original', 'blip')
_SOUNDS_DIR = Path(__file__).resolve().parent / 'sounds'
MICROBREAK_SOUND = _SOUNDS_DIR / 'microbreak' / 'started.wav'


def selected_theme():
    value = getattr(config, 'SOUND_THEME', 'blip')
    return value if value in SOUND_THEMES else 'blip'


def sound_file(level, theme=None):
    theme = selected_theme() if theme is None else theme
    if theme not in SOUND_THEMES:
        theme = 'blip'
    return _SOUNDS_DIR / theme / f'alert{max(0, min(int(level), 2))}.wav'


class AudioChannel:
    """Priority: microbreak > explicit preview > blink. Never mix cues."""
    def __init__(self):
        self.lock = threading.RLock()
        self.current = None
        self.serial = 0

    def play(self, paths, owner, priority=0, gap=.8, on_stage=None, on_finished=None, on_error=None):
        paths = tuple(Path(p) for p in paths)
        durations = []
        for path in paths:
            with wave.open(str(path), 'rb') as wav:
                durations.append(wav.getnframes() / wav.getframerate())
        with self.lock:
            if self.current and priority <= self.current['priority']:
                return None
            self.stop()
            self.serial += 1
            token = self.serial
            cancel = threading.Event()
            self.current = dict(token=token, cancel=cancel, owner=owner, priority=priority)

            def run():
                try:
                    for index, (path, duration) in enumerate(zip(paths, durations)):
                        with self.lock:
                            if cancel.is_set() or not self.current or self.current['token'] != token:
                                break
                            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_NODEFAULT | winsound.SND_ASYNC)
                        if on_stage:
                            on_stage(token, index)
                        if cancel.wait(duration + .03):
                            break
                        if index < len(paths) - 1 and cancel.wait(gap):
                            break
                except Exception as error:
                    if on_error:
                        on_error(str(error))
                finally:
                    with self.lock:
                        if self.current and self.current['token'] == token:
                            self.stop(owner)
                    if on_finished:
                        on_finished(token)

            threading.Thread(target=run, daemon=True).start()
            return token

    def stop(self, owner=None):
        with self.lock:
            if self.current and (owner is None or owner == self.current['owner']):
                self.current['cancel'].set()
                self.current = None
                winsound.PlaySound(None, 0)


AUDIO = AudioChannel()


class AlertManager:
    def __init__(self, on_error=None):
        self._last_alert_time = -1
        self.enabled = True
        self.on_error = on_error
        self.last_error = None
        missing = [str(sound_file(level, theme)) for theme in SOUND_THEMES
                   for level in range(3) if not sound_file(level, theme).is_file()]
        if not MICROBREAK_SOUND.is_file():
            missing.append(str(MICROBREAK_SOUND))
        if missing:
            raise FileNotFoundError(f'Missing reminder sounds: {missing}')

    def _error(self, message):
        self.last_error = message
        if self.on_error:
            self.on_error(message)

    def check_and_alert(self, no_blink_duration):
        if not self.enabled or no_blink_duration < config.NO_BLINK_ALERT_SEC:
            return
        interval = max(1, config.ALERT_INTERVAL_SEC)
        alert_round = int((no_blink_duration - config.NO_BLINK_ALERT_SEC) // interval)
        expected = config.NO_BLINK_ALERT_SEC + alert_round * interval
        if self._last_alert_time >= expected:
            return
        self._last_alert_time = expected
        self._play_alert(alert_round)

    def _play_alert(self, alert_round):
        return AUDIO.play([sound_file(alert_round)], self, on_error=self._error)

    def play_microbreak(self):
        if self.enabled:
            return AUDIO.play([MICROBREAK_SOUND], self, priority=3, on_error=self._error)

    def stop(self):
        AUDIO.stop(self)

    def reset(self):
        self._last_alert_time = -1
