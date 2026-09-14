import DrylessCore
import SwiftUI

struct SettingsView: View {
    @ObservedObject var controller: AppController
    @ObservedObject private var settingsStore: SettingsStore

    init(controller: AppController) {
        self.controller = controller
        self._settingsStore = ObservedObject(wrappedValue: controller.settingsStore)
    }

    var body: some View {
        HiddenScrollerScrollView {
            VStack(alignment: .leading, spacing: 18) {
                reminderSettings
                soundSettings
                cameraSettings
                advancedSettings
                languageAndPrivacy

                if let error = settingsStore.loadError ?? controller.audioError {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal, 4)
                }
            }
            .padding(20)
            .frame(maxWidth: 840, alignment: .topLeading)
            .frame(maxWidth: .infinity, alignment: .top)
        }
        .onDisappear { controller.stopSoundPreview() }
    }

    private var reminderSettings: some View {
        SettingsGroup(
            title: L10n.text("settings_alert", controller.language),
            subtitle: copy(zh: "连续未眨眼时逐级提醒，共三个等级。", en: "Three reminder stages respond to time without a blink.")
        ) {
            SliderRow(
                title: L10n.text("first_alert", controller.language),
                value: intBinding(\.alertDelaySeconds),
                range: 5...60,
                step: 1,
                suffix: "s"
            )
            Divider()
            SliderRow(
                title: L10n.text("escalation", controller.language),
                value: intBinding(\.escalationIntervalSeconds),
                range: 3...30,
                step: 1,
                suffix: "s"
            )

            HStack(spacing: 8) {
                ForEach(AlertLevel.allCases) { level in
                    Label(level.description(for: controller.language), systemImage: level.systemImage)
                        .font(.caption)
                        .foregroundStyle(level == .strong ? .orange : .secondary)
                        .padding(.horizontal, 9)
                        .frame(height: 28)
                        .background(Color.secondary.opacity(0.06), in: RoundedRectangle(cornerRadius: 6, style: .continuous))
                }
            }
        }
    }

    private var soundSettings: some View {
        SettingsGroup(
            title: L10n.text("settings_sound", controller.language),
            subtitle: copy(zh: "选择主题时会试听第一档；完整试听按三档顺序播放。", en: "Choosing a theme previews stage one; full preview plays all three stages.")
        ) {
            Toggle(L10n.text("enable_sound", controller.language), isOn: boolBinding(\.soundEnabled))

            Divider()

            HStack(alignment: .center, spacing: 14) {
                Text(copy(zh: "声音主题", en: "Sound theme"))
                    .frame(width: 104, alignment: .leading)

                HStack(spacing: 6) {
                    ForEach(SoundTheme.allCases) { theme in
                        Button {
                            controller.selectSoundTheme(theme)
                        } label: {
                            Text(theme.displayName)
                                .font(.callout)
                                .padding(.horizontal, 10)
                                .frame(height: 26)
                                .foregroundStyle(theme == settingsStore.settings.soundTheme ? Color.white : Color.primary)
                                .background(
                                    theme == settingsStore.settings.soundTheme
                                        ? BrandPalette.sage
                                        : Color.secondary.opacity(0.12),
                                    in: RoundedRectangle(cornerRadius: 6, style: .continuous)
                                )
                        }
                        .buttonStyle(.plain)
                    }
                }

                Button {
                    controller.previewAllAlertStages()
                } label: {
                    Label(
                        controller.isPreviewingSoundSequence ? copy(zh: "停止", en: "Stop") : copy(zh: "试听三档", en: "Preview all"),
                        systemImage: controller.isPreviewingSoundSequence ? "stop.fill" : "play.fill"
                    )
                }
                .buttonStyle(.bordered)
            }

            if let stage = controller.previewStage {
                Text(copy(zh: "正在播放第 \(stage + 1) 档", en: "Playing stage \(stage + 1)"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var cameraSettings: some View {
        SettingsGroup(
            title: L10n.text("settings_camera", controller.language),
            subtitle: copy(zh: "隐藏预览不会暂停检测；关闭摄像头会释放设备。", en: "Hiding preview keeps detection running; camera off releases the device.")
        ) {
            Toggle(L10n.text("show_preview", controller.language), isOn: boolBinding(\.previewVisible))

            Divider()

            HStack(spacing: 14) {
                Text(copy(zh: "分辨率", en: "Resolution"))
                    .frame(width: 104, alignment: .leading)
                Picker(copy(zh: "分辨率", en: "Resolution"), selection: resolutionBinding) {
                    Text("640 x 480").tag("640x480")
                    Text("1280 x 720").tag("1280x720")
                    Text("1920 x 1080").tag("1920x1080")
                }
                .labelsHidden()
                .pickerStyle(.segmented)
            }

            HStack(spacing: 8) {
                Label(controller.camera.state.label(language: controller.language), systemImage: cameraStatusIcon)
                    .foregroundStyle(.secondary)
                Spacer()
                if let size = controller.camera.actualResolution {
                    Text(copy(zh: "实际 \(Int(size.width)) x \(Int(size.height))", en: "Actual \(Int(size.width)) x \(Int(size.height))"))
                        .foregroundStyle(.secondary)
                }
                Button(controller.cameraIsOnOrStarting ? L10n.text("stop_camera", controller.language) : L10n.text("start_camera", controller.language)) {
                    controller.toggleCamera()
                }
                .disabled(controller.camera.state == .stopping)
            }
            .font(.caption)
        }
    }

    private var advancedSettings: some View {
        SettingsGroup(
            title: L10n.text("settings_detection", controller.language),
            subtitle: copy(zh: "通常无需修改；调整阈值会重新校准。", en: "Usually best left unchanged; threshold edits recalibrate detection.")
        ) {
            DisclosureGroup(copy(zh: "显示高级检测参数", en: "Show advanced detection controls")) {
                VStack(spacing: 12) {
                    SliderRow(
                        title: L10n.text("blink_threshold", controller.language),
                        value: doubleBinding(\.blinkRatioThreshold),
                        range: 0.40...0.80,
                        step: 0.05,
                        suffix: ""
                    )
                }
                .padding(.top, 10)
            }
        }
    }

    private var languageAndPrivacy: some View {
        SettingsGroup(
            title: L10n.text("settings_language", controller.language),
            subtitle: copy(zh: "界面语言会立即应用。", en: "Interface language updates immediately.")
        ) {
            HStack(spacing: 14) {
                Text("Language")
                    .frame(width: 104, alignment: .leading)
                Picker("Language", selection: languageBinding) {
                    ForEach(AppLanguage.allCases) { language in
                        Text(language.displayName).tag(language)
                    }
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                .frame(maxWidth: 280)
                Spacer()
            }

            Divider()

            Label {
                Text(L10n.text("privacy_note", controller.language))
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            } icon: {
                Image(systemName: "hand.raised")
                    .foregroundStyle(.green)
            }
        }
    }

    private func intBinding(_ keyPath: WritableKeyPath<AppSettings, Int>) -> Binding<Double> {
        Binding {
            Double(settingsStore.settings[keyPath: keyPath])
        } set: { value in
            controller.updateSettings { $0[keyPath: keyPath] = Int(value.rounded()) }
        }
    }

    private func doubleBinding(_ keyPath: WritableKeyPath<AppSettings, Double>) -> Binding<Double> {
        Binding {
            settingsStore.settings[keyPath: keyPath]
        } set: { value in
            controller.updateSettings { $0[keyPath: keyPath] = value }
        }
    }

    private func boolBinding(_ keyPath: WritableKeyPath<AppSettings, Bool>) -> Binding<Bool> {
        Binding {
            settingsStore.settings[keyPath: keyPath]
        } set: { value in
            controller.updateSettings { $0[keyPath: keyPath] = value }
        }
    }

    private var languageBinding: Binding<AppLanguage> {
        Binding {
            settingsStore.settings.language
        } set: { value in
            controller.updateSettings { $0.language = value }
        }
    }

    private var resolutionBinding: Binding<String> {
        Binding {
            "\(settingsStore.settings.cameraWidth)x\(settingsStore.settings.cameraHeight)"
        } set: { value in
            let parts = value.split(separator: "x").compactMap { Int($0) }
            guard parts.count == 2 else { return }
            controller.updateSettings {
                $0.cameraWidth = parts[0]
                $0.cameraHeight = parts[1]
            }
        }
    }

    private var cameraStatusIcon: String {
        controller.cameraIsOnOrStarting ? "video.fill" : "video.slash"
    }

    private func copy(zh: String, en: String) -> String {
        controller.language == .zh ? zh : en
    }
}

private struct SettingsGroup<Content: View>: View {
    var title: String
    var subtitle: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 4)

            AppCard(spacing: 12) {
                content
            }
        }
    }
}

private struct SliderRow: View {
    var title: String
    var value: Binding<Double>
    var range: ClosedRange<Double>
    var step: Double
    var suffix: String

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack {
                Text(title)
                Spacer()
                Text(displayValue)
                    .foregroundStyle(.secondary)
                    .monospacedDigit()
            }
            Slider(value: value, in: range, step: step)
        }
    }

    private var displayValue: String {
        if step >= 1 {
            return "\(Int(value.wrappedValue.rounded()))\(suffix)"
        }
        return String(format: "%.2f%@", value.wrappedValue, suffix)
    }
}
