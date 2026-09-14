# Dryless macOS Development Validation

Validated on 2026-09-14 against the Windows handoff contract from `codex/macos-handoff-rc8` at `788927b`.

## Build Environment

- Host: macOS 26.6.2 (25G83)
- Architecture: arm64
- Swift: Apple Swift 6.3.2
- Active developer directory: Command Line Tools
- `xcodebuild`: unavailable until a full Xcode installation is selected
- Declared deployment target: macOS 14.0
- Actually launched on: macOS 26.6.2

The macOS 14 deployment target is declared but has not yet been exercised on a macOS 14 machine.

## Reproducible Commands

From the repository root:

```bash
cd macos
swift build --product DrylessMac
swift run DrylessCoreChecks
./script/build_and_run.sh verify
```

The helper builds and stages the local development app at:

```text
macos/dist/Dryless.app
```

## Release App

Create a directly runnable arm64 `.app` from a clean SwiftPM build:

```text
cd macos
./script/package_release.sh 0.1.0
```

The script stages, validates, and writes:

- `macos/release/Dryless.app`

It rejects any demo resource before signing and produces a normal Finder-openable app bundle, not a screenshot fixture or a compressed archive.

## Current Verification

- `swift build --product DrylessMac`: passed.
- `DrylessCoreChecks`: all checks passed for reminder staging, blink state, live/fixed-minute rates, microbreak timing, history aggregation and legacy recovery, malformed input, and settings persistence.
- Monitor: inspected in the running app at compact and zoomed window sizes. It opens at `1000 x 590` points and is constrained to `840–1040 x 590–700`, keeping the utility layout compact.
- Camera preview: a live `1920 x 1080` feed was visually verified at its native 16:9 ratio. The canvas remained clipped to its column without cropping, stretching, or bleeding into adjacent panels.
- Monitor information: includes session blinks, current rate, time since last blink, session duration, and a fixed 30-slot chart of per-minute blink rate. A single completed minute occupies one slot instead of stretching across the chart.
- Stats: inspected in the running app with hidden native scroller chrome and responsive range, summary, trend, minute, and reminder sections.
- Settings: inspected in the running app. The old `config.py preview` panel is absent, and all settings copy follows the selected interface language.
- Localization: Chinese to English switching was verified live across the window title, sidebar, Monitor, Settings, toolbar controls, help text, and camera timeout detail.
- Branding: the Windows logo artwork is rendered as transparent sage line art. App and menu-bar eye symbols switch together from open while the camera runs to closed when it stops; the contextual care tip remains independent. The sidebar includes a filled `Star on GitHub` link using the official GitHub Octicon under its bundled MIT license.
- Privacy: source inspection confirms camera frames are converted and processed in memory; persistence stores settings and numeric history only.

## Camera Status

An actual `1920 x 1080` camera completed startup. The live preview, face detection, and open-eye signal were observed in the UI, and the open/closed brand icon transition was verified by stopping the camera. The unavailable and startup-timeout paths were also verified, including recovery controls and localized error text. Before release, validate the remaining physical-device cases:

- Built-in 4:3 camera.
- A portrait-oriented source.
- Permission denied, device busy, disconnect, stop during startup, and restart.
- Blink calibration and accuracy with varied faces, glasses, distance, and lighting.
- A continuous 20-minute session through microbreak start and completion.

## Packaging Status

The `.app` is a macOS arm64 release build, but it is not Developer ID signed, notarized, or stapled. Its ad-hoc signature proves local bundle integrity only; Gatekeeper can still require an explicit user approval. Public distribution must replace the ad-hoc signing step with a Developer ID Application certificate and notarization before calling the package a trusted macOS release.
