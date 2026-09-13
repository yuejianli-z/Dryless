"""Packaged-app checks. Uses a temporary profile set by main.py before imports."""
from pathlib import Path
import hashlib
import json
import platform
import sys
import traceback
import wave

def run(app, output, camera=False):
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QAbstractScrollArea
    import config
    import ui
    from version import VERSION
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    report = {'version': VERSION, 'frozen': bool(getattr(sys, 'frozen', False)),
              'platform': platform.platform(), 'mode': 'camera' if camera else 'self-test',
              'checks': [], 'errors': []}
    output = Path(output).resolve()
    window = None
    def check(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)
    old_hook = sys.excepthook
    sys.excepthook = lambda kind, value, tb: report['errors'].append(''.join(traceback.format_exception(kind, value, tb)))
    try:
        manifest = json.loads((base / 'release-assets.json').read_text(encoding='utf-8'))
        for name, expected in manifest.items():
            check('resource:' + name, hashlib.sha256((base / name).read_bytes()).hexdigest() == expected)
        for family in ('polite', 'sharp', 'original', 'blip'):
            for level in range(3):
                with wave.open(str(base / 'sounds' / family / f'alert{level}.wav'), 'rb') as sound:
                    check(f'wav:{family}:{level}', sound.getnframes() > 0 and sound.getsampwidth() == 2)
        # Exercise the packaged timer, not just the reported version label.
        from microbreak import MicrobreakController
        clock = MicrobreakController()
        early = []
        for second in range(1200):
            if clock.update(True, second)['started']:
                early.append(second)
        check('microbreak-no-early-trigger', not early)
        check('microbreak-at-20-minutes', clock.update(True, 1200)['started'])
        from PyQt6.QtGui import QFontDatabase
        for family in ('Dryless Sans', 'Dryless CJK'):
            check('font:' + family, family in QFontDatabase.families())
        # MediaPipe really creates its native task and processes a synthetic frame.
        from blink_detector import BlinkDetector
        import numpy as np
        detector = BlinkDetector()
        try:
            detector.process_frame(np.zeros((480, 640, 3), dtype=np.uint8))
            check('model-loaded-no-face-on-black', not detector.face_detected)
        finally:
            detector.release()
        window = ui.DrylessApp(start_worker=camera)
        window.show()
        if camera:
            config.SOUND_ENABLED = False
            window.worker.setSoundEnabled(False)
            seen = {'frames': 0, 'samples': 0, 'face_seen': False}
            window.worker.frameReady.connect(lambda frame: seen.update(frames=seen['frames'] + 1))
            def stats(value):
                seen['samples'] += 1
                seen['face_seen'] |= bool(value.get('face'))
            window.worker.stats.connect(stats)
            window.worker.errorReported.connect(report['errors'].append)
            QTimer.singleShot(12000, app.quit)
            app.exec()
            report['camera'] = seen
            check('real-camera-frames', seen['frames'] >= 5)
            check('real-camera-detection-samples', seen['samples'] >= 5)
        else:
            from PyQt6.QtTest import QTest
            geometry = {}
            for lang in ('zh', 'en'):
                config.LANGUAGE = lang
                window._on_language_changed()
                for width, height in ((1100, 700), (1240, 780)):
                    window.resize(width, height)
                    for page in ('monitor', 'stats', 'settings'):
                        window._on_nav(page)
                        app.processEvents()
                        QTest.qWait(45)
                        pane = getattr(window, page)
                        check(f'{lang}/{width}/{page}/no-scroll', all(
                            child.verticalScrollBar().maximum() == 0
                            for child in pane.findChildren(QAbstractScrollArea) if child.isVisible()))
                        key = (width, height, page)
                        dimensions = (window.sidebar.geometry().getRect(), window.stack.geometry().getRect())
                        if lang == 'zh':
                            geometry[key] = dimensions
                        else:
                            check(f'{width}/{page}/language-layout', dimensions == geometry[key])
            window._on_nav('monitor')
            window.setPaused(True)
            check('pause-propagation', window.worker._paused)
            window.setPaused(False)
            check('resume-propagation', not window.worker._paused)
            # Dispatch actual audio once, then cancel; no full-volume surprise during QA.
            import alert
            errors = []
            token = alert.AUDIO.play([alert.sound_file(0, 'blip')], 'package-check', on_error=errors.append)
            QTest.qWait(150)
            alert.AUDIO.stop('package-check')
            check('audio-dispatch-and-stop', token is not None and not errors)
    except BaseException:
        report['errors'].append(traceback.format_exc())
    finally:
        if window is not None:
            window.close()
            app.processEvents()
            if window.worker.isRunning():
                window.worker.wait(5000)
        sys.excepthook = old_hook
        report['passed'] = not report['errors'] and all(x['passed'] for x in report['checks'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['passed'] else 1
