import DrylessCore
import SwiftUI

extension PrimaryAppState {
    func title(language: AppLanguage) -> String {
        switch self {
        case .cameraOff: return L10n.text("camera_off", language)
        case .starting: return L10n.text("camera_starting", language)
        case .stopping: return L10n.text("camera_stopping", language)
        case .suspended: return L10n.text("camera_suspended", language)
        case .permissionDenied: return L10n.text("camera_denied", language)
        case .cameraUnavailable: return L10n.text("camera_missing", language)
        case .cameraError: return L10n.text("camera_failed", language)
        case .paused: return L10n.text("alerts_paused", language)
        case .microbreak: return L10n.text("microbreak_active", language)
        case .noFace: return L10n.text("face_none", language)
        case .calibrating: return L10n.text("calibrating", language)
        case .alert(let level): return level.description(for: language)
        case .monitoring: return L10n.text("monitoring", language)
        }
    }

    var systemImage: String {
        switch self {
        case .cameraOff: return "video.slash"
        case .starting: return "ellipsis.circle"
        case .stopping: return "stop.circle"
        case .suspended: return "moon.zzz"
        case .permissionDenied: return "hand.raised"
        case .cameraUnavailable, .cameraError: return "exclamationmark.triangle"
        case .paused: return "pause.circle"
        case .microbreak: return "figure.walk"
        case .noFace: return "person.crop.circle.badge.questionmark"
        case .calibrating: return "viewfinder"
        case .alert(let level): return level.systemImage
        case .monitoring: return "checkmark.circle"
        }
    }

    var tint: Color {
        switch self {
        case .monitoring: return .green
        case .alert, .microbreak: return .orange
        case .permissionDenied, .cameraUnavailable, .cameraError: return .red
        case .starting, .stopping, .calibrating: return BrandPalette.sage
        default: return .secondary
        }
    }
}
