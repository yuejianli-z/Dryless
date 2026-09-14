import Foundation
import SwiftUI

struct SidebarView: View {
    @EnvironmentObject private var controller: AppController
    var selection: Binding<AppSection?>
    @State private var isStarHovering = false

    private let repositoryURL = URL(string: "https://github.com/yuejianli-z/Dryless")!

    var body: some View {
        VStack(spacing: 0) {
            brandHeader

            List(selection: selection) {
                Section {
                    ForEach(AppSection.allCases) { section in
                        HStack(spacing: 10) {
                            if section == .monitor {
                                BrandEyeImage(state: controller.menuBarEyeState, size: 18, tint: BrandPalette.sage)
                            } else {
                                Image(systemName: section.systemImage)
                                    .foregroundStyle(.secondary)
                                    .frame(width: 18)
                            }

                            VStack(alignment: .leading, spacing: 2) {
                                Text(section.title(language: controller.language))
                                    .lineLimit(1)
                                Text(section.detail(language: controller.language))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                        .tag(section)
                    }
                }
            }
            .listStyle(.sidebar)

            Divider()

            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 10) {
                    BrandEyeImage(
                        state: controller.menuBarEyeState,
                        size: 26,
                        tint: BrandPalette.sage
                    )

                    VStack(alignment: .leading, spacing: 4) {
                        Text(controller.primaryState.title(language: controller.language))
                            .font(.caption.weight(.semibold))
                            .lineLimit(1)
                        Text(L10n.text("app_subtitle", controller.language))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                Link(destination: repositoryURL) {
                    HStack(spacing: 9) {
                        GitHubMarkImage(size: 17, tint: .primary)
                        Text("Star on GitHub")
                            .font(.caption.weight(.semibold))
                        Spacer()
                        Image(systemName: "arrow.up.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 12)
                    .frame(maxWidth: .infinity)
                    .frame(height: 38)
                    .background(
                        BrandPalette.sage.opacity(isStarHovering ? 0.25 : 0.16),
                        in: RoundedRectangle(cornerRadius: 7, style: .continuous)
                    )
                    .contentShape(RoundedRectangle(cornerRadius: 7, style: .continuous))
                }
                .buttonStyle(.plain)
                .onHover { isStarHovering = $0 }
                .help(controller.language == .zh ? "在 GitHub 上为 Dryless 加星" : "Star Dryless on GitHub")
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var brandHeader: some View {
        HStack(spacing: 10) {
            BrandEyeImage(state: controller.menuBarEyeState, size: 30, tint: BrandPalette.sage)
            HStack(spacing: 0) {
                Text("Dry")
                    .foregroundStyle(.primary)
                Text("less")
                    .foregroundStyle(BrandPalette.sage)
            }
            .font(.system(size: 27, weight: .bold, design: .rounded))
        }
        .padding(.horizontal, 16)
        .padding(.top, 10)
        .padding(.bottom, 6)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
