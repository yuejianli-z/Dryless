import DrylessCore
import SwiftUI

struct MonitorView: View {
    @ObservedObject var controller: AppController

    private let gap: CGFloat = 16

    var body: some View {
        GeometryReader { proxy in
            if proxy.size.width >= 600 {
                HStack(alignment: .top, spacing: gap) {
                    cameraPanel
                        .frame(width: min(480, max(290, (proxy.size.width - gap) * 0.54)))
                    statusPanel
                }
                .padding(16)
                .frame(maxHeight: .infinity)
            } else {
                HiddenScrollerScrollView {
                    VStack(spacing: gap) {
                        cameraPanel.frame(height: 520)
                        statusPanel.frame(minHeight: 560)
                    }
                    .padding(16)
                }
            }
        }
    }

    private var cameraPanel: some View {
        AppCard(spacing: 12, fillsHeight: true) {
            SectionHeader(
                title: copy(zh: "实时监控", en: "Live monitor"),
                subtitle: cameraSubtitle
            )

            CameraPreviewView(
                image: controller.camera.previewImage,
                state: controller.camera.state,
                primaryState: controller.primaryState,
                language: controller.language,
                previewVisible: controller.settingsStore.settings.previewVisible,
                aspectRatio: cameraAspectRatio,
                landmarks: controller.camera.eyeLandmarks,
                onCameraAction: controller.toggleCamera
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            HStack(spacing: 0) {
                CompactMetric(
                    title: L10n.text("session_blinks", controller.language),
                    value: "\(controller.snapshot.totalBlinks)",
                    systemImage: nil,
                    brandEyeState: controller.menuBarEyeState,
                    tint: BrandPalette.sage
                )
                metricDivider
                CompactMetric(
                    title: copy(zh: "当前频率", en: "Current rate"),
                    value: controller.snapshot.blinkRate.map { "\(Formatters.rate($0))/min" } ?? "-",
                    systemImage: "speedometer",
                    tint: controller.snapshot.blinkRate == nil ? .secondary : .green
                )
                metricDivider
                CompactMetric(
                    title: copy(zh: "距上次眨眼", en: "Since last blink"),
                    value: controller.snapshot.noBlinkSeconds.map(Formatters.seconds) ?? "-",
                    systemImage: "timer",
                    tint: controller.snapshot.alertLevel == nil ? .primary : .orange
                )
                metricDivider
                CompactMetric(
                    title: copy(zh: "本次使用", en: "Session time"),
                    value: Formatters.duration(controller.snapshot.sessionDuration),
                    systemImage: "clock",
                    tint: BrandPalette.sage
                )
            }
            .frame(height: 58)

            Divider()

            HStack(alignment: .firstTextBaseline) {
                Text(copy(zh: "近 30 分钟", en: "Last 30 minutes"))
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(copy(zh: "每分钟眨眼频率 · 参考 15–20", en: "Blink rate · reference 15–20/min"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            MinuteStripChart(
                records: recentThirtyMinutes,
                language: controller.language,
                showsValidityDetail: false,
                emptyText: copy(zh: "记录满 1 分钟后显示", en: "Appears after one recorded minute")
            )
            .frame(height: 82)
        }
    }

    private var statusPanel: some View {
        AppCard(spacing: 13, fillsHeight: true) {
            HStack(spacing: 18) {
                RateRingView(
                    rate: controller.snapshot.blinkRate,
                    alertLevel: controller.snapshot.alertLevel,
                    size: 132
                )

                VStack(alignment: .leading, spacing: 8) {
                    Label(
                        controller.primaryState.title(language: controller.language),
                        systemImage: controller.primaryState.systemImage
                    )
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(controller.primaryState.tint)

                    Text(statusDetail)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(copy(zh: "参考范围 15–20 次/分钟", en: "Reference range 15–20 blinks/min"))
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxWidth: .infinity)

            actionBanner

            VStack(alignment: .leading, spacing: 8) {
                Text(copy(zh: "检测信号", en: "Detection signals"))
                    .font(.headline)

                SignalRow(
                    icon: controller.snapshot.faceDetected ? "person.crop.circle.fill" : "person.crop.circle.badge.questionmark",
                    title: copy(zh: "人脸", en: "Face"),
                    value: controller.snapshot.faceDetected ? L10n.text("face_locked", controller.language) : L10n.text("face_none", controller.language)
                )
                SignalRow(
                    icon: nil,
                    brandEyeState: controller.menuBarEyeState,
                    title: copy(zh: "眼部开合", en: "Eye openness"),
                    value: controller.snapshot.measurementValid
                        ? (controller.snapshot.eyeOpen ? copy(zh: "睁开", en: "Open") : copy(zh: "闭合", en: "Closed"))
                        : "-"
                )
            }

            VStack(spacing: 10) {
                ProgressLine(
                    icon: "bell",
                    title: copy(zh: "下次眨眼提醒", en: "Next blink reminder"),
                    value: reminderProgress,
                    detail: reminderDetail,
                    tint: .orange,
                    markers: reminderMarkers
                )
                ProgressLine(
                    icon: "figure.walk",
                    title: copy(zh: "20 分钟微休息", en: "20-minute microbreak"),
                    value: min(1, controller.snapshot.microbreakPresenceSeconds / (20 * 60)),
                    detail: microbreakDetail,
                    tint: BrandPalette.sage
                )
            }

            EyeCareTipCarousel(
                language: controller.language,
                pausesAutomatically: controller.snapshot.alertLevel != nil || controller.snapshot.microbreakActive
            )
            .frame(maxHeight: .infinity, alignment: .bottom)
        }
    }

    private var actionBanner: some View {
        HStack(spacing: 12) {
            Image(systemName: actionIcon)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(actionTint)
                .frame(width: 32, height: 32)
                .background(actionTint.opacity(0.12), in: Circle())

            VStack(alignment: .leading, spacing: 2) {
                Text(actionTitle)
                    .font(.subheadline.weight(.semibold))
                Text(actionDetail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer(minLength: 8)

            if controller.camera.state.canStart {
                Button {
                    controller.startCamera()
                } label: {
                    Image(systemName: "video.fill")
                        .frame(width: 18, height: 18)
                }
                .buttonStyle(.bordered)
                .help(L10n.text("start_camera", controller.language))
                .accessibilityLabel(L10n.text("start_camera", controller.language))
            }
        }
        .padding(12)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private var statusDetail: String {
        switch controller.primaryState {
        case .monitoring:
            return copy(zh: "检测稳定，继续自然眨眼。", en: "Tracking is stable. Keep blinking naturally.")
        case .alert:
            return copy(zh: "眨几次眼即可重置提醒进度。", en: "Blink a few times to reset the reminder.")
        case .paused:
            return copy(zh: "仍在检测和记录，只暂停自动提醒。", en: "Detection and history continue; automatic reminders are paused.")
        case .microbreak:
            return copy(zh: "看向远处，休息约 20 秒。", en: "Look into the distance for about 20 seconds.")
        case .calibrating:
            return copy(zh: "请自然睁眼片刻，以建立基线。", en: "Keep your eyes naturally open while the baseline settles.")
        case .noFace:
            return copy(zh: "请回到画面中央并保持自然坐姿。", en: "Return to the center of the frame in a natural posture.")
        default:
            return controller.camera.state.label(language: controller.language)
        }
    }

    private var actionTitle: String {
        switch controller.primaryState {
        case .cameraOff: return copy(zh: "准备开始时开启摄像头", en: "Start the camera when you are ready")
        case .starting: return copy(zh: "正在连接摄像头", en: "Connecting to the camera")
        case .stopping: return copy(zh: "正在释放摄像头", en: "Releasing the camera")
        case .permissionDenied: return copy(zh: "允许摄像头访问", en: "Allow camera access")
        case .cameraUnavailable, .cameraError: return copy(zh: "检查摄像头连接", en: "Check the camera connection")
        case .paused: return copy(zh: "提醒暂时安静", en: "Reminders are quiet")
        case .microbreak: return copy(zh: "看远处 20 秒", en: "Look away for 20 seconds")
        case .noFace: return copy(zh: "回到取景区域", en: "Return to the frame")
        case .calibrating: return copy(zh: "保持自然睁眼", en: "Keep your eyes naturally open")
        case .alert: return copy(zh: "现在轻眨几次", en: "Blink gently now")
        default: return copy(zh: "保持自然眨眼", en: "Keep blinking naturally")
        }
    }

    private var actionDetail: String {
        switch controller.primaryState {
        case .permissionDenied:
            return copy(zh: "在系统设置的隐私与安全性中允许 Dryless。", en: "Allow Dryless in System Settings, Privacy & Security.")
        case .cameraUnavailable, .cameraError:
            return copy(zh: "连接摄像头后可再次尝试。", en: "Reconnect a camera, then try again.")
        case .paused:
            return copy(zh: "眨眼计数和本地历史仍会继续。", en: "Blink counting and local history continue.")
        default:
            return statusDetail
        }
    }

    private var actionIcon: String { controller.primaryState.systemImage }
    private var actionTint: Color { controller.primaryState.tint }

    private var recentThirtyMinutes: [MinuteBlinkRecord] {
        Array(controller.snapshot.recentMinutes.suffix(30))
    }

    private var cameraAspectRatio: CGFloat {
        let size = controller.camera.actualResolution ?? controller.camera.previewImage?.size ?? configuredCameraSize
        guard size.width > 0, size.height > 0 else { return 4.0 / 3.0 }
        return size.width / size.height
    }

    private var configuredCameraSize: CGSize {
        let settings = controller.settingsStore.settings
        return CGSize(width: settings.cameraWidth, height: settings.cameraHeight)
    }

    private var resolutionText: String {
        guard let size = controller.camera.actualResolution else {
            return controller.camera.state == .running ? "-" : controller.camera.state.label(language: controller.language)
        }
        return "\(Int(size.width)) × \(Int(size.height))"
    }

    private var cameraSubtitle: String {
        let state = controller.camera.state.label(language: controller.language)
        guard controller.camera.actualResolution != nil else { return state }
        return "\(state) · \(resolutionText)"
    }

    private var metricDivider: some View {
        Divider()
            .padding(.vertical, 8)
    }

    private var reminderProgress: Double {
        guard let elapsed = controller.snapshot.noBlinkSeconds else { return 0 }
        return min(1, elapsed / reminderFinalThreshold)
    }

    private var reminderDetail: String {
        if controller.isPaused { return copy(zh: "已暂停", en: "Paused") }
        guard let elapsed = controller.snapshot.noBlinkSeconds else { return "-" }
        let delay = Double(controller.settingsStore.settings.alertDelaySeconds)
        let interval = Double(max(1, controller.settingsStore.settings.escalationIntervalSeconds))
        let remaining: Double
        if elapsed < delay {
            remaining = delay - elapsed
        } else {
            let roundProgress = (elapsed - delay).truncatingRemainder(dividingBy: interval)
            remaining = roundProgress == 0 ? interval : interval - roundProgress
        }
        return Formatters.seconds(remaining)
    }

    private var reminderFinalThreshold: Double {
        let settings = controller.settingsStore.settings
        return Double(settings.alertDelaySeconds + settings.escalationIntervalSeconds * 2)
    }

    private var reminderMarkers: [Double] {
        let settings = controller.settingsStore.settings
        let final = reminderFinalThreshold
        return [
            Double(settings.alertDelaySeconds) / final,
            Double(settings.alertDelaySeconds + settings.escalationIntervalSeconds) / final,
            1
        ]
    }

    private var microbreakDetail: String {
        if controller.snapshot.microbreakActive {
            return Formatters.seconds(controller.snapshot.microbreakRemainingSeconds)
        }
        return Formatters.duration(controller.snapshot.microbreakPresenceSeconds)
    }

    private func copy(zh: String, en: String) -> String {
        controller.language == .zh ? zh : en
    }
}

private struct CompactMetric: View {
    var title: String
    var value: String
    var systemImage: String?
    var brandEyeState: BrandEyeState? = nil
    var tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 6) {
                if let brandEyeState {
                    BrandEyeImage(state: brandEyeState, size: 14, tint: BrandPalette.sage)
                } else if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            .font(.caption2)
            .foregroundStyle(.secondary)

            Text(value)
                .font(.system(size: 18, weight: .semibold, design: .rounded))
                .foregroundStyle(tint)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .contentTransition(.numericText())
        }
        .padding(.horizontal, 10)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }
}

private struct SignalRow: View {
    var icon: String?
    var brandEyeState: BrandEyeState? = nil
    var title: String
    var value: String

    var body: some View {
        HStack(spacing: 10) {
            Group {
                if let brandEyeState {
                    BrandEyeImage(state: brandEyeState, size: 18, tint: BrandPalette.sage)
                } else if let icon {
                    Image(systemName: icon)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 20)
            Text(title)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Spacer(minLength: 8)
            Text(value)
                .font(.subheadline.weight(.medium))
                .lineLimit(1)
                .minimumScaleFactor(0.75)
        }
        .padding(.horizontal, 11)
        .frame(height: 36)
        .background(Color.secondary.opacity(0.055), in: RoundedRectangle(cornerRadius: 7, style: .continuous))
    }
}

private struct ProgressLine: View {
    var icon: String
    var title: String
    var value: Double
    var detail: String
    var tint: Color
    var markers: [Double] = []

    var body: some View {
        VStack(spacing: 6) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .foregroundStyle(tint)
                    .frame(width: 18)
                Text(title)
                    .font(.caption.weight(.medium))
                Spacer()
                Text(detail)
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.secondary.opacity(0.13))
                    if value > 0.001 {
                        Capsule()
                            .fill(tint)
                            .frame(width: max(3, proxy.size.width * min(1, max(0, value))))
                    }
                    ForEach(markers, id: \.self) { marker in
                        Rectangle()
                            .fill(Color.secondary.opacity(0.45))
                            .frame(width: 1, height: 8)
                            .position(x: proxy.size.width * min(1, max(0, marker)), y: 4)
                    }
                }
            }
            .frame(height: 8)
        }
    }
}
