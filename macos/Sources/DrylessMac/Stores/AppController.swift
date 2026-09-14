import AppKit
import Combine
import DrylessCore
import Foundation
import UniformTypeIdentifiers

@MainActor
final class AppController: ObservableObject {
    @Published var snapshot: SessionSnapshot = .initial
    @Published var isPaused = false
    @Published var alertCounts: [AlertLevel: Int] = Dictionary(
        uniqueKeysWithValues: AlertLevel.allCases.map { ($0, 0) }
    )
    @Published var historyError: String?
    @Published var exportResult: String?

    let settingsStore: SettingsStore
    let historyStore: HistoryStore
    let camera: CameraService
    let readmeDemo: ReadmeDemoFixture?

    private let alerts = AlertService()
    private var engine: BlinkDetectionEngine
    private var reminderScheduler = ReminderScheduler()
    private var microbreakTracker = MicrobreakTracker()
    private var liveWindow: LiveBlinkWindow?
    private var sessionStartDate = Date()
    private var sessionStartUptime = ProcessInfo.processInfo.systemUptime
    private var reminderAnchorUptime = ProcessInfo.processInfo.systemUptime
    private var previousCameraState: CameraState = .off
    private var hasStarted = false
    private var cancellables: Set<AnyCancellable> = []

    init(
        settingsStore: SettingsStore = SettingsStore(),
        historyStore: HistoryStore = HistoryStore(),
        camera: CameraService = CameraService(),
        readmeDemo: ReadmeDemoFixture? = nil
    ) {
        self.settingsStore = settingsStore
        self.historyStore = historyStore
        self.camera = camera
        self.readmeDemo = readmeDemo
        self.engine = BlinkDetectionEngine(settings: settingsStore.settings, now: sessionStartDate)

        camera.onMeasurement = { [weak self] measurement in
            DispatchQueue.main.async {
                self?.handle(measurement)
            }
        }

        settingsStore.$settings
            .sink { [weak self] settings in
                guard let self else { return }
                self.objectWillChange.send()
                self.engine.updateSettings(settings)
                self.camera.updateSettings(settings)
                if !settings.soundEnabled {
                    self.alerts.cancelAutomatic()
                }
            }
            .store(in: &cancellables)

        settingsStore.$loadError
            .sink { [weak self] error in
                self?.historyError = error
            }
            .store(in: &cancellables)

        camera.$state
            .dropFirst()
            .sink { [weak self] state in
                self?.cameraStateDidChange(state)
            }
            .store(in: &cancellables)

        camera.objectWillChange
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)

        alerts.objectWillChange
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)
    }

    var language: AppLanguage { settingsStore.settings.language }
    var isPreviewingSound: Bool { alerts.isPreviewing }
    var isPreviewingSoundSequence: Bool { alerts.isPreviewingSequence }
    var previewStage: Int? { alerts.previewStage }
    var audioError: String? { alerts.lastError }

    var primaryState: PrimaryAppState {
        switch camera.state {
        case .off: return .cameraOff
        case .starting: return .starting
        case .stopping: return .stopping
        case .suspended: return .suspended
        case .denied: return .permissionDenied
        case .unavailable: return .cameraUnavailable
        case .failed: return .cameraError
        case .running: break
        }
        if isPaused { return .paused }
        if snapshot.microbreakActive { return .microbreak }
        if !snapshot.faceDetected { return .noFace }
        if !snapshot.measurementValid { return .calibrating }
        if let level = snapshot.alertLevel { return .alert(level) }
        return .monitoring
    }

    var menuBarEyeState: BrandEyeState {
        switch camera.state {
        case .running: return .open
        default: return .closed
        }
    }

    var cameraIsOnOrStarting: Bool {
        camera.state == .running || camera.state == .starting
    }

    func start() {
        guard !hasStarted else { return }
        hasStarted = true
        observeSystemLifecycle()
        if let readmeDemo {
            snapshot = readmeDemo.snapshot
            alertCounts = readmeDemo.alertCounts
            camera.startReadmeDemo(settings: settingsStore.settings, image: readmeDemo.image)
            return
        }
        if settingsStore.settings.cameraEnabledOnLaunch {
            camera.start(settings: settingsStore.settings)
        }
    }

    func toggleCamera() {
        switch camera.state {
        case .running, .starting:
            stopCamera()
        case .stopping:
            break
        default:
            startCamera()
        }
    }

    func startCamera() {
        guard camera.state.canStart else { return }
        _ = updateSettings { $0.cameraEnabledOnLaunch = true }
        camera.start(settings: settingsStore.settings)
    }

    func stopCamera() {
        _ = updateSettings { $0.cameraEnabledOnLaunch = false }
        alerts.cancelAll()
        camera.stop()
        endSession()
    }

    func togglePause() {
        guard camera.state == .running else { return }
        isPaused.toggle()
        let now = ProcessInfo.processInfo.systemUptime
        reminderScheduler.reset()
        reminderAnchorUptime = now
        microbreakTracker.reset(at: now)
        engine.resetReminderClock()
        alerts.cancelAll()
        snapshot.alertLevel = nil
        snapshot.microbreakActive = false
        snapshot.microbreakPresenceSeconds = 0
        snapshot.microbreakRemainingSeconds = 0
    }

    func toggleSound() {
        let enable = !settingsStore.settings.soundEnabled
        _ = updateSettings { $0.soundEnabled = enable }
        if !enable { alerts.cancelAutomatic() }
    }

    func togglePreview() {
        _ = updateSettings { $0.previewVisible.toggle() }
    }

    @discardableResult
    func updateSettings(_ update: (inout AppSettings) -> Void) -> Bool {
        do {
            let previous = settingsStore.settings
            try settingsStore.mutate(update)
            let current = settingsStore.settings
            if previous.alertDelaySeconds != current.alertDelaySeconds ||
                previous.escalationIntervalSeconds != current.escalationIntervalSeconds {
                reminderScheduler.reset()
                reminderAnchorUptime = ProcessInfo.processInfo.systemUptime
                alerts.cancelAutomatic()
            }
            if (previous.cameraWidth != current.cameraWidth || previous.cameraHeight != current.cameraHeight),
                camera.state == .running {
                camera.restart(settings: current)
            }
            return true
        } catch {
            historyError = error.localizedDescription
            NSSound.beep()
            return false
        }
    }

    func selectSoundTheme(_ theme: SoundTheme) {
        _ = updateSettings { $0.soundTheme = theme }
        alerts.preview(theme: theme, allStages: false)
    }

    func previewAllAlertStages() {
        if alerts.isPreviewingSequence {
            alerts.stopPreview()
        } else {
            alerts.preview(theme: settingsStore.settings.soundTheme, allStages: true)
        }
    }

    func stopSoundPreview() {
        alerts.stopPreview()
    }

    func historyBounds() -> ClosedRange<Date>? {
        do {
            historyError = nil
            return try historyStore.dateBounds()
        } catch {
            historyError = error.localizedDescription
            return nil
        }
    }

    func historyReport(from start: Date, through end: Date, grain: HistoryGrain) -> HistoryReport? {
        do {
            historyError = nil
            return try historyStore.report(from: start, through: end, grain: grain)
        } catch {
            historyError = error.localizedDescription
            return nil
        }
    }

    func exportHistory(from start: Date, through end: Date) {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.commaSeparatedText]
        panel.canCreateDirectories = true
        panel.nameFieldStringValue = "Dryless-history.csv"
        guard panel.runModal() == .OK, let url = panel.url else {
            exportResult = nil
            return
        }

        do {
            let csv = try historyStore.csv(from: start, through: end)
            try csv.write(to: url, atomically: true, encoding: .utf8)
            exportResult = language == .zh ? "已导出到 \(url.lastPathComponent)" : "Exported to \(url.lastPathComponent)"
        } catch {
            exportResult = error.localizedDescription
            NSSound.beep()
        }
    }

    func activateMainWindow() {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        let window = NSApp.windows.first(where: { $0.canBecomeMain }) ?? NSApp.windows.first
        window?.makeKeyAndOrderFront(nil)
    }

    func shutdown() {
        alerts.cancelAll()
        camera.stop()
    }

    private func beginSession() {
        sessionStartDate = Date()
        sessionStartUptime = ProcessInfo.processInfo.systemUptime
        reminderAnchorUptime = sessionStartUptime
        let sessionID = UUID().uuidString
        engine.resetSession(at: sessionStartDate)
        reminderScheduler.reset()
        microbreakTracker.reset(at: sessionStartUptime)
        liveWindow = LiveBlinkWindow(startUptime: sessionStartUptime, startDate: sessionStartDate, sessionID: sessionID)
        alertCounts = Dictionary(uniqueKeysWithValues: AlertLevel.allCases.map { ($0, 0) })
        snapshot = .initial
    }

    private func endSession() {
        reminderScheduler.reset()
        microbreakTracker.reset()
        liveWindow = nil
        snapshot.faceDetected = false
        snapshot.measurementValid = false
        snapshot.eyeRatio = nil
        snapshot.blinkRate = nil
        snapshot.noBlinkSeconds = nil
        snapshot.alertLevel = nil
        snapshot.microbreakActive = false
        snapshot.microbreakPresenceSeconds = 0
        snapshot.microbreakRemainingSeconds = 0
        snapshot.sessionEnded = snapshot.sessionDuration > 0
    }

    private func handle(_ measurement: EyeMeasurement) {
        guard camera.state == .running, var liveWindow else { return }
        let nowDate = Date()
        let nowUptime = ProcessInfo.processInfo.systemUptime
        let wasValid = snapshot.measurementValid
        let result = engine.process(measurement, at: nowDate)

        if result.blinked || result.measurementValid != wasValid {
            reminderAnchorUptime = nowUptime
            reminderScheduler.reset()
            alerts.cancelAutomatic()
        }

        let live: LiveBlinkSnapshot
        do {
            live = try liveWindow.sample(at: nowUptime, valid: result.measurementValid, blinked: result.blinked)
            self.liveWindow = liveWindow
            for record in live.completedMinutes {
                try historyStore.appendMinute(record)
            }
        } catch {
            historyError = error.localizedDescription
            self.liveWindow = LiveBlinkWindow(startUptime: nowUptime, startDate: nowDate, sessionID: UUID().uuidString)
            return
        }

        var recent = snapshot.recentMinutes
        recent.append(contentsOf: live.completedMinutes)
        if recent.count > 60 { recent.removeFirst(recent.count - 60) }

        let microbreak = microbreakTracker.update(
            facePresent: result.measurementValid,
            at: nowUptime,
            paused: isPaused
        )
        if microbreak.started {
            reminderScheduler.reset()
            alerts.cancelAll()
            _ = alerts.playMicrobreak(settings: settingsStore.settings)
        }
        if microbreak.ended {
            reminderAnchorUptime = nowUptime
            reminderScheduler.reset()
        }

        if isPaused, result.measurementValid {
            reminderAnchorUptime = nowUptime
        }

        let reminderElapsed = result.measurementValid ? max(0, nowUptime - reminderAnchorUptime) : 0
        let activeAlert = result.measurementValid && !isPaused && !microbreak.isActive
            ? AlertLevel.level(forNoBlinkSeconds: reminderElapsed, settings: settingsStore.settings)
            : nil
        if let event = reminderScheduler.event(
            elapsed: reminderElapsed,
            trackingValid: result.measurementValid,
            paused: isPaused,
            microbreakActive: microbreak.isActive,
            settings: settingsStore.settings
        ) {
            alertCounts[event, default: 0] += 1
            _ = alerts.playBlink(level: event, settings: settingsStore.settings)
        }

        snapshot = SessionSnapshot(
            faceDetected: result.faceDetected,
            measurementValid: result.measurementValid,
            eyeOpen: result.eyeOpen,
            eyeRatio: result.ratio,
            blinkRate: result.measurementValid ? live.rate : nil,
            rollingValidSeconds: live.validSeconds,
            rollingBlinks: live.blinks,
            noBlinkSeconds: result.measurementValid ? reminderElapsed : nil,
            totalBlinks: result.totalBlinks,
            alertLevel: activeAlert,
            sessionDuration: max(0, nowUptime - sessionStartUptime),
            recentMinutes: recent,
            microbreakActive: microbreak.isActive,
            microbreakPresenceSeconds: microbreak.presenceSeconds,
            microbreakRemainingSeconds: microbreak.remainingSeconds,
            sessionEnded: false
        )
    }

    private func cameraStateDidChange(_ state: CameraState) {
        defer { previousCameraState = state }
        if state == .running, previousCameraState != .running {
            beginSession()
        } else if state != .running, previousCameraState == .running {
            alerts.cancelAll()
            endSession()
        }
    }

    private func observeSystemLifecycle() {
        let workspaceCenter = NSWorkspace.shared.notificationCenter
        workspaceCenter.publisher(for: NSWorkspace.willSleepNotification)
            .merge(with: workspaceCenter.publisher(for: NSWorkspace.sessionDidResignActiveNotification))
            .sink { [weak self] _ in
                guard let self, self.settingsStore.settings.cameraEnabledOnLaunch else { return }
                self.alerts.cancelAll()
                self.camera.suspend()
                self.endSession()
            }
            .store(in: &cancellables)

        workspaceCenter.publisher(for: NSWorkspace.didWakeNotification)
            .merge(with: workspaceCenter.publisher(for: NSWorkspace.sessionDidBecomeActiveNotification))
            .sink { [weak self] _ in
                guard let self, self.settingsStore.settings.cameraEnabledOnLaunch else { return }
                self.camera.start(settings: self.settingsStore.settings)
            }
            .store(in: &cancellables)

        NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)
            .sink { [weak self] _ in self?.shutdown() }
            .store(in: &cancellables)
    }
}
