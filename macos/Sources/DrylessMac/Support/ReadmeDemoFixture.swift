import AppKit
import DrylessCore
import Foundation

struct ReadmeDemoFixture {
    let image: NSImage?
    let snapshot: SessionSnapshot
    let alertCounts: [AlertLevel: Int]
    let settingsStore: SettingsStore
    let historyStore: HistoryStore

    static func fromArguments() -> ReadmeDemoFixture? {
        let arguments = ProcessInfo.processInfo.arguments
        guard arguments.contains("--readme-demo") else { return nil }

        let languageValue = value(after: "--readme-demo-language", in: arguments) ?? "zh"
        let language: AppLanguage = languageValue.lowercased() == "en" ? .en : .zh
        let imagePath = value(after: "--readme-demo-image", in: arguments)
        let image = imagePath.flatMap(NSImage.init(contentsOfFile:))

        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("dryless-readme-demo-(UUID().uuidString)", isDirectory: true)
        let settingsStore = SettingsStore(fileURL: root.appendingPathComponent("config.json"))
        settingsStore.replace(
            AppSettings(
                alertDelaySeconds: 8,
                escalationIntervalSeconds: 5,
                blinkRatioThreshold: 0.60,
                processEveryNFrames: 2,
                cameraIndex: 0,
                cameraWidth: 1920,
                cameraHeight: 1080,
                soundEnabled: true,
                soundTheme: .blip,
                previewVisible: true,
                cameraEnabledOnLaunch: true,
                language: language
            )
        )

        let historyStore = HistoryStore(storageDirectory: root)
        let recent = makeRecentMinutes()
        seedHistory(historyStore, recent: recent)

        return ReadmeDemoFixture(
            image: image,
            snapshot: SessionSnapshot(
                faceDetected: true,
                measurementValid: true,
                eyeOpen: true,
                eyeRatio: 0.93,
                blinkRate: 18.0,
                rollingValidSeconds: 60,
                rollingBlinks: 18,
                noBlinkSeconds: 2.1,
                totalBlinks: 537,
                alertLevel: nil,
                sessionDuration: 1_938,
                recentMinutes: recent,
                microbreakActive: false,
                microbreakPresenceSeconds: 1_938,
                microbreakRemainingSeconds: 0,
                sessionEnded: false
            ),
            alertCounts: [.mild: 6, .moderate: 3, .strong: 1],
            settingsStore: settingsStore,
            historyStore: historyStore
        )
    }

    private static func makeRecentMinutes() -> [MinuteBlinkRecord] {
        let calendar = Calendar.current
        let minute = calendar.dateInterval(of: .minute, for: Date())?.start ?? Date()
        let rates = [16, 17, 18, 18, 17, 19, 18, 16, 17, 18, 19, 17, 18, 17, 20, 19, 18, 17, 18, 19, 17, 18, 19, 17, 18, 20, 18, 17, 18, 18]
        return rates.enumerated().map { index, rate in
            MinuteBlinkRecord(
                bucketStart: calendar.date(byAdding: .minute, value: index - rates.count + 1, to: minute) ?? minute,
                blinks: rate,
                validSeconds: 60,
                sessionID: "readme-demo"
            )
        }
    }

    private static func seedHistory(_ store: HistoryStore, recent: [MinuteBlinkRecord]) {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        for dayOffset in -29 ... -1 {
            guard let day = calendar.date(byAdding: .day, value: dayOffset, to: today) else { continue }
            for sample in 0 ..< 8 {
                let minute = calendar.date(byAdding: .minute, value: 9 * 60 + sample * 47, to: day) ?? day
                let rate = 15 + ((abs(dayOffset) + sample * 3) % 7)
                try? store.appendMinute(
                    MinuteBlinkRecord(
                        bucketStart: minute,
                        blinks: rate,
                        validSeconds: 60,
                        sessionID: "readme-demo-history"
                    )
                )
            }
        }
        recent.forEach { try? store.appendMinute($0) }
    }

    private static func value(after flag: String, in arguments: [String]) -> String? {
        guard let index = arguments.firstIndex(of: flag), arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1]
    }
}
