# Dryless 双平台交接入口

目标：在同一 GitHub Release 发布同一版本号的 Windows 与 Mac 应用。
功能一致；整体布局一致；窗口、菜单栏、字体回退等细节遵循各自系统。

## 当前接力顺序（2026-09-13更新）
0. 暂不合并/替换 main，不公开正式 Release。
1. 已收到 Mac 的 codex/macos-native；源码审查见 [MAC_REVIEW.md](MAC_REVIEW.md)。
2. Windows 侧定义的共同功能合同升级为 [FEATURE_PARITY.md F2](FEATURE_PARITY.md)。
   此次为功能审查与定义交接，W1–W7/M1–M7均不因写入文档而视为已实现。
   用户随后要求统一20分钟，Windows实际计时/文案已改；验证见release/windows-rc2.md。
3. Mac 保留现有 SwiftUI 页面，在自己的分支按 M1–M7 修复；Windows 按 W1–W7 补齐。
   先看 MAC_HANDOFF.md；不要重新创建Qt版来覆盖Mac成果。
4. 两端完成合同后，Mac PR 到 codex/dryless-design-v2；整合后双方重新验收/构建。
5. 两平台在同一最终提交通过 RELEASE_CHECKLIST.md，之后再安排正式 tag/release。

共同交接问题：[GitHub #2](https://github.com/yuejianli-z/Dryless/issues/2)。
最新规则为20分钟微休息；旧rc.1报告保留25分钟历史证据，不能当成当前触发值。

## 如何通信
GitHub 分支/PR + 本目录交接文档是共同记录。登录相同 Codex 账号不替代源码同步。
开始工作先 git fetch，阅读另一平台最新验收记录；结束时提交并 push。
需要对方处理的问题写在 PR 描述/评论中，明确文件、复现步骤与预期行为。
不要同时修改同一共享模块；Mac API 适配尽量放独立模块。

版本：version.py；候选：0.2.0-rc.2；正式目标：0.2.0。
目前 Mac 尚未验收；不得把 Windows 构建成功称为双平台完成。

## 当前布局参考（合成测试数据和摄像头占位图）
以下截图来自当前实际代码，不含用户摄像头照片；供 Mac 保持信息架构参考。
- [监测](images/current/monitor-zh.png) / [Monitor](images/current/monitor-en.png)
- [统计](images/current/stats-zh.png) / [Statistics](images/current/stats-en.png)
- [设置](images/current/settings-zh.png) / [Settings](images/current/settings-en.png)

## Mac 如果已经有设计或代码
不要用 Windows 文件夹覆盖 Mac 工作目录。先保存现有 Mac 分支并 push，
在其 PR 中写明：所用设计 skill、当前截图/原生风格、已实现功能、准备改动的共享模块。
Windows 侧先比较两边再决定合并顺序；不要因为“同步仓库”丢掉 Mac 已做好的页面。
GitHub 分支/PR 是交接渠道，不代表两个 Codex 会实时自动互相发消息。
当前 Windows 会话没有可直接连接 Mac 本地任务的工具；双方每次开工读取仓库最新记录。

Mac 可对界面做较大原生适配，不必照搬 Windows 的 Qt 控件。
应保留功能合同和三页信息架构，允许原生窗口、工具栏、侧栏、表单控件、字体与交互的系统差异。
Mac 当前已采用 SwiftUI/Vision；可保留该技术。共同功能以F2合同、资源和验收用例为准，
原生适配器不要求调用同一Python文件，但必须通过同一产品行为测试，模型精度各自真机验证。
