"""Audio alert manager for Dryless."""

import os
import threading
import winsound

import config

_SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

_SOUND_FILES = [
    os.path.join(_SOUNDS_DIR, "alert0.wav"),
    os.path.join(_SOUNDS_DIR, "alert1.wav"),
    os.path.join(_SOUNDS_DIR, "alert2.wav"),
    os.path.join(_SOUNDS_DIR, "alert3.wav"),
]


class AlertManager:
    """Play escalating WAV alerts without blocking the UI thread."""

    def __init__(self):
        self._alert_thread = None
        self._last_alert_time = 0
        self.enabled = True

        missing = [f for f in _SOUND_FILES if not os.path.exists(f)]
        if missing:
            raise FileNotFoundError(
                f"Missing alert sound files: {missing}\n"
                f"Expected alert0.wav to alert3.wav in {_SOUNDS_DIR}"
            )

    def check_and_alert(self, no_blink_duration):
        if not self.enabled:
            return

        if no_blink_duration < config.NO_BLINK_ALERT_SEC:
            return

        overtime = no_blink_duration - config.NO_BLINK_ALERT_SEC
        alert_round = int(overtime // config.ALERT_INTERVAL_SEC)
        expected_alert_time = config.NO_BLINK_ALERT_SEC + alert_round * config.ALERT_INTERVAL_SEC

        if self._last_alert_time >= expected_alert_time and alert_round > 0:
            return

        if no_blink_duration >= expected_alert_time:
            self._last_alert_time = expected_alert_time
            self._play_alert(alert_round)

    def _play_alert(self, alert_round):
        if self._alert_thread and self._alert_thread.is_alive():
            return

        level = min(alert_round, len(_SOUND_FILES) - 1)
        self._alert_thread = threading.Thread(
            target=self._play, args=(level,), daemon=True
        )
        self._alert_thread.start()

    def _play(self, level):
        winsound.PlaySound(_SOUND_FILES[level], winsound.SND_FILENAME)

    def reset(self):
        self._last_alert_time = 0
