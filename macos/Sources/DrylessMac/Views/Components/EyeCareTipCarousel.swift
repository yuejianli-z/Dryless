import Combine
import DrylessCore
import SwiftUI

struct EyeCareTipCarousel: View {
    @Environment(\.scenePhase) private var scenePhase
    var language: AppLanguage
    var pausesAutomatically: Bool

    @State private var selection = 0
    @State private var isHovering = false
    @FocusState private var isFocused: Bool

    private let timer = Timer.publish(every: 20, on: .main, in: .common).autoconnect()

    private var tips: [(icon: String, title: String, detail: String, tint: Color)] {
        if language == .zh {
            return [
                ("eye", "自然轻眨", "轻轻眨几次，让泪膜重新铺开。", BrandPalette.sage),
                ("mountain.2", "看向远处", "每 20 分钟看向约 6 米外，持续 20 秒。", .blue),
                ("moon", "闭眼放松", "完整闭眼 10 秒，让眼睛短暂休息。", .orange)
            ]
        }
        return [
            ("eye", "Blink gently", "Blink a few times to refresh the tear film.", BrandPalette.sage),
            ("mountain.2", "Look into the distance", "Every 20 minutes, look about 6 m away for 20 seconds.", .blue),
            ("moon", "Close and rest", "Close your eyes fully for 10 seconds.", .orange)
        ]
    }

    var body: some View {
        let tip = tips[selection]
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                Group {
                    if tip.icon == "eye" {
                        BrandEyeImage(state: .open, size: 18, tint: tip.tint)
                    } else {
                        Image(systemName: tip.icon)
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundStyle(tip.tint)
                    }
                }
                    .frame(width: 30, height: 30)
                    .background(tip.tint.opacity(0.12), in: Circle())

                VStack(alignment: .leading, spacing: 2) {
                    Text(tip.title)
                        .font(.subheadline.weight(.semibold))
                    Text(tip.detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer(minLength: 8)
            }

            HStack(spacing: 5) {
                ForEach(tips.indices, id: \.self) { index in
                    Capsule()
                        .fill(index == selection ? BrandPalette.sage : Color.secondary.opacity(0.22))
                        .frame(width: index == selection ? 14 : 5, height: 5)
                }
            }
            .frame(maxWidth: .infinity)
            .animation(.easeInOut(duration: 0.2), value: selection)
        }
        .padding(12)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .focusable()
        .focusEffectDisabled()
        .focused($isFocused)
        .onHover { isHovering = $0 }
        .onMoveCommand { direction in
            switch direction {
            case .left: selection = (selection + tips.count - 1) % tips.count
            case .right: selection = (selection + 1) % tips.count
            default: break
            }
        }
        .onReceive(timer) { _ in
            guard scenePhase == .active, !pausesAutomatically, !isHovering, !isFocused else { return }
            selection = (selection + 1) % tips.count
        }
        .onChange(of: language) { _, _ in selection = 0 }
    }
}
