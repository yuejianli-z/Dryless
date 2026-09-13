# Windows 0.2.0-rc.2 — 20-minute microbreak

Date: 2026-09-13.

Change: the user replaced the 25-minute presence trigger with 20 minutes. Production timing and
Chinese/English reminder copy now use one constant. The 30-second display lifetime, 20-second
absence dismissal, three-stage blink alerts and sound assets remain unchanged.

The same source update includes the F2 feature contract, Mac branch review and native-Mac handoff.
Camera start/stop, expanded tray controls, tips carousel and the other W/M gaps in MAC_REVIEW.md
remain pending; this candidate does not claim they are implemented.

## Source validation

- `python -B -m unittest discover -s tests -v`: **22 passed**.
- `python -B tools/qa_reminders_windows.py`: **66 passed**.
- Timing was simulated: no alert through1199 seconds, one trigger at1200, ends1230,
  next full cycle triggers2430; 20 seconds away dismisses and blink reminders resume after a fresh delay.
- Integration uses mocked camera time/audio playback; it checks both localized status messages.
- The real 20-minute face-present session has not been performed.

## Package validation

- Source commit: `67b37de7096d47310dbbe2079794fddc3fcab17b`.
- Local build: `python -B build.py` completed; output `dist/0.2.0-rc.2/Dryless.exe`.
- Packaged `--self-test`, launched from outside the source checkout with a temporary profile:
  **62 checks passed**, no reported errors. Includes actual packaged timer execution through1200 seconds.
- EXE bytes: 131046428; SHA256: `509321f9299046d0d137217145663c1b6a7fcc772c48cad9d3afc802b31dd0b0`.
- Desktop shortcut updated to rc.2 after gracefully closing rc.1; old package and shortcut backup preserved.
- Detailed machine-readable evidence: [windows-rc2-validation.json](windows-rc2-validation.json).
- Previous rc.1 binaries and their reports remain intact. This is a local candidate, not a public stable release.
No Mac runtime or camera accuracy claim is made by Windows checks.
