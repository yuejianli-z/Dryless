import Foundation

public struct MicrobreakSnapshot: Equatable {
    public var isActive: Bool
    public var started: Bool
    public var ended: Bool
    public var presenceSeconds: TimeInterval
    public var remainingSeconds: TimeInterval
}

public struct MicrobreakTracker {
    public static let triggerSeconds: TimeInterval = 20 * 60
    public static let promptSeconds: TimeInterval = 30
    public static let absenceEndSeconds: TimeInterval = 20
    public static let trackingGraceSeconds: TimeInterval = 5

    private var lastTime: TimeInterval?
    private var previousFace = false
    private var presence: TimeInterval = 0
    private var absentSince: TimeInterval?
    private var promptUntil: TimeInterval?

    public init() {}

    public mutating func update(facePresent: Bool, at now: TimeInterval, paused: Bool) -> MicrobreakSnapshot {
        let wasActive = promptUntil != nil
        var delta = lastTime.map { max(0, now - $0) } ?? 0

        if paused {
            resetState()
            delta = 0
        } else if delta > Self.trackingGraceSeconds, promptUntil == nil {
            presence = 0
            absentSince = nil
            delta = 0
        }

        if facePresent {
            if let absentSince, now - absentSince > Self.trackingGraceSeconds {
                presence = 0
            }
            absentSince = nil
            if previousFace, promptUntil == nil, !paused {
                presence += delta
            }
        } else {
            if absentSince == nil {
                absentSince = previousFace ? lastTime : now
            }
            let absence = now - (absentSince ?? now)
            if absence > Self.trackingGraceSeconds {
                presence = 0
            }
            if absence >= Self.absenceEndSeconds {
                promptUntil = nil
            }
        }

        if let promptUntil, now >= promptUntil {
            self.promptUntil = nil
        }

        let ended = wasActive && promptUntil == nil
        if ended {
            presence = 0
        }

        var started = false
        if !paused, facePresent, !ended, promptUntil == nil, presence >= Self.triggerSeconds {
            promptUntil = now + Self.promptSeconds
            presence = 0
            started = true
        }

        lastTime = now
        previousFace = facePresent && !paused

        return MicrobreakSnapshot(
            isActive: promptUntil != nil,
            started: started,
            ended: ended,
            presenceSeconds: presence,
            remainingSeconds: max(0, (promptUntil ?? now) - now)
        )
    }

    public mutating func reset(at now: TimeInterval? = nil) {
        resetState()
        lastTime = now
    }

    private mutating func resetState() {
        presence = 0
        promptUntil = nil
        absentSince = nil
        previousFace = false
    }
}
