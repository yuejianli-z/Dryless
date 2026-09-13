# Dryless

**Blink more, dry less. / 多眨一眼，少一分干涩。**

Local desktop blink reminders, on-device camera processing, and numeric history.
摄像头只在本机处理，不上传、不保存图像或视频。

## Current development status / 当前状态

This branch contains the latest Windows redesign and the handoff for macOS.
Target release: **0.2.0**; current candidate: **0.2.0-rc.1**.
macOS is **not yet implemented or verified**. Existing public Releases may be older.

**Mac 上的 Codex：从 [docs/START_HERE.md](docs/START_HERE.md) 开始。**

- Shared requirements: [Feature parity](docs/FEATURE_PARITY.md)
- Mac implementation: [Mac handoff](docs/MAC_HANDOFF.md)
- Actual results: [Windows](docs/release/windows.md) / [macOS](docs/release/macos.md)
- Publication gate: [Release checklist](docs/RELEASE_CHECKLIST.md)

## Features

- Live camera and blink detection; preview may be hidden while detection continues.
- Three-stage blink reminders; Polite, Sharp, Original and Blip; play all three.
- Fixed 25-minute presence microbreak, with priority over blink reminders.
- Monitor rhythm cells; historical time bubbles with day/week/month aggregation and CSV export.
- Chinese/English interface, saved settings, local numerical history, desktop tray.
- Approved green rounded interface and original detailed eye logo.

## Windows development / 构建

Use Python 3.14 x64 for the recorded candidate environment:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-windows.lock
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python main.py
.venv\Scripts\python build.py
```

Output: `dist/0.2.0-rc.1/Dryless.exe` (portable app, not an installer).
No Python is required on the destination machine for the packaged EXE.
Packaging itself does not establish clean-machine or hardware compatibility.
The Windows candidate is unsigned. Keep old builds; the script uses versioned output.

Packaged resource/UI smoke check: `Dryless.exe --self-test report.json`.
Camera check with a connected, unoccupied webcam: `Dryless.exe --camera-smoke camera.json`.
Both checks use temporary profiles, save no camera frames, and do not modify personal history.

## Local data

The current branch keeps its established `~/.dryless-redesign/` profile.
It imports legacy `~/.blink_reminder/` settings/history once without modifying the originals.
`DRYLESS_DATA_DIR` overrides storage for isolated tests. Do not commit personal profiles.

## Licensing

Dryless-owned source: [MIT](LICENSE). Third-party components retain their own terms;
the combined PyQt6 executable includes GPLv3 components and is not MIT-only.
See [third-party notices](THIRD_PARTY_NOTICES.md), bundled font/sound licenses,
and the final release checklist. Source and build instructions accompany candidate binaries.
