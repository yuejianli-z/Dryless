import AppKit
import DrylessCore
import SwiftUI

struct CameraPreviewView: View {
    var image: NSImage?
    var state: CameraState
    var primaryState: PrimaryAppState
    var language: AppLanguage
    var previewVisible: Bool
    var aspectRatio: CGFloat
    var landmarks: EyeLandmarks?
    var onCameraAction: () -> Void

    var body: some View {
        GeometryReader { proxy in
            let canvasSize = fittedSize(in: proxy.size)

            previewCanvas
                .frame(width: canvasSize.width, height: canvasSize.height)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        }
        .clipped()
    }

    private var previewCanvas: some View {
        ZStack {
            Rectangle()
                .fill(Color.black)

            if state == .running, previewVisible, let image {
                ZStack {
                    Image(nsImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .clipped()

                    if let landmarks {
                        EyeLandmarkOverlay(landmarks: landmarks)
                    }
                }
            } else {
                emptyContent
            }

            VStack {
                HStack {
                    statusBadge
                    Spacer()
                    if state == .running {
                        Button {
                            onCameraAction()
                        } label: {
                            Image(systemName: "stop.fill")
                        }
                        .buttonStyle(.borderless)
                        .foregroundStyle(.secondary)
                        .accessibilityLabel(L10n.text("stop_camera", language))
                    }
                }
                Spacer()
            }
            .padding(14)
        }
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(.white.opacity(0.11))
        }
        .clipped()
    }

    private var emptyContent: some View {
        VStack(spacing: 14) {
            BrandEyeImage(
                state: state == .running ? .open : .closed,
                size: 62,
                tint: BrandPalette.sage.opacity(0.78)
            )

            VStack(spacing: 4) {
                Text(emptyTitle)
                    .font(.headline)
                    .foregroundStyle(.white.opacity(0.86))
                if let detail = state.failureDetail(language: language) {
                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.48))
                        .lineLimit(2)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 340)
                }
            }

        }
        .padding(28)
    }

    private var emptyTitle: String {
        if state == .running, !previewVisible {
            return L10n.text("preview_hidden", language)
        }
        return state.label(language: language)
    }

    private var statusBadge: some View {
        Label(primaryState.title(language: language), systemImage: primaryState.systemImage)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white.opacity(0.88))
            .padding(.horizontal, 10)
            .frame(height: 28)
            .background(.black.opacity(0.58), in: Capsule())
    }

    private func fittedSize(in available: CGSize) -> CGSize {
        guard available.width > 0, available.height > 0 else { return .zero }
        let ratio = min(2.5, max(0.5, aspectRatio))
        let availableRatio = available.width / available.height
        if availableRatio > ratio {
            return CGSize(width: available.height * ratio, height: available.height)
        }
        return CGSize(width: available.width, height: available.width / ratio)
    }
}

private struct EyeLandmarkOverlay: View {
    let landmarks: EyeLandmarks

    var body: some View {
        Canvas { context, size in
            for eye in [landmarks.left, landmarks.right] {
                var path = Path()
                guard let first = eye.first else { continue }
                path.move(to: point(first, in: size))
                for node in eye.dropFirst() {
                    path.addLine(to: point(node, in: size))
                }
                path.closeSubpath()
                context.stroke(path, with: .color(BrandPalette.sage.opacity(0.64)), lineWidth: 0.45)

                for node in eye {
                    let center = point(node, in: size)
                    let dot = CGRect(x: center.x - 0.55, y: center.y - 0.55, width: 1.1, height: 1.1)
                    context.fill(Path(ellipseIn: dot), with: .color(BrandPalette.sage.opacity(0.76)))
                }
            }
        }
        .allowsHitTesting(false)
    }

    private func point(_ point: CGPoint, in size: CGSize) -> CGPoint {
        CGPoint(x: point.x * size.width, y: point.y * size.height)
    }
}
