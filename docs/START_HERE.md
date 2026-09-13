# Dryless 双平台交接入口

目标：在同一 GitHub Release 发布同一版本号的 Windows 与 Mac 应用。
功能一致；整体布局一致；窗口、菜单栏、字体回退等细节遵循各自系统。

## 当前接力顺序
0. 用户最新要求：先评估和对接，暂不合并/替换 main，也不公开正式 Release。
1. Windows：最新源码整理到 codex/dryless-design-v2，构建候选 EXE、运行测试、记录结果。
2. Mac mini：从上述分支创建 codex/macos-v0.2.0；先读 MAC_HANDOFF.md 和 FEATURE_PARITY.md。
3. Mac：适配、真机验收，提交 PR 回 codex/dryless-design-v2，并更新 release/macos.md。
4. Windows：拉取合并后的代码，重新跑 Windows 回归并重建。不可发布旧提交的 Windows 包。
5. 两平台在同一最终提交通过 RELEASE_CHECKLIST.md，再创建 v0.2.0 正式 tag/release。

## 如何通信
GitHub 分支/PR + 本目录交接文档是共同记录。登录相同 Codex 账号不替代源码同步。
开始工作先 git fetch，阅读另一平台最新验收记录；结束时提交并 push。
需要对方处理的问题写在 PR 描述/评论中，明确文件、复现步骤与预期行为。
不要同时修改同一共享模块；Mac API 适配尽量放独立模块。

版本：version.py；候选：0.2.0-rc.1；正式目标：0.2.0。
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
若采用新的原生 UI 技术，先写明如何复用/调用共享检测与提醒核心，防止分裂为两套业务逻辑。
