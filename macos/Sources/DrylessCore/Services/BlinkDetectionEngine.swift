import Foundation

public struct BlinkDetectionEngine {
    private var settings: AppSettings
    private var blinkCount: Int
    private var lastBlinkDate: Date
    private var wasOpen = true
    private var isOpen = true
    private var currentOpenness = 0.0
    private var baseline: Double?
    private var ratio: Double?
    private var buffer: [Double] = []
    private var wasTrackingValid = false

    private let bufferSize = 30

    public init(settings: AppSettings = .default, now: Date = Date()) {
        self.settings = settings
        self.blinkCount = 0
        self.lastBlinkDate = now
    }

    public mutating func updateSettings(_ settings: AppSettings) {
        let thresholdChanged = settings.blinkRatioThreshold != self.settings.blinkRatioThreshold
        self.settings = settings
        if thresholdChanged {
            recalibrate()
        }
    }

    public mutating func reset(at date: Date = Date()) {
        resetReminderClock(at: date)
    }

    public mutating func resetSession(at date: Date = Date()) {
        blinkCount = 0
        baseline = nil
        buffer = []
        currentOpenness = 0
        resetReminderClock(at: date)
    }

    public mutating func resetReminderClock(at date: Date = Date()) {
        lastBlinkDate = date
        wasOpen = true
        isOpen = true
        ratio = nil
        wasTrackingValid = false
    }

    public mutating func recalibrate(at date: Date = Date()) {
        baseline = nil
        buffer = []
        currentOpenness = 0
        resetReminderClock(at: date)
    }

    public mutating func process(_ measurement: EyeMeasurement, at date: Date = Date()) -> BlinkDetectionResult {
        var blinked = false

        if measurement.faceDetected {
            currentOpenness = max(0, measurement.openness)
            buffer.append(currentOpenness)
            if buffer.count > bufferSize {
                buffer.removeFirst(buffer.count - bufferSize)
            }

            if buffer.count >= 8 {
                baseline = percentile(buffer, percentile: 0.80)
            }

            let measurementValid = baseline != nil
            if let baseline, baseline > 0 {
                ratio = currentOpenness / baseline
                isOpen = (ratio ?? 0) >= settings.blinkRatioThreshold
            } else {
                ratio = nil
                isOpen = true
            }

            if measurementValid, wasTrackingValid, !wasOpen, isOpen {
                blinkCount += 1
                lastBlinkDate = date
                blinked = true
            }

            wasOpen = isOpen
            if measurementValid, !wasTrackingValid {
                lastBlinkDate = date
            }
            wasTrackingValid = measurementValid
        } else {
            wasOpen = true
            isOpen = true
            ratio = nil
            wasTrackingValid = false
            lastBlinkDate = date
        }

        return BlinkDetectionResult(
            faceDetected: measurement.faceDetected,
            measurementValid: measurement.faceDetected && baseline != nil,
            eyeOpen: isOpen,
            blinked: blinked,
            totalBlinks: blinkCount,
            noBlinkSeconds: max(0, date.timeIntervalSince(lastBlinkDate)),
            currentOpenness: currentOpenness,
            baseline: baseline,
            ratio: ratio
        )
    }

    private func percentile(_ values: [Double], percentile: Double) -> Double {
        guard !values.isEmpty else { return 0 }
        let sorted = values.sorted()
        let clamped = max(0, min(1, percentile))
        let index = Int((Double(sorted.count - 1) * clamped).rounded(.toNearestOrAwayFromZero))
        return sorted[index]
    }
}
