# Mac mini 接手说明

先读 START_HERE.md、FEATURE_PARITY.md、release/windows.md。
Windows 最新基线在 codex/dryless-design-v2，不是旧 main。

```sh
git clone https://github.com/yuejianli-z/Dryless.git
cd Dryless
git fetch origin
git switch -c codex/macos-v0.2.0 origin/codex/dryless-design-v2
```

## 按顺序完成
1. 记录 sw_vers、uname -m、芯片与摄像头；检查 Mac 的 Python/MediaPipe/Qt wheel 兼容性。
   创建本机 .venv，不复制 Windows .venv；以 requirements-windows.lock 为版本参考，
   新增 requirements-macos.lock，实际安装成功后记录版本。不要宣称未经测过的 Intel 支持。
2. `alert.py` 当前直接 import winsound。抽出小型播放/停止后端：Windows 保持原行为，
   Mac 用可靠的原生/Qt 后端。保留同一 AudioChannel 的优先级、取消和三档语义。
   微休息 > 试听 > 眨眼。增加跨后端测试，不得用四档/重复次数取代现有音频。
3. `ui.py`/`widgets/title_bar.py`/`widgets/window_frame.py` 适配 macOS 窗口、菜单栏、
   隐藏/重开/退出；尽量采用原生窗口装饰。保持三页总体布局和绿色视觉。
4. `theme.py` 处理字体回退；保留品牌 Georgia 斜体略粗字标和随包字体。
   检查 Retina 与中英文，1100×700 和 1240×780 逻辑像素无纵向滚动。
5. 摄像头权限：.app 的 Info.plist 填 NSCameraUsageDescription，按签名方式配置
   camera entitlement。测试首次允许、拒绝、重新允许、占用、拔插、睡眠唤醒。
   Mac mini 需外接摄像头/带摄像头显示器；CI 无真实摄像头不能代替本机测试。
6. 实现 build_macos.py，打包全部 release-assets.json 素材及许可证，生成 .app/.dmg。
   原人眼 Logo 保持形状；如转 ICNS，只转格式，不生成新图形。
7. 跑共享单测、界面检查、真实使用验收；在 release/macos.md 填版本/提交/机器/命令/结果。
   正常25分钟微休息真测和加速测试分别记录。测试三档试听、实时提醒与抢占。
8. 提交 PR 到 codex/dryless-design-v2。发布前 Windows 必须拉取共享改动后重新验证和构建。

## 发布边界
原 Windows build.py 只针对 Windows，不应在 Mac 硬跑。
本候选没有完成 Mac 支持；不要通过跳过测试/禁用音频来得到“成功”。
签名/公证需要用户 Apple Developer 身份，在需要时再让用户提供授权，不提交密钥。
无身份时可以提供明确标注未签名的本机测试包，但不能标记公开发布验收通过。
最终发布同一提交、同一版本号、分别命名 Windows/macOS/架构的包及 SHA256。
