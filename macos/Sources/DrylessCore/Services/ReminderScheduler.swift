import Foundation

public struct ReminderScheduler {
    private var lastEventRound: Int?

    public init() {}

    public mutating func event(
        elapsed: TimeInterval,
        trackingValid: Bool,
        paused: Bool,
        microbreakActive: Bool,
        settings: AppSettings
    ) -> AlertLevel? {
        guard trackingValid, !paused, !microbreakActive else {
            reset()
            return nil
        }

        let delay = TimeInterval(max(0, settings.alertDelaySeconds))
        guard elapsed >= delay else {
            lastEventRound = nil
            return nil
        }

        let interval = TimeInterval(max(1, settings.escalationIntervalSeconds))
        let round = Int((elapsed - delay) / interval)
        guard round != lastEventRound else { return nil }
        lastEventRound = round
        return AlertLevel(rawValue: min(2, round)) ?? .strong
    }

    public mutating func reset() {
        lastEventRound = nil
    }
}
