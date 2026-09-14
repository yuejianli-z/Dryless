import AppKit
import CoreImage
import SwiftUI

enum BrandPalette {
    static let sage = Color(red: 0.42, green: 0.78, blue: 0.53)
}

enum BrandEyeState {
    case open
    case closed

    var resourceName: String {
        switch self {
        case .open: return "eye-open-line-source"
        case .closed: return "eye-closed-source"
        }
    }
}

enum BrandAssets {
    private static let menuBarImageSize = NSSize(width: 18, height: 18)
    private static let openTemplate = loadMonochromeTemplate(for: .open)
    private static let closedTemplate = loadMonochromeTemplate(for: .closed)
    private static let githubTemplate = loadTemplate(named: "github-mark", extension: "svg")

    static func image(for state: BrandEyeState, template: Bool = false) -> NSImage? {
        if template {
            return state == .open ? openTemplate : closedTemplate
        }
        guard let url = resourceURL(for: state),
              let source = NSImage(contentsOf: url),
              let copy = source.copy() as? NSImage else {
            return nil
        }
        return copy
    }

    static var githubMark: NSImage? { githubTemplate }

    private static func loadMonochromeTemplate(for state: BrandEyeState) -> NSImage? {
        guard let url = resourceURL(for: state) else { return nil }
        guard let input = CIImage(contentsOf: url) else { return nil }
        let output = input
            .applyingFilter("CIColorInvert")
            .applyingFilter("CIMaskToAlpha")
        let representation = NSCIImageRep(ciImage: output)
        let image = NSImage(size: menuBarImageSize)
        image.addRepresentation(representation)
        image.size = menuBarImageSize
        image.isTemplate = true
        return image
    }

    private static func resourceURL(for state: BrandEyeState) -> URL? {
        AppResources.bundle.url(forResource: state.resourceName, withExtension: "png", subdirectory: "Icons")
    }

    private static func loadTemplate(named name: String, extension fileExtension: String) -> NSImage? {
        guard let url = AppResources.bundle.url(forResource: name, withExtension: fileExtension, subdirectory: "Icons"),
              let image = NSImage(contentsOf: url) else {
            return nil
        }
        image.isTemplate = true
        return image
    }
}

struct BrandEyeImage: View {
    var state: BrandEyeState
    var size: CGFloat
    var tint: Color = BrandPalette.sage

    var body: some View {
        Group {
            if let image = BrandAssets.image(for: state, template: true) {
                Image(nsImage: image)
                    .resizable()
                    .renderingMode(.template)
                    .foregroundStyle(tint)
            } else {
                Image(systemName: state == .open ? "eye" : "eye.slash")
                    .resizable()
                    .scaledToFit()
                    .foregroundStyle(tint)
            }
        }
        .scaledToFit()
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

struct GitHubMarkImage: View {
    var size: CGFloat
    var tint: Color

    var body: some View {
        Group {
            if let image = BrandAssets.githubMark {
                Image(nsImage: image)
                    .resizable()
                    .renderingMode(.template)
                    .foregroundStyle(tint)
            } else {
                Image(systemName: "star.fill")
                    .resizable()
                    .scaledToFit()
                    .foregroundStyle(tint)
            }
        }
        .scaledToFit()
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}
