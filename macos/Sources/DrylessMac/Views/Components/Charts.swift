import DrylessCore
import SwiftUI

struct RateRingView: View {
    var rate: Double?
    var alertLevel: AlertLevel?
    var size: CGFloat = 128

    private var progress: Double {
        min(1, max(0, (rate ?? 0) / 30.0))
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(.quaternary, lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(color, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))

            VStack(spacing: 2) {
                Text(Formatters.optionalRate(rate))
                    .font(.system(size: size * 0.22, weight: .bold, design: .rounded))
                Text("/min")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(width: size, height: size)
        .accessibilityElement(children: .combine)
    }

    private var lineWidth: CGFloat {
        max(8, size * 0.09)
    }

    private var color: Color {
        guard let rate else { return .secondary }
        if alertLevel != nil { return .orange }
        if rate < 10 { return .red }
        if rate < 15 { return .orange }
        return .green
    }
}

struct HistoryTrendChart: View {
    var periods: [HistoryPeriod]
    var language: AppLanguage
    @State private var selection: Int?

    private var values: [Double?] { periods.map(\.averageRate) }

    var body: some View {
        if values.allSatisfy({ $0 == nil }) {
            EmptyChartState(
                icon: "chart.xyaxis.line",
                text: language == .zh ? "所选范围暂无有效记录" : "No valid records in this range"
            )
        } else {
            VStack(spacing: 8) {
                selectedSummary
                GeometryReader { proxy in
                    chart(size: proxy.size)
                        .contentShape(Rectangle())
                        .gesture(
                            DragGesture(minimumDistance: 0).onEnded { value in
                                let fraction = min(0.999, max(0, value.location.x / max(1, proxy.size.width)))
                                selection = min(periods.count - 1, Int(fraction * CGFloat(periods.count)))
                            }
                        )
                }
                labels
            }
            .focusable()
            .focusEffectDisabled()
            .onMoveCommand { direction in
                switch direction {
                case .left: selection = max(0, selectedIndex - 1)
                case .right: selection = min(periods.count - 1, selectedIndex + 1)
                default: break
                }
            }
        }
    }

    private func chart(size: CGSize) -> some View {
        let plot = CGRect(x: 4, y: 4, width: max(1, size.width - 8), height: max(1, size.height - 8))
        let ceiling = max(30, values.compactMap { $0 }.max() ?? 30)

        return Canvas { context, _ in
            let bandTop = plot.maxY - CGFloat(20 / ceiling) * plot.height
            let bandBottom = plot.maxY - CGFloat(15 / ceiling) * plot.height
            context.fill(
                Path(CGRect(x: plot.minX, y: bandTop, width: plot.width, height: max(1, bandBottom - bandTop))),
                with: .color(.green.opacity(0.08))
            )

            for rate in [10.0, 20.0, 30.0] where rate <= ceiling {
                let y = plot.maxY - CGFloat(rate / ceiling) * plot.height
                var grid = Path()
                grid.move(to: CGPoint(x: plot.minX, y: y))
                grid.addLine(to: CGPoint(x: plot.maxX, y: y))
                context.stroke(grid, with: .color(.secondary.opacity(0.18)), style: StrokeStyle(lineWidth: 1, dash: [3, 4]))
            }

            var segment = Path()
            var hasSegment = false
            for (index, value) in values.enumerated() {
                guard let value else {
                    if hasSegment {
                        context.stroke(segment, with: .color(BrandPalette.sage), style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))
                    }
                    segment = Path()
                    hasSegment = false
                    continue
                }
                let x = plot.minX + CGFloat(index) / CGFloat(max(1, values.count - 1)) * plot.width
                let y = plot.maxY - CGFloat(min(ceiling, max(0, value)) / ceiling) * plot.height
                if hasSegment {
                    segment.addLine(to: CGPoint(x: x, y: y))
                } else {
                    segment.move(to: CGPoint(x: x, y: y))
                    hasSegment = true
                }
                context.fill(Path(ellipseIn: CGRect(x: x - 2.5, y: y - 2.5, width: 5, height: 5)), with: .color(BrandPalette.sage))
            }
            if hasSegment {
                context.stroke(segment, with: .color(BrandPalette.sage), style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))
            }
        }
    }

    private var labels: some View {
        HStack {
            Text(periodLabel(periods.first))
            Spacer()
            Text(language == .zh ? "绿色区域：15–20 次/分钟" : "Green band: 15–20 blinks/min")
            Spacer()
            Text(periodLabel(periods.last))
        }
        .font(.caption2)
        .foregroundStyle(.secondary)
    }

    private var selectedIndex: Int {
        if let selection {
            return min(periods.count - 1, max(0, selection))
        }
        return periods.lastIndex(where: { $0.averageRate != nil }) ?? 0
    }

    private var selectedSummary: some View {
        let period = periods[selectedIndex]
        return HStack(spacing: 12) {
            Text(detailPeriodLabel(period))
                .fontWeight(.medium)
            if period.isPartial {
                Text(language == .zh ? "部分周期" : "Partial period")
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(period.averageRate.map { "\(Formatters.rate($0)) /min" } ?? "-")
            Text(language == .zh ? "\(period.recordedMinutes) 分钟" : "\(period.recordedMinutes) min")
            Text(language == .zh ? "\(period.totalBlinks ?? 0) 次" : "\(period.totalBlinks ?? 0) blinks")
            Text(language == .zh ? "\(period.recordedDays) 天" : "\(period.recordedDays) days")
        }
        .font(.caption.monospacedDigit())
        .foregroundStyle(period.averageRate == nil ? .secondary : .primary)
        .padding(.horizontal, 10)
        .frame(height: 30)
        .background(Color.secondary.opacity(0.055), in: RoundedRectangle(cornerRadius: 6, style: .continuous))
    }

    private func detailPeriodLabel(_ period: HistoryPeriod) -> String {
        if Calendar.current.isDate(period.start, inSameDayAs: period.end.addingTimeInterval(-1)) {
            if Calendar.current.component(.hour, from: period.start) != 0 || period.end.timeIntervalSince(period.start) <= 3_600 {
                return period.start.formatted(.dateTime.month().day().hour(.twoDigits(amPM: .omitted)))
            }
            return period.start.formatted(.dateTime.year().month().day())
        }
        let start = period.start.formatted(.dateTime.month().day())
        let end = period.end.addingTimeInterval(-1).formatted(.dateTime.month().day())
        return "\(start) – \(end)"
    }

    private func periodLabel(_ period: HistoryPeriod?) -> String {
        guard let period else { return "" }
        let first = periods.first?.start ?? period.start
        let last = periods.last?.end ?? period.end
        let days = Calendar.current.dateComponents([.day], from: first, to: last).day ?? 0
        if days == 0 {
            return period.start.formatted(.dateTime.hour(.twoDigits(amPM: .omitted)))
        }
        return period.start.formatted(.dateTime.month(.abbreviated).day())
    }
}

struct MinuteStripChart: View {
    var records: [MinuteBlinkRecord]
    var language: AppLanguage
    var showsValidityDetail = true
    var emptyText: String? = nil
    @State private var selection: Int?

    private let slotCount = 30

    private var plottedRecords: [MinuteBlinkRecord?] {
        let visible = Array(records.suffix(slotCount))
        return Array(repeating: nil, count: slotCount - visible.count) + visible.map(Optional.some)
    }

    private var rates: [Double?] {
        plottedRecords.map { record in
            guard let record else { return nil }
            guard let blinks = record.blinks else { return nil }
            let validSeconds = max(LiveBlinkWindow.minimumValidSeconds, record.validSeconds ?? 60)
            return Double(blinks) * 60 / validSeconds
        }
    }

    var body: some View {
        if records.isEmpty {
            EmptyChartState(
                icon: "chart.bar.xaxis",
                text: emptyText ?? (language == .zh ? "完成首个有效分钟后显示" : "Appears after the first valid minute")
            )
        } else {
            VStack(spacing: 8) {
                GeometryReader { proxy in
                    let gap: CGFloat = 3
                    let barWidth = max(2, (proxy.size.width - CGFloat(slotCount - 1) * gap) / CGFloat(slotCount))
                    let ceiling = max(30, rates.compactMap { $0 }.max() ?? 30)
                    HStack(alignment: .bottom, spacing: gap) {
                        ForEach(plottedRecords.indices, id: \.self) { index in
                            RoundedRectangle(cornerRadius: min(2, barWidth / 2))
                                .fill(rates[index].map(color) ?? Color.secondary.opacity(0.16))
                                .frame(
                                    width: barWidth,
                                    height: barHeight(rate: rates[index], ceiling: ceiling, available: proxy.size.height)
                                )
                                .overlay(alignment: .bottom) {
                                    if selectedIndex == index {
                                        Rectangle()
                                            .fill(Color.primary.opacity(0.8))
                                            .frame(height: 2)
                                    }
                                }
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
                    .contentShape(Rectangle())
                    .gesture(
                        DragGesture(minimumDistance: 0).onEnded { value in
                            let fraction = min(0.999, max(0, value.location.x / max(1, proxy.size.width)))
                            selection = min(slotCount - 1, Int(fraction * CGFloat(slotCount)))
                        }
                    )
                }

                selectedDetail
            }
        }
    }

    private var selectedIndex: Int {
        min(slotCount - 1, max(0, selection ?? (slotCount - 1)))
    }

    @ViewBuilder
    private var selectedDetail: some View {
        Group {
            if let record = plottedRecords[selectedIndex] {
                let rate = rates[selectedIndex]
                HStack(spacing: 10) {
                    Text(record.bucketStart.formatted(.dateTime.hour(.twoDigits(amPM: .omitted)).minute(.twoDigits)))
                    Spacer()
                    Text(rate.map { "\(Formatters.rate($0)) /min" } ?? (language == .zh ? "缺失" : "Missing"))
                    Text(language == .zh ? "\(record.blinks ?? 0) 次" : "\(record.blinks ?? 0) blinks")
                    if showsValidityDetail {
                        Text(language == .zh
                            ? "\(Int(record.validSeconds ?? 60)) 秒有效"
                            : "\(Int(record.validSeconds ?? 60)) s valid")
                    }
                }
            } else {
                HStack {
                    Text(language == .zh ? "过去 30 分钟" : "Past 30 minutes")
                    Spacer()
                    Text(language == .zh ? "该分钟无记录" : "No record for this minute")
                }
            }
        }
        .font(.caption2.monospacedDigit())
        .foregroundStyle(.secondary)
    }

    private func barHeight(rate: Double?, ceiling: Double, available: CGFloat) -> CGFloat {
        guard let rate else { return 4 }
        return max(5, CGFloat(max(0, rate) / ceiling) * available)
    }

    private func color(_ value: Double) -> Color {
        if value < 10 { return .red }
        if value < 15 { return .orange }
        return BrandPalette.sage
    }
}

struct EmptyChartState: View {
    var icon: String
    var text: String

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundStyle(.tertiary)
            Text(text)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.secondary.opacity(0.045), in: RoundedRectangle(cornerRadius: 7, style: .continuous))
    }
}
