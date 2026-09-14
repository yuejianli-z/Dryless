import Foundation

public func applicationSupportDirectory() -> URL {
    if let override = ProcessInfo.processInfo.environment["DRYLESS_DATA_DIR"], !override.isEmpty {
        return URL(fileURLWithPath: override, isDirectory: true).standardizedFileURL
    }
    let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
        ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support")
    return base.appendingPathComponent("Dryless", isDirectory: true)
}
