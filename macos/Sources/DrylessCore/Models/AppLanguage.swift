import Foundation

public enum AppLanguage: String, Codable, CaseIterable, Equatable, Identifiable {
    case en
    case zh

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .en: return "English"
        case .zh: return "中文"
        }
    }
}
