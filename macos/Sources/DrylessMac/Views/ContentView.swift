import DrylessCore
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var controller: AppController
    @SceneStorage("selectedSection") private var selectedSectionRaw = AppSection.monitor.rawValue

    private var selectedSection: AppSection {
        AppSection(rawValue: selectedSectionRaw) ?? .monitor
    }

    private var selection: Binding<AppSection?> {
        Binding {
            AppSection(rawValue: selectedSectionRaw) ?? .monitor
        } set: { next in
            selectedSectionRaw = (next ?? .monitor).rawValue
        }
    }

    var body: some View {
        NavigationSplitView {
            SidebarView(selection: selection)
                .navigationSplitViewColumnWidth(min: 190, ideal: 210, max: 220)
        } detail: {
            detail
                .navigationTitle(selectedSection.title(language: controller.language))
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button {
                    controller.toggleCamera()
                } label: {
                    Label(
                        L10n.text(controller.cameraIsOnOrStarting ? "stop_camera" : "start_camera", controller.language),
                        systemImage: controller.cameraIsOnOrStarting ? "video.fill" : "video.slash"
                    )
                }
                .disabled(controller.camera.state == .stopping)

                Button {
                    controller.toggleSound()
                } label: {
                    Label(
                        L10n.text(controller.settingsStore.settings.soundEnabled ? "sound_off" : "sound_on", controller.language),
                        systemImage: controller.settingsStore.settings.soundEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill"
                    )
                }

                Button {
                    controller.togglePause()
                } label: {
                    Label(
                        L10n.text(controller.isPaused ? "resume" : "pause", controller.language),
                        systemImage: controller.isPaused ? "play.fill" : "pause.fill"
                    )
                }
                .disabled(controller.camera.state != .running)
            }
        }
    }

    @ViewBuilder
    private var detail: some View {
        switch selectedSection {
        case .monitor:
            MonitorView(controller: controller)
        case .stats:
            StatsView(controller: controller)
        case .settings:
            SettingsView(controller: controller)
        }
    }
}
