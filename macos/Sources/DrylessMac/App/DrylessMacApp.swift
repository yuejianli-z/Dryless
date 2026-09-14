import AppKit
import SwiftUI

@main
struct DrylessMacApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var controller: AppController

    init() {
        if let fixture = ReadmeDemoFixture.fromArguments() {
            _controller = StateObject(
                wrappedValue: AppController(
                    settingsStore: fixture.settingsStore,
                    historyStore: fixture.historyStore,
                    readmeDemo: fixture
                )
            )
        } else {
            _controller = StateObject(wrappedValue: AppController())
        }
    }

    var body: some Scene {
        WindowGroup("Dryless", id: "main") {
            ContentView()
                .environmentObject(controller)
                .tint(BrandPalette.sage)
                .frame(
                    minWidth: 840,
                    idealWidth: 1000,
                    maxWidth: 1040,
                    minHeight: 590,
                    idealHeight: 590,
                    maxHeight: 700
                )
                .task {
                    controller.start()
                }
        }
        .defaultSize(width: 1000, height: 590)
        .windowResizability(.contentSize)
        .windowToolbarStyle(.unified)
        .commands {
            CommandMenu("Dryless") {
                Button(controller.cameraIsOnOrStarting ? L10n.text("stop_camera", controller.language) : L10n.text("start_camera", controller.language)) {
                    controller.toggleCamera()
                }
                .keyboardShortcut("k", modifiers: [.command, .shift])

                Button(L10n.text(controller.isPaused ? "resume" : "pause", controller.language)) {
                    controller.togglePause()
                }
                .keyboardShortcut("p", modifiers: [.command])
                .disabled(controller.camera.state != .running)

                Button(L10n.text(controller.settingsStore.settings.soundEnabled ? "sound_off" : "sound_on", controller.language)) {
                    controller.toggleSound()
                }

                Divider()

                Button(L10n.text("open", controller.language)) {
                    controller.activateMainWindow()
                }
                .keyboardShortcut("0", modifiers: [.command])
            }
        }

        MenuBarExtra {
            MenuBarStatusView()
                .environmentObject(controller)
        } label: {
            if let image = BrandAssets.image(for: controller.menuBarEyeState, template: true) {
                Image(nsImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 18, height: 18)
                    .accessibilityLabel("Dryless")
            } else {
                Image(systemName: controller.menuBarEyeState == .open ? "eye" : "eye.slash")
                    .accessibilityLabel("Dryless")
            }
        }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }
}
