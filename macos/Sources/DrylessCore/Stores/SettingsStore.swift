import Combine
import Foundation

public final class SettingsStore: ObservableObject {
    @Published public private(set) var settings: AppSettings
    @Published public private(set) var loadError: String?

    private let fileURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private var requiresBackupOnSave: Bool

    public init(fileURL: URL = SettingsStore.defaultFileURL()) {
        self.fileURL = fileURL
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
        self.requiresBackupOnSave = false
        self.encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        do {
            self.settings = try Self.load(from: fileURL, decoder: decoder)
            self.loadError = nil
        } catch {
            self.settings = .default
            self.loadError = error.localizedDescription
            self.requiresBackupOnSave = FileManager.default.fileExists(atPath: fileURL.path)
        }
    }

    public func replace(_ settings: AppSettings) {
        self.settings = settings
    }

    public func mutate(_ update: (inout AppSettings) -> Void) throws {
        var next = settings
        update(&next)
        try save(next)
    }

    public func save(_ settings: AppSettings) throws {
        try FileManager.default.createDirectory(
            at: fileURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        if requiresBackupOnSave {
            let backup = fileURL.deletingPathExtension().appendingPathExtension("invalid-backup.json")
            if !FileManager.default.fileExists(atPath: backup.path) {
                try FileManager.default.copyItem(at: fileURL, to: backup)
            }
            requiresBackupOnSave = false
        }
        let data = try encoder.encode(settings)
        try data.write(to: fileURL, options: [.atomic])
        self.settings = settings
        self.loadError = nil
    }

    public static func defaultFileURL() -> URL {
        applicationSupportDirectory().appendingPathComponent("config.json")
    }

    private static func load(from fileURL: URL, decoder: JSONDecoder) throws -> AppSettings {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return .default
        }
        let data = try Data(contentsOf: fileURL)
        return try decoder.decode(AppSettings.self, from: data)
    }
}
