# Dryless 0.2.0 shared behavior contract

This file defines the product behavior shared by the Windows and macOS apps.
Each platform may use its native window, navigation, typography, and control
patterns; the user-visible behavior below must remain equivalent.

## Privacy and storage

- Camera frames are processed locally in memory and are never uploaded or saved.
- Only settings and numeric minute-level blink history are stored locally.
- No API key, account, cloud service, or facial template is required.

## Camera, preview, alerts, and sound

These controls are independent:

| Control | Camera | Detection and history | Visual reminders | Sound |
| --- | --- | --- | --- | --- |
| Hide preview | running | running | unchanged | unchanged |
| Pause reminders | running | running | paused | paused |
| Stop camera | released | stopped | stopped | stopped |
| Mute | running | running | running | muted |

The app remembers the user's explicit camera choice. Stopping the camera clears
the preview and resets the active session. Sleep, lock, camera loss, permission
denial, and device errors must not be presented as normal monitoring.

Windows uses its notification-area tray and macOS uses its menu bar for opening
the app, camera control, pausing, sound, and quitting. Camera state is shared
between the main window and the system menu.

## Blink measurement

- One complete closed-to-open eye cycle counts as one blink.
- Invalid eye detection and missing-face time do not count as valid observation.
- The live rate is a rolling 60-second rate:
  `blinks in valid intervals × 60 / valid eye-detection seconds`.
- A rate is shown only after at least 30 valid seconds in the window.
- Completed one-minute rhythm cells use the same denominator rule. A measured
  zero remains zero; missing data remains missing.
- History averages are weighted by recorded duration rather than averaging
  already-averaged display values.

## Reminders and sounds

- Blink reminders have exactly three stages: first, second, and stronger.
- Defaults are 8 seconds before stage one and 5 seconds between later stages.
  Stage three repeats at the interval until a blink or state change resets it.
- Four bundled themes are available: Polite, Sharp, Ding, and Blip. Selecting a
  theme previews stage one; **Preview all 3** plays all three stages in order.
- A single cancellable audio channel prevents overlapping reminders.
- Continuous detected presence triggers one microbreak prompt after 20 minutes.
  It has one fixed sound, temporarily takes priority over blink reminders, and
  does not interrupt blink measurement or numeric history.

## Monitor, statistics, and settings

- Monitor shows current camera/detection state, rolling rate, time since the last
  blink, microbreak progress, recent minute rhythm, and short eye-care tips.
- Stats provides date ranges, hour/day/week/month aggregation, total blinks,
  recorded minutes, recorded days, weighted average rate, and CSV export.
- Settings controls reminder timing, the four sound themes, preview, resolution,
  advanced detection parameters, and English/Simplified Chinese language.
- Language changes text only; it must not shift the stable control layout.
- Automatic hover tooltips are not used for information already visible in the UI.

## Cross-platform acceptance

Both apps must preserve the same three reminder stages, 20-minute microbreak,
valid-time rate formula, local history semantics, sound families, camera/privacy
boundary, and bilingual terminology. Camera accuracy and platform packaging must
be verified on the corresponding operating system and hardware.

---

# Dryless 0.2.0 双平台功能约定

Windows 与 macOS 保持相同的产品逻辑，同时各自采用符合系统习惯的窗口、导航、
字体和控件。两端共同遵循以下规则：摄像头画面只在本机内存中分析，不上传也不
保存；本地只保留设置和按分钟记录的数值历史。

- 隐藏预览、暂停提醒、静音和关闭摄像头是四个独立操作。
- 一次完整的闭眼再睁眼计为一次眨眼；无效识别时间不进入频率分母。
- 实时频率按最近 60 秒内“有效区间眨眼数 × 60 ÷ 有效眼部识别秒数”计算，
  有效识别不足 30 秒时不显示频率。
- 固定分钟节律使用相同分母规则；真实零值与缺测严格区分。
- 眨眼提醒只有首次、再次、加强三档；默认 8 秒首次、5 秒递进，加强档持续重复。
- 内置 Polite、Sharp、Ding、Blip 四套三档声音；切换音色试听首档，试听三档按
  顺序播放全部三级。
- 连续识别到用户在场 20 分钟后触发一次微休息；微休息优先于眨眼提醒，但检测
  与数值记录继续。
- 监测、统计、设置三大模块，以及 CSV、本地历史、中英文切换和系统托盘或菜单栏
  快捷控制，在两端保持功能对应。
- 自动悬停黑框不承载界面中已经明确显示的信息。
