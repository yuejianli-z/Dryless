# Dryless 0.2.0

This is the single public release note for Dryless 0.2.0.

## What is included

- Windows source at the repository root and a standalone Windows executable,
  `Dryless-0.2.0-windows.exe`, attached to the matching GitHub Release.
- Native macOS source under `macos/` and a directly runnable arm64 App bundle
  at `macos/release/Dryless.app` for macOS 14 or later.
- English and Simplified Chinese documentation, plus twelve verified native-app
  screenshots: Monitor, Stats, and Settings for both languages on both platforms.

The two implementations provide the same product behavior while following
their operating-system conventions: local camera analysis, minute-level blink
history, three-level blink reminders, a 20-minute microbreak, local CSV export,
sound choices, and Chinese/English interface text.

## Privacy boundary

No API credentials, personal paths, local camera captures, recordings, facial
templates, or user history are included. Camera frames are processed in memory;
only settings and numeric minute-level records are persisted locally by the
application.

The README portrait is separately licensed documentation artwork. It is not a
runtime resource, a camera fallback, or production data.

## Verification

- Windows: 32 unit tests and the source self-test passed before packaging.
- macOS: the native arm64 App bundle was built and opened on macOS; its bundle
  verification is recorded with the macOS source.

Successful build and layout checks do not by themselves establish camera or
blink-measurement accuracy for every device, lighting condition, or face.
