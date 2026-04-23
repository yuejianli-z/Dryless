# Dryless

**Blink more, dry less.**

[Download the latest Windows release](https://github.com/yuejianli-z/Dryless/releases/latest)

[下载最新 Windows 版本](https://github.com/yuejianli-z/Dryless/releases/latest)

Dryless is a local-first Windows desktop app that monitors blink frequency in real time and reminds users to blink before eye strain and dry-eye discomfort build up.

Dryless 是一个本地优先的 Windows 桌面应用，用于实时监测眨眼频率，并在长时间未眨眼时提醒用户主动眨眼，帮助缓解用眼疲劳和干眼不适。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## Download / 下载

For most users, download the latest `Dryless.exe` from GitHub Releases and double-click to run it.

对于大多数用户，直接从 GitHub Releases 下载最新的 `Dryless.exe`，双击即可运行。

Release page / 发布页:

- https://github.com/yuejianli-z/Dryless/releases

Notes / 说明:

- The release executable is intended to be self-contained on Windows.
- You do not need to install Python when using the release executable.
- The executable is currently unsigned, so Windows SmartScreen or antivirus software may show a warning.
- If you prefer, you can also build and run Dryless from source.

- 发布版 EXE 面向 Windows 开箱即用。
- 使用发布版 EXE 时不需要另外安装 Python。
- 由于当前 EXE 未签名，Windows SmartScreen 或杀毒软件可能会弹出提示。
- 如果你更谨慎，也可以从源码自行构建运行。

## Features / 功能

- Real-time blink detection powered by MediaPipe
- Local-only camera processing
- No camera frame upload
- No camera image or video storage
- Adaptive eye-openness baseline
- Escalating audio alerts
- Session stats and local history
- English and Chinese UI strings
- Windows tray integration

- 基于 MediaPipe 的实时眨眼检测
- 摄像头画面仅在本地处理
- 不上传摄像头画面
- 不保存摄像头图片或视频
- 自适应眼部开合基线
- 逐级增强的声音提醒
- 会话统计与本地历史记录
- 中英文界面文案
- Windows 托盘集成

## Privacy / 隐私说明

Dryless is designed as a local-first desktop app.

Dryless 被设计为一个本地优先的桌面应用。

What Dryless does / Dryless 会做什么:

- Opens your local webcam through OpenCV
- Processes frames in memory to estimate eye openness and blink events
- Displays a live preview inside the app
- Stores local settings and numeric blink statistics under `~/.blink_reminder/`

- 通过 OpenCV 打开本机摄像头
- 在内存中处理画面，用于估算眼睛开合程度和眨眼事件
- 在应用内显示实时预览
- 将本地设置和数字化眨眼统计保存到 `~/.blink_reminder/`

What Dryless does not do / Dryless 不会做什么:

- It does not upload camera frames
- It does not save camera images
- It does not record video
- It does not collect account information
- It does not include analytics or telemetry logic in the source code

- 不上传摄像头画面
- 不保存摄像头图片
- 不录制视频
- 不收集账号信息
- 源码中不包含分析统计或遥测上报逻辑

## Requirements / 运行要求

For the release executable / 对于发布版 EXE:

- Windows
- A working webcam

- Windows 系统
- 可用摄像头

For running from source / 对于源码运行:

- Windows
- Python 3.10+
- A working webcam
- Dependencies listed in `requirements.txt`

- Windows 系统
- Python 3.10+
- 可用摄像头
- `requirements.txt` 中列出的依赖

## Run From Source / 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

The repository currently includes `face_landmarker.task`, the MediaPipe face model required by the app.

当前仓库包含应用所需的 MediaPipe 人脸模型文件 `face_landmarker.task`。

Bundled custom fonts are optional. If `assets/fonts/` is missing, Dryless falls back to system fonts.

自定义字体资源是可选的。如果缺少 `assets/fonts/`，Dryless 会自动回退到系统字体。

If you remove the model file, download it from MediaPipe and place it in the project root as:

如果你移除了模型文件，需要从 MediaPipe 下载，并放到项目根目录：

```text
face_landmarker.task
```

## Build / 打包

Install PyInstaller and run:

安装 PyInstaller 后运行：

```bash
pip install pyinstaller
python build.py
```

The generated executable is written to:

生成的 EXE 文件位于：

```text
dist/Dryless.exe
```

Build outputs should not be committed to Git. Publish executables through GitHub Releases instead.

构建产物不建议提交到 Git 仓库，推荐通过 GitHub Releases 发布 EXE。

## Project Structure / 项目结构

```text
dryless/
  main.py              App entry point
  ui.py                Main PyQt window and detection worker
  blink_detector.py    MediaPipe blink detection logic
  alert.py             Audio alert manager
  config.py            Local settings persistence
  history_store.py     Local blink statistics storage
  i18n.py              English and Chinese UI strings
  theme.py             UI colors and visual tokens
  tray.py              Windows tray integration
  screens/             Monitor, stats, and settings screens
  widgets/             Reusable PyQt widgets
  sounds/              Alert sound files
  build.py             PyInstaller build script
  face_landmarker.task MediaPipe face model
```

## Release Strategy / 发布方式

Recommended GitHub layout:

- Source code in the repository
- Executable files in GitHub Releases
- Version tags such as `v0.1.0`, `v0.1.1`, `v0.2.0`

推荐 GitHub 发布方式：

- 仓库中放源码
- GitHub Releases 中放 EXE
- 使用 `v0.1.0`、`v0.1.1`、`v0.2.0` 这样的版本标签

## Known Notes / 已知说明

- Dryless is currently focused on Windows
- The release executable may trigger warnings because it is unsigned
- Camera access can be blocked by Windows privacy settings or corporate security policies
- Blink detection quality depends on lighting, camera angle, face visibility, and glasses reflections

- Dryless 当前主要面向 Windows
- 发布版 EXE 因未签名，可能触发系统或杀毒软件提示
- 摄像头权限可能被 Windows 隐私设置或公司安全策略阻止
- 眨眼检测效果会受到光线、摄像头角度、人脸可见度、眼镜反光等因素影响

## Contributing / 参与贡献

Issues and pull requests are welcome. Please keep privacy and local-first behavior as core project principles.

欢迎提交 Issue 和 Pull Request。请始终将隐私保护和本地优先作为项目核心原则。

## License / 许可证

MIT License. See [LICENSE](LICENSE).

本项目使用 MIT License，详见 [LICENSE](LICENSE)。
