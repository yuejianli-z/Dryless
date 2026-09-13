# Dryless 双平台交接入口

目标：在同一 GitHub Release 发布同一版本号的 Windows 与 Mac 应用。
功能一致；整体布局一致；窗口、菜单栏、字体回退等细节遵循各自系统。

## 当前接力顺序
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
