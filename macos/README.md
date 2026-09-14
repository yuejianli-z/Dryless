# Dryless for macOS

Native macOS implementation of Dryless, built with SwiftUI, AVFoundation, and Vision.

## Current scope

- Native Monitor, Stats, and Settings navigation with adaptive light/dark appearance.
- Camera previews constrained to the available panel and aspect-fitted from the actual captured frame size.
- Vision-based face and eye landmark processing, blink counting, 60-second live rate, and a 30-minute Monitor overview.
- Three-stage reminders, selectable bundled sound themes, and a 20-minute microbreak timer.
- Minute history, weighted range reports, legacy Windows/macOS history import, and CSV export.
- Menu bar pause/resume, sound, camera, open-window, and quit actions.
- Immediate Chinese and English switching.

Camera frames stay in memory. Dryless stores numeric blink history, not photos, video, or biometric templates, and does not upload camera data.

## Run locally

The package declares macOS 14 or newer. A full Xcode installation is recommended for development, signing, and distribution; the local SwiftPM build also works with a compatible Apple Swift toolchain.

```bash
cd macos
./script/build_and_run.sh
```

The script builds and stages `dist/Dryless.app`, then opens it.

## Checks

```bash
cd macos
swift build --product DrylessMac
swift run DrylessCoreChecks
```

Core checks cover the three reminder stages, blink detection, rolling and fixed-minute rates, microbreak timing, history aggregation and migration, malformed-file recovery, and settings persistence.

## Structure

- `Sources/DrylessCore`: shared models, detection state, settings, and history storage.
- `Sources/DrylessMac`: SwiftUI app, camera/Vision services, menu bar integration, and views.
- `Tests/DrylessCoreChecks`: executable core behavior checks.
- `script/build_and_run.sh`: local app-bundle build and launch helper.

Release scope and privacy boundary are recorded in [`../docs/RELEASE.md`](../docs/RELEASE.md).
