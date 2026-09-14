import SwiftUI

struct MenuBarStatusView: View {
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var controller: AppController

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 9) {
                BrandEyeImage(state: controller.menuBarEyeState, size: 24, tint: BrandPalette.sage)
                VStack(alignment: .leading, spacing: 1) {
                    Text("Dryless")
                        .font(.headline)
                    Text(controller.primaryState.title(language: controller.language))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Divider()

            Button(L10n.text("open", controller.language)) {
                openWindow(id: "main")
                DispatchQueue.main.async {
                    controller.activateMainWindow()
                }
            }

            Button(L10n.text(controller.cameraIsOnOrStarting ? "stop_camera" : "start_camera", controller.language)) {
                controller.toggleCamera()
            }
            .disabled(controller.camera.state == .stopping)

            Button(L10n.text(controller.isPaused ? "resume" : "pause", controller.language)) {
                controller.togglePause()
            }
            .disabled(controller.camera.state != .running)

            Button(L10n.text(controller.settingsStore.settings.soundEnabled ? "sound_off" : "sound_on", controller.language)) {
                controller.toggleSound()
            }

            Divider()

            Button(L10n.text("quit", controller.language)) {
                controller.shutdown()
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(8)
        .frame(width: 240, alignment: .leading)
    }
}
