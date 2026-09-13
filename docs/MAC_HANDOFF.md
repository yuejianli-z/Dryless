# Mac mini 接手说明 · 已有原生分支

2026-09-13 已收到 `codex/macos-native` 的原生 SwiftUI 实现。
保留该分支、现有页面和 macos/ 代码，不用 Windows 目录覆盖，不要求换成 Qt。
此文件替代此前“从 Windows 分支新建 Python/Qt Mac 版本”的旧流程。

## 现在先做什么

1. 提交/保存本地改动，`git fetch origin`。
2. 读取 Windows 分支上的最新功能定义，不需要先合并任何代码：

```sh
git show origin/codex/dryless-design-v2:docs/FEATURE_PARITY.md
git show origin/codex/dryless-design-v2:docs/MAC_REVIEW.md
```

3. 依 MAC_REVIEW.md 的 M1–M7 改 Mac：真实摄像头开关 → 统一状态/暂停 → 三档声音与微休息 →
   统计/数据 → 参数 → 发布与真机验收。规则依据 FEATURE_PARITY.md F2。
4. 原生UI继续由Mac设计；所有入口必须调用同一个AppController，不能在View层复制计时/统计。
   Windows维护共同功能合同/验收用例/资源manifest。Vision和MediaPipe可以各自适配，
   但不能因此出现不同的提醒阶段、统计分母或暂停含义。
5. 在GitHub交接问题下回复已做/待做/阻塞项，附提交号。提交PR目标选择
   `codex/dryless-design-v2`，不要合并main。文档不会自动通知另一个本地Codex任务去执行。

## 需要带回的材料

- 监测、统计、设置，以及菜单栏/镜头关闭/提醒中的中英文截图或简短录屏。
  使用占位相机画面，避免提交个人影像；说明设计skill名称，不推测另一台机器安装了什么。
- F2每条验收用例的结果，区分模拟时间、模拟相机和真实硬件。
- `sw_vers`、`uname -m`、Xcode/Swift版本、芯片、摄像头型号、实际采集分辨率。
- 首次权限允许/拒绝/恢复、快速启动取消、释放镜头后其他应用可用、睡眠唤醒、关窗菜单栏驻留。
- 三档实际耳听、声音取消/抢占、自动静音仍显示提示；20分钟微休息真测另行记录。
- 更新 `docs/release/macos.md`，写明命令、提交号、产物版本、SHA256、签名/公证情况与未完成项。

## 实现和发布边界

现有Swift源码可继续使用，核心不是“是否调用同一个Python文件”，而是相同输入得到同一产品行为。
Mac原始几何与WindowsMediaPipe不同，检测准确率仍要真机验证，不能承诺逐帧结果相同。
当前开发脚本的启动成功/pgrep不等于完整验收；资源清单、音频/Logo、版本、许可都要进入应用包。
未确认可用的Intel架构或旧macOS版本不要标支持。Mac mini的外接摄像头需实测。
签名/公证使用用户授权的Apple身份，不提交证书或密钥；本机未签名测试包需明确标注。
正式发布仍要求同一最终提交/版本号的Windows与Mac包，两边回归通过后再决定合并main和发布。
