# Windows acceptance — candidate built and locally verified

最新候选：0.2.0-rc.8。验证记录见 [windows-rc8.md](windows-rc8.md)，源提交和包哈希见 [windows-rc8-validation.json](windows-rc8-validation.json)。
本轮清除悬停窗、压缩顶部开关、统一有效识别频率口径、调整Ding命名和选择即试听；检测算法未变。Mac真机尚未完成共同验收。


Date: 2026-09-13. Version: **0.2.0-rc.1**. Native platform: Windows-11-10.0.26200-SP0.
Binary source commit: `0cb6f305f593f794fd44bb3cf6753266a910d1cf`.
Later commits on the handoff branch only update CI, tests or documentation;
do not infer that the attached binary was rebuilt from those commits.

## Delivered
- Versioned portable EXE: `dist/0.2.0-rc.1/Dryless.exe`.
- Draft release: https://github.com/yuejianli-z/Dryless/releases/tag/untagged-398c3617b64b6a6b8587 (repository owner sign-in required).
- Draft PR: https://github.com/yuejianli-z/Dryless/pull/1
- Windows ZIP, matching source ZIP, SHA256SUMS.txt and build/validation metadata attached.
- Existing Windows desktop shortcut now runs the packaged EXE, with the approved transparent eye icon.
- EXE SHA256: `d816e3bd7c0cdf40c86ad39926f51f2f8a9ff6ad6c1c3a4a123a17d35a23c996`.

## Verified
| Check | Actual result |
| --- | --- |
| `python -m unittest discover -s tests -v` | 22 passed: weighted stats, label collision, microbreak timing |
| `python tools/qa_reminders_windows.py` | 66 passed: exact audio assets, three stages, priority/cancellation, simulated timing, settings behavior |
| `python tools/qa_ui.py` | 184 passed: zh/en, 1100×700 and 1240×780, all three pages and control bounds |
| Source `--self-test` | All passed: resource hashes, model initialization, synthetic no-face frame, fonts, navigation, pause and audio dispatch |
| Packaged `--self-test` | 60 passed outside checkout, PATH limited to Windows directories; no project files or Python required in launch directory |
| Packaged `--camera-smoke` | 12-second smoke: 42 frames and 63 detection samples; no camera errors |
| Shared GitHub checks | Windows and macOS jobs passed: https://github.com/yuejianli-z/Dryless/actions/runs/34753064702 |

The camera smoke had **no face in view**. It proves capture + detector execution,
not face-present blink accuracy. No real camera images were saved or uploaded.
The 25-minute tests use simulated time. They are not a 25-minute live session.

## Still required before stable release
- Mac implementation, packaged app, actual camera/audio/permission testing.
- Face-present blink behavior and a real 25-minute session on the final packaged builds.
- Windows sleep/resume, unplug/replug, and second physical Windows PC acceptance.
- Final combined-distribution licensing/corresponding-source review; current executable is unsigned.
- Merge Mac work, then rebuild/retest Windows from the same final commit and version as Mac.

## Clean Windows runner — PASSED
Run: https://github.com/yuejianli-z/Dryless/actions/runs/34753289552
CI commit: `3af754bbb9031e31631b9d91b2721eef7c6e627b`. Locked dependency install, shared tests, all 66 reminder
checks, all 184 UI checks, standalone build, and packaged self-test with system-only PATH passed.
The CI commit differs from the local binary commit only in test/workflow changes;
the packaged runtime source is unchanged. CI artifacts are attached to the run.
This proves clean-environment build/launch, not physical camera/speaker behavior.
See windows-ci-validation.json for the concise machine-readable result.
