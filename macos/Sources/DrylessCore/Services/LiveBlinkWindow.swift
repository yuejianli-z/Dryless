import Foundation

public enum LiveBlinkWindowError: Error {
    case nonMonotonicSample
}

public struct LiveBlinkSnapshot: Equatable {
    public var rate: Double?
    public var validSeconds: TimeInterval
    public var blinks: Int
    public var completedMinutes: [MinuteBlinkRecord]

    public init(rate: Double?, validSeconds: TimeInterval, blinks: Int, completedMinutes: [MinuteBlinkRecord]) {
        self.rate = rate
        self.validSeconds = validSeconds
        self.blinks = blinks
        self.completedMinutes = completedMinutes
    }
}

public struct LiveBlinkWindow {
    public static let windowSeconds: TimeInterval = 60
    public static let minimumValidSeconds: TimeInterval = 30
    public static let maximumSampleGap: TimeInterval = 1

    private struct Span {
        var begin: TimeInterval
        var end: TimeInterval
    }

    private struct Bucket {
        var blinks = 0
        var validSeconds: TimeInterval = 0
    }

    private let startUptime: TimeInterval
    private let startDate: Date
    private let sessionID: String
    private var previousUptime: TimeInterval?
    private var previousWasValid = false
    private var events: [TimeInterval] = []
    private var spans: [Span] = []
    private var buckets: [Int: Bucket] = [:]
    private var nextMinute = 0

    public init(startUptime: TimeInterval, startDate: Date, sessionID: String) {
        self.startUptime = startUptime
        self.startDate = startDate
        self.sessionID = sessionID
    }

    public mutating func sample(at uptime: TimeInterval, valid: Bool, blinked: Bool) throws -> LiveBlinkSnapshot {
        guard uptime.isFinite, uptime >= startUptime, previousUptime.map({ uptime >= $0 }) ?? true else {
            throw LiveBlinkWindowError.nonMonotonicSample
        }

        let continuous = previousUptime.map {
            valid && previousWasValid && uptime > $0 && uptime - $0 <= Self.maximumSampleGap
        } ?? false

        if continuous, let previousUptime {
            addExposure(from: previousUptime, to: uptime)
            if blinked {
                events.append(uptime)
                let index = Int((uptime - startUptime) / 60)
                buckets[index, default: Bucket()].blinks += 1
            }
        }

        let currentMinute = Int((uptime - startUptime) / 60)
        var completed: [MinuteBlinkRecord] = []
        while nextMinute < currentMinute {
            let bucket = buckets.removeValue(forKey: nextMinute) ?? Bucket()
            let validSeconds = min(60, bucket.validSeconds)
            let isValid = validSeconds >= Self.minimumValidSeconds
            completed.append(
                MinuteBlinkRecord(
                    bucketStart: startDate.addingTimeInterval(TimeInterval(nextMinute * 60)),
                    blinks: isValid ? bucket.blinks : nil,
                    validSeconds: validSeconds,
                    sessionID: sessionID,
                    missingReason: isValid ? nil : "insufficient_tracking"
                )
            )
            nextMinute += 1
        }

        previousUptime = uptime
        previousWasValid = valid

        let cutoff = uptime - Self.windowSeconds
        events.removeAll { $0 <= cutoff }
        spans.removeAll { $0.end <= cutoff }
        let exposure = min(
            Self.windowSeconds,
            spans.reduce(0) { total, span in
                total + span.end - max(span.begin, cutoff)
            }
        )
        let rate = exposure >= Self.minimumValidSeconds
            ? Double(events.count) * 60 / exposure
            : nil

        return LiveBlinkSnapshot(
            rate: rate,
            validSeconds: exposure,
            blinks: events.count,
            completedMinutes: completed
        )
    }

    private mutating func addExposure(from begin: TimeInterval, to end: TimeInterval) {
        spans.append(Span(begin: begin, end: end))
        var cursor = begin
        while cursor < end {
            let index = Int((cursor - startUptime) / 60)
            let boundary = startUptime + TimeInterval((index + 1) * 60)
            let segmentEnd = min(end, boundary)
            buckets[index, default: Bucket()].validSeconds += segmentEnd - cursor
            cursor = segmentEnd
        }
    }
}
