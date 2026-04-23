"""Dryless configuration and local settings persistence."""

import json
import os

_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".blink_reminder", "config.json")

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
PROCESS_EVERY_N_FRAMES = 2

BLINK_RATIO_THRESHOLD = 0.60

NO_BLINK_ALERT_SEC = 8
ALERT_INTERVAL_SEC = 5
ALERT_LEVELS = [0, 1, 2, 3]

SHOW_PREVIEW_ON_START = True
PREVIEW_WINDOW_NAME = "Dryless - Press Q to hide"

LANGUAGE = "en"

_PERSIST_KEYS = {
    "NO_BLINK_ALERT_SEC": int,
    "ALERT_INTERVAL_SEC": int,
    "BLINK_RATIO_THRESHOLD": float,
    "PROCESS_EVERY_N_FRAMES": int,
    "CAMERA_INDEX": int,
    "CAMERA_WIDTH": int,
    "CAMERA_HEIGHT": int,
    "LANGUAGE": str,
}


def load_config():
    """Load user settings from the local config file."""
    import sys

    if not os.path.exists(_CONFIG_FILE):
        return
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        module = sys.modules[__name__]
        for key, cast in _PERSIST_KEYS.items():
            if key in data:
                setattr(module, key, cast(data[key]))
    except Exception as e:
        print(f"[config] Failed to load config, using defaults: {e}")


def save_config():
    """Save current runtime settings to the local config file."""
    import sys

    try:
        os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
        module = sys.modules[__name__]
        data = {key: getattr(module, key) for key in _PERSIST_KEYS}
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[config] Failed to save config: {e}")


load_config()
