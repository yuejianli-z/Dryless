import Foundation

public enum SoundTheme: String, Codable, CaseIterable, Equatable, Identifiable {
    case polite
    case sharp
    case original
    case blip

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .polite: return "Polite"
        case .sharp: return "Sharp"
        case .original: return "Ding"
        case .blip: return "Blip"
        }
    }
}

public struct AppSettings: Codable, Equatable {
    public var alertDelaySeconds: Int
    public var escalationIntervalSeconds: Int
    public var blinkRatioThreshold: Double
    public var processEveryNFrames: Int
    public var cameraIndex: Int
    public var cameraWidth: Int
    public var cameraHeight: Int
    public var soundEnabled: Bool
    public var soundTheme: SoundTheme
    public var previewVisible: Bool
    public var cameraEnabledOnLaunch: Bool
    public var language: AppLanguage

    public static let `default` = AppSettings()

    public init(
        alertDelaySeconds: Int = 8,
        escalationIntervalSeconds: Int = 5,
        blinkRatioThreshold: Double = 0.60,
        processEveryNFrames: Int = 1,
        cameraIndex: Int = 0,
        cameraWidth: Int = 640,
        cameraHeight: Int = 480,
        soundEnabled: Bool = true,
        soundTheme: SoundTheme = .blip,
        previewVisible: Bool = true,
        cameraEnabledOnLaunch: Bool = false,
        language: AppLanguage = .en
    ) {
        self.alertDelaySeconds = alertDelaySeconds
        self.escalationIntervalSeconds = escalationIntervalSeconds
        self.blinkRatioThreshold = blinkRatioThreshold
        self.processEveryNFrames = processEveryNFrames
        self.cameraIndex = cameraIndex
        self.cameraWidth = cameraWidth
        self.cameraHeight = cameraHeight
        self.soundEnabled = soundEnabled
        self.soundTheme = soundTheme
        self.previewVisible = previewVisible
        self.cameraEnabledOnLaunch = cameraEnabledOnLaunch
        self.language = language
    }

    public init(from decoder: Decoder) throws {
        let defaults = AppSettings.default
        let container = try decoder.container(keyedBy: CodingKeys.self)
        alertDelaySeconds = (try? container.decode(Int.self, forKey: .alertDelaySeconds)) ?? defaults.alertDelaySeconds
        escalationIntervalSeconds = (try? container.decode(Int.self, forKey: .escalationIntervalSeconds)) ?? defaults.escalationIntervalSeconds
        blinkRatioThreshold = (try? container.decode(Double.self, forKey: .blinkRatioThreshold)) ?? defaults.blinkRatioThreshold
        processEveryNFrames = (try? container.decode(Int.self, forKey: .processEveryNFrames)) ?? defaults.processEveryNFrames
        cameraIndex = (try? container.decode(Int.self, forKey: .cameraIndex)) ?? defaults.cameraIndex
        cameraWidth = (try? container.decode(Int.self, forKey: .cameraWidth)) ?? defaults.cameraWidth
        cameraHeight = (try? container.decode(Int.self, forKey: .cameraHeight)) ?? defaults.cameraHeight
        soundEnabled = (try? container.decode(Bool.self, forKey: .soundEnabled)) ?? defaults.soundEnabled
        soundTheme = (try? container.decode(SoundTheme.self, forKey: .soundTheme)) ?? defaults.soundTheme
        previewVisible = (try? container.decode(Bool.self, forKey: .previewVisible)) ?? defaults.previewVisible
        cameraEnabledOnLaunch = (try? container.decode(Bool.self, forKey: .cameraEnabledOnLaunch)) ?? defaults.cameraEnabledOnLaunch
        language = (try? container.decode(AppLanguage.self, forKey: .language)) ?? defaults.language
    }
}
