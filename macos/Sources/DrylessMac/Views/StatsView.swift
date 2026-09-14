import DrylessCore
import SwiftUI

struct StatsView: View {
    @ObservedObject var controller: AppController

    @State private var range: StatsRange = .last30Days
    @State private var requestedGrain: HistoryGrain = .automatic
    @State private var startDate = Calendar.current.date(byAdding: .day, value: -29, to: Date()) ?? Date()
    @State private var endDate = Date()
    @State private var report: HistoryReport?
    @State private var sessionWindow: SessionWindow = .automatic

    var body: some View {
        HiddenScrollerScrollView {
            VStack(alignment: .leading, spacing: 16) {
                rangeControls
                summaryGrid
                trendPanel
                detailGrid
            }
            .padding(16)
            .frame(maxWidth: 1180, alignment: .topLeading)
            .frame(maxWidth: .infinity, alignment: .top)
        }
        .onAppear {
            applyRange(range)
            reload()
        }
        .onChange(of: range) { _, newValue in
            applyRange(newValue)
            reload()
        }
        .onChange(of: requestedGrain) { _, _ in reload() }
        .onChange(of: startDate) { _, _ in if range == .custom { reload() } }
        .onChange(of: endDate) { _, _ in if range == .custom { reload() } }
        .onChange(of: controller.snapshot.recentMinutes.count) { _, _ in reload() }
    }

    private var rangeControls: some View {
        AppCard(spacing: 12) {
            HStack(spacing: 14) {
                Picker(copy(zh: "时间范围", en: "Range"), selection: $range) {
                    ForEach(StatsRange.allCases) { item in
                        Text(item.title(language: controller.language)).tag(item)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
                .frame(maxWidth: 430)

                Divider().frame(height: 22)

                Picker(copy(zh: "粒度", en: "Grain"), selection: $requestedGrain) {
                    ForEach(HistoryGrain.allCases) { grain in
                        Text(grainTitle(grain)).tag(grain)
                    }
                }
                .frame(width: 150)

                Spacer()

                Button {
                    controller.exportHistory(from: startDate, through: endDate)
                } label: {
                    Label(L10n.text("export_csv", controller.language), systemImage: "square.and.arrow.up")
                }
                .disabled((report?.summary.recordedMinutes ?? 0) == 0)
            }

            if range == .custom {
                HStack(spacing: 12) {
                    DatePicker(copy(zh: "开始", en: "From"), selection: $startDate, displayedComponents: .date)
                    DatePicker(copy(zh: "结束", en: "Through"), selection: $endDate, displayedComponents: .date)
                    Spacer()
                }
            }

            if let message = controller.exportResult {
                Label(message, systemImage: "checkmark.circle")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if let error = controller.historyError {
                Label(error, systemImage: "exclamationmark.triangle")
                    .font(.caption)
                    .foregroundStyle(.red)
            }
        }
    }

    private var summaryGrid: some View {
        let summary = report?.summary ?? .empty
        return LazyVGrid(
            columns: Array(repeating: GridItem(.flexible(), spacing: 12), count: 4),
            spacing: 12
        ) {
            StatusTile(
                title: copy(zh: "加权平均", en: "Weighted average"),
                value: Formatters.optionalRate(summary.averageRate),
                unit: "/min",
                systemImage: "speedometer",
                tint: BrandPalette.sage
            )
            StatusTile(
                title: copy(zh: "眨眼总数", en: "Total blinks"),
                value: "\(summary.totalBlinks)",
                unit: "",
                systemImage: "eye",
                brandEyeState: controller.menuBarEyeState,
                tint: .green
            )
            StatusTile(
                title: copy(zh: "有效分钟", en: "Recorded minutes"),
                value: "\(summary.recordedMinutes)",
                unit: copy(zh: "分钟", en: "min"),
                systemImage: "clock",
                tint: .blue
            )
            StatusTile(
                title: copy(zh: "记录天数", en: "Recorded days"),
                value: "\(summary.recordedDays)",
                unit: copy(zh: "天", en: "days"),
                systemImage: "calendar",
                tint: .orange
            )
        }
        .frame(height: 102)
    }

    private var trendPanel: some View {
        AppCard(spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                SectionHeader(
                    title: copy(zh: "眨眼频率趋势", en: "Blink-rate trend"),
                    subtitle: trendSubtitle
                )
                Spacer()
                if let grain = report?.grain {
                    Text(copy(zh: "按\(grainTitle(grain))汇总", en: "Grouped by \(grainTitle(grain).lowercased())"))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            HistoryTrendChart(periods: report?.periods ?? [], language: controller.language)
                .frame(height: 250)
        }
    }

    private var detailGrid: some View {
        HStack(alignment: .top, spacing: 16) {
            AppCard(spacing: 12, fillsHeight: true) {
                HStack(alignment: .top, spacing: 12) {
                    SectionHeader(
                        title: copy(zh: "当前会话分钟", en: "Current session minutes"),
                        subtitle: copy(zh: "有效分钟保留真实 0；缺失分钟单独标记", en: "True zero is retained; missing minutes stay distinct")
                    )
                    Spacer()
                    Picker(copy(zh: "窗口", en: "Window"), selection: $sessionWindow) {
                        ForEach(SessionWindow.allCases) { window in
                            Text(window.title(language: controller.language)).tag(window)
                        }
                    }
                    .labelsHidden()
                    .pickerStyle(.segmented)
                    .frame(width: 210)
                }
                MinuteStripChart(records: recentRecords, language: controller.language)
                    .frame(height: 126)
                HStack {
                    Label(copy(zh: "有效 \(validRecentMinutes)", en: "Valid \(validRecentMinutes)"), systemImage: "checkmark.circle")
                    Spacer()
                    Label(copy(zh: "缺失 \(missingRecentMinutes)", en: "Missing \(missingRecentMinutes)"), systemImage: "minus.circle")
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, minHeight: 228)

            AppCard(spacing: 12, fillsHeight: true) {
                SectionHeader(
                    title: L10n.text("alerts_title", controller.language),
                    subtitle: copy(zh: "静音时仍会记录触发事件", en: "Events are counted even when sound is muted")
                )
                ForEach(AlertLevel.allCases) { level in
                    HStack(spacing: 10) {
                        Image(systemName: level.systemImage)
                            .foregroundStyle(level == .strong ? .orange : .secondary)
                            .frame(width: 20)
                        Text(level.description(for: controller.language))
                            .font(.subheadline)
                        Spacer()
                        Text("\(controller.alertCounts[level, default: 0])")
                            .font(.subheadline.weight(.semibold).monospacedDigit())
                    }
                    .padding(.horizontal, 11)
                    .frame(height: 38)
                    .background(Color.secondary.opacity(0.055), in: RoundedRectangle(cornerRadius: 7, style: .continuous))
                }
            }
            .frame(width: 330)
            .frame(minHeight: 228)
        }
    }

    private var trendSubtitle: String {
        guard let report else { return L10n.text("stats_empty", controller.language) }
        let start = report.startDate.formatted(.dateTime.year().month().day())
        let end = report.endDate.formatted(.dateTime.year().month().day())
        let missing = report.missingRecords
        return copy(
            zh: "\(start) – \(end) · \(missing) 个明确缺失分钟",
            en: "\(start) – \(end) · \(missing) explicitly missing minutes"
        )
    }

    private var validRecentMinutes: Int {
        recentRecords.filter { $0.blinks != nil }.count
    }

    private var missingRecentMinutes: Int {
        recentRecords.filter { $0.blinks == nil }.count
    }

    private var recentRecords: [MinuteBlinkRecord] {
        Array(controller.snapshot.recentMinutes.suffix(sessionWindow.count(for: controller.snapshot.recentMinutes.count)))
    }

    private func applyRange(_ range: StatsRange) {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        switch range {
        case .last30Days:
            startDate = calendar.date(byAdding: .day, value: -29, to: today) ?? today
            endDate = today
        case .currentYear:
            startDate = calendar.date(from: calendar.dateComponents([.year], from: today)) ?? today
            let nextYear = calendar.date(byAdding: .year, value: 1, to: startDate) ?? today
            endDate = calendar.date(byAdding: .day, value: -1, to: nextYear) ?? today
        case .all:
            if let bounds = controller.historyBounds() {
                startDate = bounds.lowerBound
                endDate = bounds.upperBound
            } else {
                startDate = today
                endDate = today
            }
        case .custom:
            break
        }
    }

    private func reload() {
        report = controller.historyReport(from: startDate, through: endDate, grain: requestedGrain)
    }

    private func grainTitle(_ grain: HistoryGrain) -> String {
        switch (grain, controller.language) {
        case (.automatic, .en): return "Automatic"
        case (.hour, .en): return "Hour"
        case (.day, .en): return "Day"
        case (.week, .en): return "Week"
        case (.month, .en): return "Month"
        case (.automatic, .zh): return "自动"
        case (.hour, .zh): return "小时"
        case (.day, .zh): return "天"
        case (.week, .zh): return "周"
        case (.month, .zh): return "月"
        }
    }

    private func copy(zh: String, en: String) -> String {
        controller.language == .zh ? zh : en
    }
}

private enum StatsRange: String, CaseIterable, Identifiable {
    case last30Days
    case currentYear
    case all
    case custom

    var id: String { rawValue }

    func title(language: AppLanguage) -> String {
        switch (self, language) {
        case (.last30Days, .en): return "30 Days"
        case (.currentYear, .en): return "This Year"
        case (.all, .en): return "All"
        case (.custom, .en): return "Custom"
        case (.last30Days, .zh): return "30 天"
        case (.currentYear, .zh): return "今年"
        case (.all, .zh): return "全部"
        case (.custom, .zh): return "自定义"
        }
    }
}

private enum SessionWindow: String, CaseIterable, Identifiable {
    case automatic
    case fifteen
    case thirty
    case sixty

    var id: String { rawValue }

    func count(for available: Int) -> Int {
        switch self {
        case .automatic:
            if available <= 15 { return 15 }
            if available <= 30 { return 30 }
            return 60
        case .fifteen: return 15
        case .thirty: return 30
        case .sixty: return 60
        }
    }

    func title(language: AppLanguage) -> String {
        switch self {
        case .automatic: return language == .zh ? "自动" : "Auto"
        case .fifteen: return "15"
        case .thirty: return "30"
        case .sixty: return "60"
        }
    }
}
