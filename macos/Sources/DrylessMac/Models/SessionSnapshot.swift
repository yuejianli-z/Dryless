import DrylessCore
import Foundation

enum PrimaryAppState: Equatable {
    case cameraOff
    case starting
    case stopping
    case suspended
    case permissionDenied
    case cameraUnavailable
    case cameraError
    case paused
    case microbreak
    case noFace
    case calibrating
    case alert(AlertLevel)
    case monitoring
}

struct SessionSnapshot: Equatable {
    var faceDetected: Bool
    var measurementValid: Bool
    var eyeOpen: Bool
    var eyeRatio: Double?
    var blinkRate: Double?
    var rollingValidSeconds: TimeInterval
    var rollingBlinks: Int
    var noBlinkSeconds: TimeInterval?
    var totalBlinks: Int
    var alertLevel: AlertLevel?
    var sessionDuration: TimeInterval
    var recentMinutes: [MinuteBlinkRecord]
    var microbreakActive: Bool
    var microbreakPresenceSeconds: TimeInterval
    var microbreakRemainingSeconds: TimeInterval
    var sessionEnded: Bool

    static let initial = SessionSnapshot(
        faceDetected: false,
        measurementValid: false,
        eyeOpen: true,
        eyeRatio: nil,
        blinkRate: nil,
        rollingValidSeconds: 0,
        rollingBlinks: 0,
        noBlinkSeconds: nil,
        totalBlinks: 0,
        alertLevel: nil,
        sessionDuration: 0,
        recentMinutes: [],
        microbreakActive: false,
        microbreakPresenceSeconds: 0,
        microbreakRemainingSeconds: 0,
        sessionEnded: false
    )
}
