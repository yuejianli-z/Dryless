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

Build and packaged checks pending at this source commit; results and exact binary SHA256 will be
recorded here after construction. Previous rc.1 binaries and their reports remain intact.
No Mac runtime or camera accuracy claim is made by Windows checks.
