# Release gate: Windows + macOS

Keep the release a draft until every required item is backed by evidence.
The 2026-09-13 F2 feature review adds requirements beyond Windows rc.1; previous build results do not prove F2 completion.

- [ ] docs/MAC_REVIEW.md W1–W7 and M1–M7 resolved with evidence against FEATURE_PARITY.md F2.
- [ ] True camera stop/release, canceled permission request, stale callbacks and rapid toggling tested on both OSes.
- [ ] Tray/menu controls and close-window background behavior match; explicit Quit releases devices and audio.
- [ ] Zero/missing minutes, weighted means, first blink, minute boundary and midnight tested on both implementations.
- [ ] Shared tips/slogan restored, no invented health scores, no "pause" control falsely presented as camera-off.

- [ ] Windows and Mac built from the same final commit and version.py version.
- [ ] Shared automated tests pass on both OSes; same feature contract, settings and audio assets.
- [ ] Windows portable EXE launches on a clean Windows machine without Python installed.
- [ ] Windows camera/audio/quit/sleep-resume/long-session manual acceptance recorded.
- [ ] Mac .app launches from its distributed package, not just from a source checkout.
- [ ] Mac permission allowed/denied/recovery, camera/audio/menu/quit/sleep-resume acceptance recorded.
- [ ] Real 20-minute session recorded separately from simulated timing checks on both platforms.
- [ ] Chinese and English layouts at supported minimum size; no clipped controls or page scroll.
- [ ] Upgrade retains history/settings; new-user install and missing-camera cases tested.
- [ ] Supported OS versions and architectures are explicit; untested platforms not claimed.
- [ ] Third-party notices and corresponding-source/license obligations reviewed for the combined package.
- [ ] Mac Developer ID signing/notarization completed for normal external distribution; status disclosed.
- [ ] SHA256 sums, exact source archive, dependency/build metadata accompany binaries.
- [ ] Tag v0.2.0 points to the actual final tested commit, then upload BOTH OS assets to one Release.

Never reuse the old Windows candidate after shared-code changes without rebuilding it.
Never promote a draft containing only Windows to the requested dual-platform stable release.
