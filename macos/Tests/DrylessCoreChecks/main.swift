import DrylessCore
import Foundation

enum CheckFailure: Error, CustomStringConvertible {
    case failed(String)

    var description: String {
        switch self {
        case .failed(let message): return message
        }
    }
}

func expect(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() { throw CheckFailure.failed(message) }
}

func checkThreeStageReminderContract() throws {
    let settings = AppSettings(alertDelaySeconds: 8, escalationIntervalSeconds: 5)
    try expect(AlertLevel.level(forNoBlinkSeconds: 7.9, settings: settings) == nil, "No alert should fire before 8 seconds")
    try expect(AlertLevel.level(forNoBlinkSeconds: 8, settings: settings) == .mild, "8 seconds should use stage one")
    try expect(AlertLevel.level(forNoBlinkSeconds: 13, settings: settings) == .moderate, "13 seconds should use stage two")
    try expect(AlertLevel.level(forNoBlinkSeconds: 18, settings: settings) == .strong, "18 seconds should use stage three")
    try expect(AlertLevel.level(forNoBlinkSeconds: 23, settings: settings) == .strong, "Later rounds must repeat stage three")

    var scheduler = ReminderScheduler()
    let timeline: [TimeInterval] = [7.9, 8, 8.1, 13, 18, 23, 28]
    let events = timeline.compactMap {
        scheduler.event(elapsed: $0, trackingValid: true, paused: false, microbreakActive: false, settings: settings)
    }
    try expect(events == [.mild, .moderate, .strong, .strong, .strong], "Scheduler should emit once per round and repeat stage three")
    try expect(scheduler.event(elapsed: 33, trackingValid: true, paused: true, microbreakActive: false, settings: settings) == nil, "Pause should suppress reminders")
}

func checkBlinkDetectionCountsClosedToOpenTransitions() throws {
    var engine = BlinkDetectionEngine(
        settings: AppSettings(blinkRatioThreshold: 0.6),
        now: Date(timeIntervalSinceReferenceDate: 100)
    )
    for index in 0..<8 {
        _ = engine.process(
            EyeMeasurement(faceDetected: true, leftOpenness: 0.35, rightOpenness: 0.36),
            at: Date(timeIntervalSinceReferenceDate: 100 + Double(index))
        )
    }

    let closed = engine.process(
        EyeMeasurement(faceDetected: true, leftOpenness: 0.08, rightOpenness: 0.08),
        at: Date(timeIntervalSinceReferenceDate: 109)
    )
    try expect(closed.measurementValid && !closed.eyeOpen && !closed.blinked, "Closing should not count until reopening")

    let reopened = engine.process(
        EyeMeasurement(faceDetected: true, leftOpenness: 0.36, rightOpenness: 0.37),
        at: Date(timeIntervalSinceReferenceDate: 110)
    )
    try expect(reopened.eyeOpen && reopened.blinked && reopened.totalBlinks == 1, "A valid closed-to-open transition should count once")

    let missing = engine.process(
        EyeMeasurement(faceDetected: false, leftOpenness: 0, rightOpenness: 0),
        at: Date(timeIntervalSinceReferenceDate: 111)
    )
    try expect(!missing.faceDetected && !missing.measurementValid && !missing.blinked, "No face must invalidate the signal without a blink")

    engine.updateSettings(AppSettings(blinkRatioThreshold: 0.65))
    let recalibrating = engine.process(
        EyeMeasurement(faceDetected: true, leftOpenness: 0.36, rightOpenness: 0.37),
        at: Date(timeIntervalSinceReferenceDate: 112)
    )
    try expect(!recalibrating.measurementValid, "Threshold edits should force recalibration")
}

func checkBlinkDetectionUsesRecentRelativeBaseline() throws {
    var engine = BlinkDetectionEngine(
        settings: AppSettings(blinkRatioThreshold: 0.6),
        now: Date(timeIntervalSinceReferenceDate: 200)
    )

    for frame in 0..<8 {
        _ = engine.process(
            EyeMeasurement(faceDetected: true, leftOpenness: 0.40, rightOpenness: 0.40),
            at: Date(timeIntervalSinceReferenceDate: 200 + Double(frame))
        )
    }

    for frame in 8..<38 {
        _ = engine.process(
            EyeMeasurement(faceDetected: true, leftOpenness: 0.20, rightOpenness: 0.20),
            at: Date(timeIntervalSinceReferenceDate: 200 + Double(frame))
        )
    }

    let adapted = engine.process(
        EyeMeasurement(faceDetected: true, leftOpenness: 0.20, rightOpenness: 0.20),
        at: Date(timeIntervalSinceReferenceDate: 239)
    )
    try expect(abs((adapted.baseline ?? 0) - 0.20) < 0.000_1, "Baseline should follow the latest 30 samples, not an earlier camera distance")
    try expect(adapted.eyeOpen, "A stable new relative baseline should remain open")
}

func checkLiveRateAndMinuteBuckets() throws {
    let start = Date(timeIntervalSince1970: 1_700_000_000)
    var window = LiveBlinkWindow(startUptime: 100, startDate: start, sessionID: "test")
    var snapshot = try window.sample(at: 100, valid: true, blinked: false)
    for second in 1...30 {
        snapshot = try window.sample(at: 100 + Double(second), valid: true, blinked: second % 3 == 0)
    }
    try expect(snapshot.rate != nil, "Rate should appear after 30 valid seconds")
    try expect(abs((snapshot.rate ?? 0) - 20) < 0.001, "10 blinks in 30 valid seconds should normalize to 20/min")

    snapshot = try window.sample(at: 160, valid: false, blinked: false)
    try expect(snapshot.completedMinutes.count == 1, "Crossing the minute boundary should close one bucket")
    try expect(snapshot.completedMinutes[0].blinks == 10, "The completed valid minute should preserve its blink count")

    var insufficient = LiveBlinkWindow(startUptime: 0, startDate: start, sessionID: "missing")
    _ = try insufficient.sample(at: 0, valid: true, blinked: false)
    _ = try insufficient.sample(at: 20, valid: true, blinked: false)
    let missing = try insufficient.sample(at: 60, valid: false, blinked: false)
    try expect(missing.completedMinutes.first?.blinks == nil, "Less than 30 valid seconds should be missing, not zero")
}

func checkMicrobreakTimingAndFaceGrace() throws {
    var tracker = MicrobreakTracker()
    _ = tracker.update(facePresent: true, at: 0, paused: false)
    var result = tracker.update(facePresent: true, at: 1, paused: false)
    for second in 2...1_199 {
        result = tracker.update(facePresent: true, at: Double(second), paused: false)
    }
    try expect(!result.isActive, "Microbreak should not start before 20 valid minutes")
    result = tracker.update(facePresent: true, at: 1_200, paused: false)
    try expect(result.started && result.isActive, "Microbreak should start at 20 valid minutes")
    result = tracker.update(facePresent: false, at: 1_219, paused: false)
    try expect(result.isActive, "Absence shorter than 20 seconds should keep the prompt active")
    result = tracker.update(facePresent: false, at: 1_220, paused: false)
    try expect(result.ended && !result.isActive, "20 seconds of absence should end the prompt")

    tracker.reset(at: 2_000)
    _ = tracker.update(facePresent: true, at: 2_001, paused: false)
    result = tracker.update(facePresent: true, at: 2_100, paused: true)
    try expect(result.presenceSeconds == 0 && !result.isActive, "Pause should reset microbreak accumulation")
}

func checkHistoryWeightedAggregationAndMissingValues() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    let store = HistoryStore(storageDirectory: root)
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = TimeZone(secondsFromGMT: 0)!
    let day = ISO8601DateFormatter().date(from: "2026-05-14T00:00:00Z")!

    try store.appendMinute(MinuteBlinkRecord(bucketStart: day.addingTimeInterval(9 * 3_600), blinks: 0, validSeconds: 60))
    try store.appendMinute(MinuteBlinkRecord(bucketStart: day.addingTimeInterval(9 * 3_600 + 60), blinks: 30, validSeconds: 60))
    try store.appendMinute(MinuteBlinkRecord(bucketStart: day.addingTimeInterval(10 * 3_600), blinks: nil, validSeconds: 12, missingReason: "insufficient_tracking"))

    let report = try store.report(from: day, through: day, grain: .hour, calendar: calendar)
    try expect(report.summary.totalBlinks == 30, "True zero must remain in the weighted total")
    try expect(report.summary.recordedMinutes == 2, "Missing records must not count as recorded minutes")
    try expect(abs((report.summary.averageRate ?? -1) - 15) < 0.001, "Average should be weighted by recorded minutes")
    try expect(report.missingRecords == 1, "Explicitly missing records should remain distinct")
    try expect(report.periods[9].totalBlinks == 30 && report.periods[10].totalBlinks == nil, "Hourly buckets should preserve zero-versus-missing semantics")

    let csv = try store.csv(from: day, through: day, calendar: calendar)
    try expect(csv.contains("bucket_start,local_date,local_time,blinks"), "CSV should expose minute-level columns")
    try expect(csv.contains("insufficient_tracking"), "CSV should preserve missing reasons")
}

func checkLegacyMacHistoryMigration() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    let file = root.appendingPathComponent("blink_data.json")
    let legacy = """
    {"records":[{"minuteStart":"2026-05-14T09:00:00Z","blinks":0},{"minuteStart":"2026-05-14T09:01:00Z","blinks":18}]}
    """
    try legacy.data(using: .utf8)!.write(to: file, options: .atomic)

    let store = HistoryStore(storageDirectory: root)
    let records = try store.loadRecords()
    try expect(records.compactMap(\.blinks) == [0, 18], "Old Mac records should load without dropping true zero")
    try store.appendMinute(MinuteBlinkRecord(bucketStart: Date(), blinks: 12))
    let backup = root.appendingPathComponent("blink_data.legacy-backup.json")
    try expect(FileManager.default.fileExists(atPath: backup.path), "Migrating old Mac history should preserve a backup")
}

func checkWindowsHistoryAndBadFileProtection() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    let file = root.appendingPathComponent("blink_data.json")
    let windows = """
    {"days":{"2026-05-14":[{"minute":0,"time":"09:00","blinks":0},{"minute":1,"time":"09:01","blinks":20}]}}
    """
    try windows.data(using: .utf8)!.write(to: file, options: .atomic)
    let store = HistoryStore(storageDirectory: root)
    let report = try store.report(
        from: ISO8601DateFormatter().date(from: "2026-05-14T00:00:00Z")!,
        through: ISO8601DateFormatter().date(from: "2026-05-14T00:00:00Z")!,
        grain: .day
    )
    try expect(report.summary.totalBlinks == 20 && report.summary.recordedMinutes == 2, "Windows history should preserve true zero")
    try expect(abs((report.summary.averageRate ?? -1) - 10) < 0.001, "Windows history average should use saved minutes")

    let badRoot = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: badRoot, withIntermediateDirectories: true)
    let badFile = badRoot.appendingPathComponent("blink_data.json")
    let badData = Data("{not-json".utf8)
    try badData.write(to: badFile)
    let badStore = HistoryStore(storageDirectory: badRoot)
    do {
        try badStore.appendMinute(MinuteBlinkRecord(bucketStart: Date(), blinks: 1))
        throw CheckFailure.failed("Appending to bad history should fail")
    } catch is HistoryStoreError {
        let preserved = try Data(contentsOf: badFile)
        try expect(preserved == badData, "Bad history must remain byte-for-byte unchanged")
    }
}

func checkSettingsPersistenceAndBackwardDefaults() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    let fileURL = root.appendingPathComponent("config.json")
    var settings = AppSettings.default
    settings.alertDelaySeconds = 11
    settings.soundTheme = .sharp
    settings.previewVisible = false
    settings.language = .zh

    let store = SettingsStore(fileURL: fileURL)
    try store.save(settings)
    let reloaded = SettingsStore(fileURL: fileURL)
    try expect(reloaded.settings == settings, "All current preferences should persist")

    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    let oldJSON = """
    {"alertDelaySeconds":9,"language":"en"}
    """.data(using: .utf8)!
    try oldJSON.write(to: fileURL, options: .atomic)
    let migrated = SettingsStore(fileURL: fileURL)
    try expect(migrated.settings.alertDelaySeconds == 9, "Known legacy settings should load")
    try expect(migrated.settings.soundTheme == AppSettings.default.soundTheme, "New fields should receive safe defaults")

    let badData = Data("{broken".utf8)
    try badData.write(to: fileURL, options: .atomic)
    let recovered = SettingsStore(fileURL: fileURL)
    try expect(recovered.loadError != nil, "Malformed settings should surface a load error")
    try recovered.save(.default)
    let backup = root.appendingPathComponent("config.invalid-backup.json")
    let backupData = try Data(contentsOf: backup)
    try expect(backupData == badData, "Malformed settings should be backed up before recovery")
}

let checks: [(String, () throws -> Void)] = [
    ("three-stage reminders", checkThreeStageReminderContract),
    ("blink detection", checkBlinkDetectionCountsClosedToOpenTransitions),
    ("recent relative baseline", checkBlinkDetectionUsesRecentRelativeBaseline),
    ("live rate and minute buckets", checkLiveRateAndMinuteBuckets),
    ("microbreak timing", checkMicrobreakTimingAndFaceGrace),
    ("history aggregation", checkHistoryWeightedAggregationAndMissingValues),
    ("legacy Mac history", checkLegacyMacHistoryMigration),
    ("Windows history and bad files", checkWindowsHistoryAndBadFileProtection),
    ("settings persistence", checkSettingsPersistenceAndBackwardDefaults)
]

do {
    for (name, check) in checks {
        try check()
        print("PASS \(name)")
    }
    print("All DrylessCore checks passed")
} catch {
    fputs("FAIL \(error)\n", stderr)
    exit(1)
}
