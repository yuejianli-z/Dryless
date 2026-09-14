import Foundation

public struct EyeMeasurement: Equatable {
    public var faceDetected: Bool
    public var leftOpenness: Double
    public var rightOpenness: Double

    public init(faceDetected: Bool, leftOpenness: Double, rightOpenness: Double) {
        self.faceDetected = faceDetected
        self.leftOpenness = leftOpenness
        self.rightOpenness = rightOpenness
    }

    public var openness: Double {
        max(leftOpenness, rightOpenness)
    }
}

public struct BlinkDetectionResult: Equatable {
    public var faceDetected: Bool
    public var measurementValid: Bool
    public var eyeOpen: Bool
    public var blinked: Bool
    public var totalBlinks: Int
    public var noBlinkSeconds: TimeInterval
    public var currentOpenness: Double
    public var baseline: Double?
    public var ratio: Double?

    public init(
        faceDetected: Bool,
        measurementValid: Bool,
        eyeOpen: Bool,
        blinked: Bool,
        totalBlinks: Int,
        noBlinkSeconds: TimeInterval,
        currentOpenness: Double,
        baseline: Double?,
        ratio: Double?
    ) {
        self.faceDetected = faceDetected
        self.measurementValid = measurementValid
        self.eyeOpen = eyeOpen
        self.blinked = blinked
        self.totalBlinks = totalBlinks
        self.noBlinkSeconds = noBlinkSeconds
        self.currentOpenness = currentOpenness
        self.baseline = baseline
        self.ratio = ratio
    }
}

public struct MinuteBlinkRecord: Codable, Equatable, Identifiable {
    public var bucketStart: Date
    public var blinks: Int?
    public var validSeconds: Double?
    public var sessionID: String?
    public var missingReason: String?

    public init(
        bucketStart: Date,
        blinks: Int?,
        validSeconds: Double? = nil,
        sessionID: String? = nil,
        missingReason: String? = nil
    ) {
        self.bucketStart = bucketStart
        self.blinks = blinks.map { max(0, $0) }
        self.validSeconds = validSeconds.map { max(0, min(60, $0)) }
        self.sessionID = sessionID
        self.missingReason = missingReason
    }

    public var id: String {
        "\(sessionID ?? "legacy")-\(bucketStart.timeIntervalSinceReferenceDate)"
    }

    private enum CodingKeys: String, CodingKey {
        case bucketStart
        case minuteStart
        case blinks
        case validSeconds
        case sessionID
        case missingReason
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        if let value = try? container.decode(Date.self, forKey: .bucketStart) {
            bucketStart = value
        } else {
            bucketStart = try container.decode(Date.self, forKey: .minuteStart)
        }
        blinks = try? container.decodeIfPresent(Int.self, forKey: .blinks)
        validSeconds = try? container.decodeIfPresent(Double.self, forKey: .validSeconds)
        sessionID = try? container.decodeIfPresent(String.self, forKey: .sessionID)
        missingReason = try? container.decodeIfPresent(String.self, forKey: .missingReason)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(bucketStart, forKey: .bucketStart)
        try container.encodeIfPresent(blinks, forKey: .blinks)
        try container.encodeIfPresent(validSeconds, forKey: .validSeconds)
        try container.encodeIfPresent(sessionID, forKey: .sessionID)
        try container.encodeIfPresent(missingReason, forKey: .missingReason)
    }
}

public struct DailyBlinkStats: Equatable, Identifiable {
    public var date: Date
    public var averageRate: Double
    public var minimumRate: Double
    public var maximumRate: Double
    public var totalBlinks: Int
    public var recordedMinutes: Int
    public var minuteRates: [Double]

    public init(
        date: Date,
        averageRate: Double,
        minimumRate: Double,
        maximumRate: Double,
        totalBlinks: Int,
        recordedMinutes: Int,
        minuteRates: [Double]
    ) {
        self.date = date
        self.averageRate = averageRate
        self.minimumRate = minimumRate
        self.maximumRate = maximumRate
        self.totalBlinks = totalBlinks
        self.recordedMinutes = recordedMinutes
        self.minuteRates = minuteRates
    }

    public var id: Date { date }
}

public struct HourlyBlinkStats: Equatable, Identifiable {
    public var hour: Int
    public var averageRate: Double
    public var totalBlinks: Int
    public var recordedMinutes: Int

    public init(hour: Int, averageRate: Double, totalBlinks: Int, recordedMinutes: Int) {
        self.hour = hour
        self.averageRate = averageRate
        self.totalBlinks = totalBlinks
        self.recordedMinutes = recordedMinutes
    }

    public var id: Int { hour }
}

public enum HistoryGrain: String, CaseIterable, Equatable, Identifiable {
    case automatic
    case hour
    case day
    case week
    case month

    public var id: String { rawValue }
}

public struct HistoryPeriod: Equatable, Identifiable {
    public var start: Date
    public var end: Date
    public var naturalStart: Date
    public var isPartial: Bool
    public var recordedMinutes: Int
    public var totalBlinks: Int?
    public var averageRate: Double?
    public var recordedDays: Int

    public init(
        start: Date,
        end: Date,
        naturalStart: Date,
        isPartial: Bool,
        recordedMinutes: Int,
        totalBlinks: Int?,
        averageRate: Double?,
        recordedDays: Int
    ) {
        self.start = start
        self.end = end
        self.naturalStart = naturalStart
        self.isPartial = isPartial
        self.recordedMinutes = recordedMinutes
        self.totalBlinks = totalBlinks
        self.averageRate = averageRate
        self.recordedDays = recordedDays
    }

    public var id: Date { start }
}

public struct HistorySummary: Equatable {
    public var totalBlinks: Int
    public var recordedMinutes: Int
    public var recordedDays: Int
    public var averageRate: Double?

    public static let empty = HistorySummary(totalBlinks: 0, recordedMinutes: 0, recordedDays: 0, averageRate: nil)
}

public struct HistoryReport: Equatable {
    public var startDate: Date
    public var endDate: Date
    public var grain: HistoryGrain
    public var summary: HistorySummary
    public var periods: [HistoryPeriod]
    public var missingRecords: Int

    public init(
        startDate: Date,
        endDate: Date,
        grain: HistoryGrain,
        summary: HistorySummary,
        periods: [HistoryPeriod],
        missingRecords: Int
    ) {
        self.startDate = startDate
        self.endDate = endDate
        self.grain = grain
        self.summary = summary
        self.periods = periods
        self.missingRecords = missingRecords
    }
}
