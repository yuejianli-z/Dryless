import AVFoundation
import DrylessCore
import Foundation

@MainActor
final class AlertService: ObservableObject {
    @Published private(set) var isPreviewing = false
    @Published private(set) var isPreviewingSequence = false
    @Published private(set) var previewStage: Int?
    @Published private(set) var lastError: String?

    private enum Owner: Int {
        case blink = 1
        case preview = 2
        case microbreak = 3
    }

    private var owner: Owner?
    private var player: AVAudioPlayer?
    private var sequenceTask: Task<Void, Never>?
    private var playbackToken = UUID()

    @discardableResult
    func playBlink(level: AlertLevel, settings: AppSettings) -> Bool {
        guard settings.soundEnabled, let url = soundURL(theme: settings.soundTheme, level: level.rawValue) else {
            return false
        }
        return start(urls: [url], owner: .blink, gap: 0)
    }

    @discardableResult
    func playMicrobreak(settings: AppSettings) -> Bool {
        guard settings.soundEnabled, let url = resourceURL("started", extension: "wav", subdirectory: "Sounds/microbreak") else {
            return false
        }
        return start(urls: [url], owner: .microbreak, gap: 0)
    }

    func preview(theme: SoundTheme, allStages: Bool) {
        let levels = allStages ? [0, 1, 2] : [0]
        let urls = levels.compactMap { soundURL(theme: theme, level: $0) }
        guard urls.count == levels.count else {
            lastError = "One or more bundled reminder sounds could not be found."
            return
        }
        if start(urls: urls, owner: .preview, gap: allStages ? 0.8 : 0) {
            isPreviewingSequence = allStages
        }
    }

    func stopPreview() {
        guard owner == .preview else { return }
        cancelAll()
    }

    func cancelAutomatic() {
        guard owner == .blink || owner == .microbreak else { return }
        cancelAll()
    }

    func cancelAll() {
        sequenceTask?.cancel()
        sequenceTask = nil
        player?.stop()
        player = nil
        owner = nil
        isPreviewing = false
        isPreviewingSequence = false
        previewStage = nil
        playbackToken = UUID()
    }

    private func start(urls: [URL], owner newOwner: Owner, gap: TimeInterval) -> Bool {
        if let owner, owner.rawValue > newOwner.rawValue {
            return false
        }
        cancelAll()

        let token = UUID()
        playbackToken = token
        owner = newOwner
        isPreviewing = newOwner == .preview
        isPreviewingSequence = false
        lastError = nil
        sequenceTask = Task { [weak self] in
            guard let self else { return }
            for (index, url) in urls.enumerated() {
                guard !Task.isCancelled, self.playbackToken == token else { return }
                do {
                    let player = try AVAudioPlayer(contentsOf: url)
                    player.prepareToPlay()
                    self.player = player
                    self.previewStage = newOwner == .preview ? index : nil
                    guard player.play() else {
                        throw CocoaError(.fileReadUnknown)
                    }
                    let nanoseconds = UInt64(max(0.05, player.duration + 0.03) * 1_000_000_000)
                    try await Task.sleep(nanoseconds: nanoseconds)
                    if index < urls.count - 1, gap > 0 {
                        try await Task.sleep(nanoseconds: UInt64(gap * 1_000_000_000))
                    }
                } catch is CancellationError {
                    return
                } catch {
                    self.lastError = error.localizedDescription
                    break
                }
            }
            guard self.playbackToken == token else { return }
            self.sequenceTask = nil
            self.player = nil
            self.owner = nil
            self.isPreviewing = false
            self.isPreviewingSequence = false
            self.previewStage = nil
        }
        return true
    }

    private func soundURL(theme: SoundTheme, level: Int) -> URL? {
        resourceURL("alert\(max(0, min(2, level)))", extension: "wav", subdirectory: "Sounds/\(theme.rawValue)")
    }

    private func resourceURL(_ name: String, extension fileExtension: String, subdirectory: String) -> URL? {
        AppResources.bundle.url(forResource: name, withExtension: fileExtension, subdirectory: subdirectory)
    }
}
