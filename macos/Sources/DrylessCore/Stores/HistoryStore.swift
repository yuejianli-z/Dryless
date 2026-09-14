import CoreFoundation
import Foundation

public enum HistoryStoreError: LocalizedError {
    case unrecognizedFormat

    public var errorDescription: String? {
        "The history file has an unrecognized format. The original file was left unchanged."
    }
}

public final class HistoryStore {
    private struct Payload: Codable {
        var version = 2
        var records: [MinuteBlinkRecord]

        private enum CodingKeys: String, CodingKey {
            case version
            case records
        }

        init(version: Int = 2, records: [MinuteBlinkRecord]) {
            self.version = version
            self.records = records
        }

        init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            version = (try? container.decode(Int.self, forKey: .version)) ?? 1
            records = try container.decode([MinuteBlinkRecord].self, forKey: .records)
        }
    }

    private struct DecodedHistory {
        var records: [MinuteBlinkRecord]
        var isLegacy: Bool
    }

    private let fileURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(storageDirectory: URL = applicationSupportDirectory()) {
        fileURL = storageDirectory.appendingPathComponent("blink_data.json")
        encoder = JSONEncoder()
        decoder = JSONDecoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601
    }

    public func appendMinute(_ record: MinuteBlinkRecord) throws {
        var decoded = try loadDecoded()
        if decoded.isLegacy {
            try backupLegacyFileIfNeeded()
        }
        decoded.records.append(record)
        try save(records: decoded.records)
    }

    public func appendMinute(blinks: Int, minuteStart: Date = Date()) throws {
        try appendMinute(MinuteBlinkRecord(bucketStart: minuteStart, blinks: blinks))
    }

    public func loadRecords() throws -> [MinuteBlinkRecord] {
        try loadDecoded().records.sorted { $0.bucketStart < $1.bucketStart }
    }

    public func dateBounds(calendar: Calendar = .current) throws -> ClosedRange<Date>? {
        let records = try loadRecords()
        guard let first = records.first?.bucketStart, let last = records.last?.bucketStart else { return nil }
        return calendar.startOfDay(for: first)...calendar.startOfDay(for: last)
    }

    public func report(
        from startDate: Date,
        through endDate: Date,
        grain requestedGrain: HistoryGrain,
        calendar: Calendar = .current
    ) throws -> HistoryReport {
        let start = calendar.startOfDay(for: min(startDate, endDate))
        let end = calendar.startOfDay(for: max(startDate, endDate))
        let dayAfterEnd = calendar.date(byAdding: .day, value: 1, to: end) ?? end.addingTimeInterval(86_400)
        let selected = try loadRecords().filter { $0.bucketStart >= start && $0.bucketStart < dayAfterEnd }
        let valid = selected.filter { $0.blinks != nil }
        let total = valid.compactMap(\.blinks).reduce(0, +)
        let validDays = Set(valid.map { calendar.startOfDay(for: $0.bucketStart) })
        let summary = HistorySummary(
            totalBlinks: total,
            recordedMinutes: valid.count,
            recordedDays: validDays.count,
            averageRate: valid.isEmpty ? nil : Double(total) / Double(valid.count)
        )
        let grain = resolvedGrain(requestedGrain, start: start, end: end, calendar: calendar)
        let periods = aggregate(valid, from: start, through: end, grain: grain, calendar: calendar)
        return HistoryReport(
            startDate: start,
            endDate: end,
            grain: grain,
            summary: summary,
            periods: periods,
            missingRecords: selected.filter { $0.blinks == nil }.count
        )
    }

    public func loadDailyStats(
        days: Int = 30,
        now: Date = Date(),
        calendar: Calendar = .current
    ) throws -> [DailyBlinkStats] {
        let end = calendar.startOfDay(for: now)
        let start = calendar.date(byAdding: .day, value: -(max(1, days) - 1), to: end) ?? end
        let records = try loadRecords()
        return dates(from: start, through: end, calendar: calendar).compactMap { day in
            let next = calendar.date(byAdding: .day, value: 1, to: day) ?? day.addingTimeInterval(86_400)
            let values = records.filter { $0.bucketStart >= day && $0.bucketStart < next }.compactMap(\.blinks)
            guard !values.isEmpty else { return nil }
            let rates = values.map(Double.init)
            return DailyBlinkStats(
                date: day,
                averageRate: Double(values.reduce(0, +)) / Double(values.count),
                minimumRate: rates.min() ?? 0,
                maximumRate: rates.max() ?? 0,
                totalBlinks: values.reduce(0, +),
                recordedMinutes: values.count,
                minuteRates: rates
            )
        }
    }

    public func todayHourly(now: Date = Date(), calendar: Calendar = .current) throws -> [HourlyBlinkStats] {
        let start = calendar.startOfDay(for: now)
        let end = calendar.date(byAdding: .day, value: 1, to: start) ?? start.addingTimeInterval(86_400)
        let records = try loadRecords().filter { $0.bucketStart >= start && $0.bucketStart < end && $0.blinks != nil }
        let grouped = Dictionary(grouping: records) { calendar.component(.hour, from: $0.bucketStart) }
        return grouped.keys.sorted().map { hour in
            let values = grouped[hour, default: []].compactMap(\.blinks)
            let total = values.reduce(0, +)
            return HourlyBlinkStats(
                hour: hour,
                averageRate: values.isEmpty ? 0 : Double(total) / Double(values.count),
                totalBlinks: total,
                recordedMinutes: values.count
            )
        }
    }

    public func csv(from startDate: Date, through endDate: Date, calendar: Calendar = .current) throws -> String {
        let start = calendar.startOfDay(for: min(startDate, endDate))
        let end = calendar.date(byAdding: .day, value: 1, to: calendar.startOfDay(for: max(startDate, endDate)))
            ?? max(startDate, endDate).addingTimeInterval(86_400)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var rows = ["bucket_start,local_date,local_time,blinks,valid_seconds,session_id,missing_reason"]
        for record in try loadRecords().filter({ $0.bucketStart >= start && $0.bucketStart < end }) {
            let date = record.bucketStart.formatted(.dateTime.year().month(.twoDigits).day(.twoDigits))
            let time = record.bucketStart.formatted(.dateTime.hour(.twoDigits(amPM: .omitted)).minute(.twoDigits))
            rows.append([
                formatter.string(from: record.bucketStart),
                date,
                time,
                record.blinks.map(String.init) ?? "",
                record.validSeconds.map { String(format: "%.3f", $0) } ?? "",
                escapeCSV(record.sessionID ?? ""),
                escapeCSV(record.missingReason ?? "")
            ].joined(separator: ","))
        }
        return rows.joined(separator: "\n") + "\n"
    }

    private func resolvedGrain(
        _ requested: HistoryGrain,
        start: Date,
        end: Date,
        calendar: Calendar
    ) -> HistoryGrain {
        let days = (calendar.dateComponents([.day], from: start, to: end).day ?? 0) + 1
        if requested == .hour, days != 1 { return .day }
        guard requested == .automatic else { return requested }
        if days == 1 { return .hour }
        if days <= 45 { return .day }
        if days <= 210 { return .week }
        return .month
    }

    private func aggregate(
        _ records: [MinuteBlinkRecord],
        from start: Date,
        through end: Date,
        grain: HistoryGrain,
        calendar: Calendar
    ) -> [HistoryPeriod] {
        if grain == .hour {
            return (0..<24).map { hour in
                let hourStart = calendar.date(byAdding: .hour, value: hour, to: start) ?? start
                let hourEnd = calendar.date(byAdding: .hour, value: 1, to: hourStart) ?? hourStart.addingTimeInterval(3_600)
                return makePeriod(records.filter { $0.bucketStart >= hourStart && $0.bucketStart < hourEnd }, start: hourStart, end: hourEnd, naturalStart: hourStart, isPartial: false, calendar: calendar)
            }
        }

        let rangeEnd = calendar.date(byAdding: .day, value: 1, to: end) ?? end.addingTimeInterval(86_400)
        var naturalStart = periodStart(containing: start, grain: grain, calendar: calendar)
        var periods: [HistoryPeriod] = []
        while naturalStart < rangeEnd {
            let naturalEnd = nextPeriod(after: naturalStart, grain: grain, calendar: calendar)
            let visibleStart = max(start, naturalStart)
            let visibleEnd = min(rangeEnd, naturalEnd)
            let matching = records.filter { $0.bucketStart >= visibleStart && $0.bucketStart < visibleEnd }
            periods.append(makePeriod(matching, start: visibleStart, end: visibleEnd, naturalStart: naturalStart, isPartial: visibleStart != naturalStart || visibleEnd != naturalEnd, calendar: calendar))
            naturalStart = naturalEnd
        }
        return periods
    }

    private func makePeriod(
        _ records: [MinuteBlinkRecord],
        start: Date,
        end: Date,
        naturalStart: Date,
        isPartial: Bool,
        calendar: Calendar
    ) -> HistoryPeriod {
        let values = records.compactMap(\.blinks)
        let total = values.isEmpty ? nil : values.reduce(0, +)
        return HistoryPeriod(
            start: start,
            end: end,
            naturalStart: naturalStart,
            isPartial: isPartial,
            recordedMinutes: values.count,
            totalBlinks: total,
            averageRate: total.map { Double($0) / Double(values.count) },
            recordedDays: Set(records.map { calendar.startOfDay(for: $0.bucketStart) }).count
        )
    }

    private func periodStart(containing date: Date, grain: HistoryGrain, calendar: Calendar) -> Date {
        switch grain {
        case .week:
            let weekday = calendar.component(.weekday, from: date)
            let daysFromMonday = (weekday + 5) % 7
            return calendar.date(byAdding: .day, value: -daysFromMonday, to: calendar.startOfDay(for: date)) ?? date
        case .month:
            return calendar.date(from: calendar.dateComponents([.year, .month], from: date)) ?? date
        default:
            return calendar.startOfDay(for: date)
        }
    }

    private func nextPeriod(after date: Date, grain: HistoryGrain, calendar: Calendar) -> Date {
        let component: Calendar.Component
        switch grain {
        case .week: component = .weekOfYear
        case .month: component = .month
        default: component = .day
        }
        return calendar.date(byAdding: component, value: 1, to: date) ?? date.addingTimeInterval(86_400)
    }

    private func dates(from start: Date, through end: Date, calendar: Calendar) -> [Date] {
        var result: [Date] = []
        var cursor = start
        while cursor <= end {
            result.append(cursor)
            guard let next = calendar.date(byAdding: .day, value: 1, to: cursor), next > cursor else { break }
            cursor = next
        }
        return result
    }

    private func loadDecoded() throws -> DecodedHistory {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return DecodedHistory(records: [], isLegacy: false)
        }
        let data = try Data(contentsOf: fileURL)
        if let payload = try? decoder.decode(Payload.self, from: data) {
            return DecodedHistory(records: payload.records, isLegacy: payload.version < 2)
        }
        if let records = decodeWindowsLegacy(data) {
            return DecodedHistory(records: records, isLegacy: true)
        }
        throw HistoryStoreError.unrecognizedFormat
    }

    private func decodeWindowsLegacy(_ data: Data) -> [MinuteBlinkRecord]? {
        guard let value = try? JSONSerialization.jsonObject(with: data),
              let root = value as? [String: Any] else { return nil }
        let days: [String: Any]
        if let value = root["days"] as? [String: Any] {
            days = value
        } else if let date = root["date"] as? String, let history = root["history"] {
            days = [date: history]
        } else {
            return nil
        }

        let dayFormatter = DateFormatter()
        dayFormatter.calendar = Calendar(identifier: .gregorian)
        dayFormatter.locale = Locale(identifier: "en_US_POSIX")
        dayFormatter.dateFormat = "yyyy-MM-dd"
        var records: [MinuteBlinkRecord] = []
        for (dayText, rawEntries) in days {
            guard let day = dayFormatter.date(from: dayText), let entries = rawEntries as? [[String: Any]] else { continue }
            for (index, entry) in entries.enumerated() {
                guard let number = entry["blinks"] as? NSNumber,
                      CFGetTypeID(number) != CFBooleanGetTypeID(),
                      number.intValue >= 0 else { continue }
                let offset: TimeInterval
                if let time = entry["time"] as? String {
                    let parts = time.split(separator: ":").compactMap { Int($0) }
                    offset = parts.count >= 2 ? TimeInterval(parts[0] * 3_600 + parts[1] * 60) : TimeInterval(index * 60)
                } else if let minute = entry["minute"] as? NSNumber {
                    offset = TimeInterval(max(0, minute.intValue) * 60)
                } else {
                    offset = TimeInterval(index * 60)
                }
                records.append(MinuteBlinkRecord(bucketStart: day.addingTimeInterval(offset), blinks: number.intValue, sessionID: "windows-legacy"))
            }
        }
        return records
    }

    private func save(records: [MinuteBlinkRecord]) throws {
        try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try encoder.encode(Payload(records: records)).write(to: fileURL, options: [.atomic])
    }

    private func backupLegacyFileIfNeeded() throws {
        let backup = fileURL.deletingPathExtension().appendingPathExtension("legacy-backup.json")
        guard !FileManager.default.fileExists(atPath: backup.path) else { return }
        try FileManager.default.copyItem(at: fileURL, to: backup)
    }

    private func escapeCSV(_ value: String) -> String {
        guard value.contains(",") || value.contains("\"") || value.contains("\n") else { return value }
        return "\"\(value.replacingOccurrences(of: "\"", with: "\"\""))\""
    }
}
