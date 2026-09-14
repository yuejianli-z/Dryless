import Foundation

enum Formatters {
    static func seconds(_ value: TimeInterval) -> String {
        String(format: "%.1fs", value)
    }

    static func rate(_ value: Double) -> String {
        String(format: "%.1f", value)
    }

    static func optionalRate(_ value: Double?) -> String {
        value.map(rate) ?? "-"
    }

    static func duration(_ value: TimeInterval) -> String {
        let total = max(0, Int(value))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        if hours > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(minutes)m \(seconds)s"
    }
}
