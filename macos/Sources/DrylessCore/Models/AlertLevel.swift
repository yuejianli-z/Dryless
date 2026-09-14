import Foundation

public enum AlertLevel: Int, Codable, CaseIterable, Comparable, Identifiable {
    case mild = 0
    case moderate = 1
    case strong = 2

    public var id: Int { rawValue }

    public static func < (lhs: AlertLevel, rhs: AlertLevel) -> Bool {
        lhs.rawValue < rhs.rawValue
    }

    public static func level(forNoBlinkSeconds seconds: TimeInterval, settings: AppSettings) -> AlertLevel? {
        let delay = TimeInterval(max(0, settings.alertDelaySeconds))
        guard seconds >= delay else { return nil }

        let interval = TimeInterval(max(1, settings.escalationIntervalSeconds))
        let round = Int((seconds - delay) / interval)
        return AlertLevel(rawValue: min(2, max(0, round))) ?? .strong
    }

    public func description(for language: AppLanguage) -> String {
        switch (self, language) {
        case (.mild, .en): return "First reminder"
        case (.moderate, .en): return "Second reminder"
        case (.strong, .en): return "Strong reminder"
        case (.mild, .zh): return "首次提醒"
        case (.moderate, .zh): return "再次提醒"
        case (.strong, .zh): return "加强提醒"
        }
    }

    public var systemImage: String {
        switch self {
        case .mild: return "bell"
        case .moderate: return "bell.badge"
        case .strong: return "exclamationmark.triangle"
        }
    }
}
