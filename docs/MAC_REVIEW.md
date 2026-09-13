# Mac 上传分支功能审查与分工

审查时间：2026-09-13；性质：源码功能审查，非 Mac 真机/页面观感验收。

| 对象 | 分支 | 锁定提交 |
| --- | --- | --- |
| Windows | codex/dryless-design-v2 | a11214c8e33abc0fec782b790caa8c9b90f145c1 |
| Mac | codex/macos-native | 01b48807b75da4861e37f766c5a7596065aeb4b8 |
| 共同祖先 / 当前 main | main | a4723a877ef82ce62319f8b65d0087891cc41b0c |

Mac 分支从旧 main 新增独立的 SwiftUI + AVFoundation + Vision 实现（macos/），
没有包含 Windows 最新三档音色、微休息和时间气泡统计。不是简单换皮；不能认为功能已经同步。
此轮未合并任一实现、未执行Mac构建脚本。下表按锁定提交审查；用户后续将微休息改为20分钟，
Windows计时和文案另行同步，最终以最新提交与验收记录为准。

## 值得采用的部分

- MenuBarExtra 常驻入口，以及关闭主窗口仍可找回应用的机制。
- 在工具栏突出“能控制工作状态”的入口。**但已上传代码实际调用 togglePause，
  不是 CameraService.stop，不能据此宣称已经可以关闭摄像头。**
- 下一步建议、自然眨眼/远眺 tips、保留 slogan；Windows 目前都缺少外显或被隐藏。
- SwiftUI 原生侧栏、系统控件、自适应明暗、卡片和信号说明可由 Mac 继续设计。
  本轮没有 Mac 实机截图，以上是从代码可确认的实现方式，不是对实际渲染质量的验收。

## 功能差异总表

| 项目 | Windows 现状 | Mac 现状 | 最终处理 |
| --- | --- | --- | --- |
| 真正关闭摄像头 | 自动启动；仅退出释放；隐藏预览不关镜头 | 自动启动；按钮只暂停处理；stop 未绑定可见入口 | 两端补共同摄像头状态机与真实开关 |
| 驻留与快捷菜单 | 有打开、暂停、退出；关窗退出；图标固定 | MenuBarExtra；打开、暂停、退出；关窗驻留 | 两端补镜头/声音控制、状态图标；Windows 补关窗驻留 |
| 暂停含义 | 暂停提醒，检测/计数继续 | handle 提前 return，检测结果不计入记录 | 统一为只暂停自动提醒 |
| 提醒/音色 | 三档；四套已选音色；三档连听 | 四档；Ping/Glass/Funk/Basso；单档试听 | Mac 对齐既定音频，不重新选音 |
| 最后档重复 | 按间隔继续 | 最后档相同就不再播放 | 统一第三档周期提示直到重置 |
| 音频抢占 | 单通道；微休息/试听/眨眼优先级 | NSSound 独立播放，reset 不停止声音 | Mac 补取消与优先级 |
| 微休息 | 有 25 分钟逻辑及模拟检查 | 未见实现 | Mac 按 F2 第5节补齐 |
| 近期频率 | 首页使用有效分钟加权；worker还留旧混合估算 | 首页用混合估算，最大截到30 | 两端取消旧估算业务用途 |
| 历史范围 | 30天/整年/全部/自选；小时/日/周/月；CSV | 30天每日、当日小时，7日均值；无范围/CSV | Mac 补完整范围、聚合和导出 |
| 零值/平均 | 实际统计走 stats_data，保留0；旧history辅助仍有过滤 | 日/小时过滤0；7日均值按最近7个有记录日简单平均 | Mac 修正；Windows 清理遗留并修采集桶 |
| 健康评分 | 当前三页不用评分 | 根据频率距17.5的距离计算健康分 | 删除评分；可保留一般参考带 |
| 设置 | 参数范围较全、四音色、试听、预览偏好 | 有语言、时长、检测、分辨率；音色/偏好缺失 | 参数范围与生效规则统一 |
| 分辨率应用 | 保存，重启后设置请求分辨率 | 保存width/height但采集固定vga640x480 | 两端按下次镜头启动生效并披露实际分辨率 |
| slogan | subtitle标签存在但hide且未加入布局 | Sidebar已有app_subtitle | Windows恢复；Mac保留 |
| 历史格式 | days字典与旧单日格式 | records数组+ISO日期 | 双向读取/无损迁移，不假设文件名相同就兼容 |
| 发布 | Windows rc.1有构建检查，仍有真机验收未做 | Swift源码+开发构建脚本；无本轮真机证据 | 依F2重新验收，不能沿用“编译成功=发布完成” |

## Mac 修复清单（不改变原生UI技术）

1. **M1 摄像头与状态：** CameraService.start/configureAndStart 无在途保护；权限回调与
   stop 存在迟到启动风险。stop 不清除 previewImage；旧测量仍可能更新状态。
   为每次采集分配 generation，串行驱动启停、完成后确认释放，忽略过期回调。
   AppController.stop 对接所有入口；ContentView、菜单栏不能再用 togglePause 冒充关闭。
2. **M2 暂停/错误语义：** AppController.handle 暂停时直接返回，与Windows“记录继续”不同。
   MonitorView.statusText 只查alertLevel，无脸也可能显示 Normal blink、绿色与健康分。
   Sidebar/MenuBar状态没有完整反映暂停/关闭/错误。统一从一个业务快照派生。
3. **M3 提醒/声音：** AlertLevel含urgent第四档；AlertService.lastPlayedLevel阻止第三档后续重复；
   soundEnabled为false导致trigger不返回成功，提醒次数随静音改变；reset没取消NSSound。
   使用已选三档音频与统一事件计数，补播放所有三档、取消、优先级及微休息。
4. **M4 统计正确性：** HistoryStore.todayHourly/aggregate过滤0；average7是最近7个有记录日的
   简单平均，不是7个日历日加权平均。HabitHeatmap按数组索引而非日期定位，缺测天会前移。
   DailyQualityChart高度使用虚构健康分。改为真实记录数据及日期覆盖，补范围/粒度/CSV。
5. **M5 数据采集：** commitMinuteIfNeeded在新事件计数后提交，第一下/分钟边界可能丢失或错桶；
   保存用now而非bucketStart；未存有效时长，暂停长间隔不能重建真实数据。
   与Windows一起按F2修复，但不要把旧记录分母换成推测的有效秒数。
6. **M6 参数与资源：** CameraService固定vga640x480；设置范围5–20/3–10与Windows5–60/3–30不一致。
   SettingsStore对缺字段的旧JSON整体解码失败后回到默认，需要逐字段默认/错误提示。
   Package.swift未打包共同音频/Logo资源，构建脚本无版本/图标/签名/公证/产物hash信息。
7. **M7 验收：** 现有4项DrylessCoreChecks还明确要求第四档，没覆盖0、缺测、取消启动、
   关闭设备、声音抢占、微休息。须按F2验收表增加测试并在Mac真机验证权限/镜头/音频/驻留。
   Windows不能确认Mac的实际渲染、耳听效果、Vision检测精度或权限体验。

## Windows 实施进度（rc.3 更新）
- W1：显式启停、首次默认关闭、保存选择、取消连接、旧信号隔离、finally 释放已实现。
  锁屏/睡眠重连、系统权限原因细分仍待完成，不宣称完整生命周期全部验收。
- W2：菜单镜头/声音/暂停、关窗驻留、退出释放、闭眼/暂停状态图标已实现。
- W6：首页 tips 与 slogan 已恢复，四项当前会话指标对齐；具体见 release/windows-rc3.md。
- W3/W4/W5 其余逻辑修复仍待完成；W7 本轮增加生命周期集成检查，不替代全部边界和双平台真机验收。

## Windows 原始修复清单（以下是固定提交的审查记录）

1. **W1 摄像头生命周期：** ui.py新增真正的启停控制器、在途保护与状态信号；
   DetectorWorker资源清理用finally覆盖异常路径。清除关闭后的帧/提示，禁止旧信号串入新会话。
2. **W2 驻留：** main.py.create_tray补镜头/声音操作、状态图标；
   ui.py.closeEvent区分隐藏窗口与真正退出；托盘不可用时可安全退出。
3. **W3 提醒边界：** _update_reminders目前按face而非眼部有效性门控；校准期应抑制声音。
   改T/I、暂停/恢复要立即重置计时，不依赖下一帧碰巧纠正；补后台非激活提示验收。
4. **W4 采集/历史：** run里先加当前blink再切分钟，存在首条/边界错桶；append_minute写到今日，
   跨午夜错日期；停止不提交完整待写桶；异常可能未release；空脸分钟会当0保存。
   保留stats_data已正确的零值/范围逻辑，补新缺测元数据与正确落盘；弃用旧健康评分辅助路径。
5. **W5 频率：** 首页节律已按有效秒数计算；worker的旧混合/30上限估算仍会发出，需清理。
   当前历史仍只能称记录时长；不能拿rc.1证据断言已经有可靠有效时长历史。
6. **W6 tips/slogan：** 恢复widgets/sidebar.py隐藏的subtitle；首页纳入简短护眼内容，
   复用现有控件风格和字号，不恢复复杂图表或大弹窗。
7. **W7 集成验证：** 将相机开关、托盘、关窗、声画提醒、跨午夜与统计边界加入回归；
   两端共同改动稳定后再构建新候选，rc.1不因此自动成为新功能包。

## 源码证据（固定审查提交）

Mac关键文件均位于 [Mac审查提交](https://github.com/yuejianli-z/Dryless/tree/01b48807b75da4861e37f766c5a7596065aeb4b8/macos)：
- `Sources/DrylessMac/Stores/AppController.swift`：handle、togglePause、commitMinuteIfNeeded、menuBarSystemImage。
- `Sources/DrylessMac/Services/CameraService.swift`：start、stop、configureAndStart、captureOutput。
- `Sources/DrylessMac/Views/ContentView.swift` 与 `Views/MenuBarStatusView.swift`：实际按钮调用。
- `Sources/DrylessMac/Services/AlertService.swift` 与 `Sources/DrylessCore/Models/AlertLevel.swift`：四档、播放与计数。
- `Sources/DrylessCore/Stores/HistoryStore.swift`、`Views/StatsView.swift`、`Views/Components/Charts.swift`：零值、均值、评分/日期。
- `Sources/DrylessMac/Views/MonitorView.swift`：状态与tips；`Views/SidebarView.swift`、`Support/L10n.swift`：slogan。
- `Sources/DrylessMac/Views/SettingsView.swift`、`DrylessCore/Stores/SettingsStore.swift`：设置范围/保存。
- `Package.swift`、`script/build_and_run.sh`、`Tests/DrylessCoreChecks/main.swift`：资源、构建与已有检查。

Windows关键文件位于 [Windows审查提交](https://github.com/yuejianli-z/Dryless/tree/a11214c8e33abc0fec782b790caa8c9b90f145c1)：
`ui.py`、`main.py`、`alert.py`、`microbreak.py`、`history_store.py`、`stats_data.py`、
`screens/monitor.py`、`screens/stats.py`、`screens/settings.py`、`widgets/sidebar.py`。

## 实施顺序与协作

1. 本轮先发布F2功能合同及此差异表；以GitHub交接问题和PR评论作为双方共同记录。
2. Windows负责F2规则与W1–W7；Mac在现有codex/macos-native保留原生界面，完成M1–M7。
   无需删Mac目录或改成Qt。两个平台按同一组业务事件/用例验证，不能各自改规则。
3. 可并行改各自实现；改公共音频/字段/规则前先在交接问题说明，由Windows维护功能合同。
4. Mac提交以Windows工作分支为目标的PR；先解决共同规则与数据兼容，再决定合并顺序。
   审查期间不合并main、不公开正式Release。
5. Mac补真机截图/操作录屏（用占位画面或去除个人相机内容）、所用设计skill名称和验收记录。
   提供材料后才能做页面细节比较；代码可读不等于Windows可以运行Mac原生应用。
