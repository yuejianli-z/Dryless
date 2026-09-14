import AppKit
import SwiftUI

struct ScrollChromeHider: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let view = NSView(frame: .zero)
        DispatchQueue.main.async {
            hideScrollChrome(from: view)
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async {
            hideScrollChrome(from: nsView)
        }
    }

    private func hideScrollChrome(from view: NSView) {
        guard let scrollView = nearestScrollView(from: view) else { return }
        scrollView.hasVerticalScroller = false
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.scrollerStyle = .overlay
    }

    private func nearestScrollView(from view: NSView) -> NSScrollView? {
        var candidate: NSView? = view
        while let current = candidate {
            if let scrollView = current as? NSScrollView {
                return scrollView
            }
            if let scrollView = current.enclosingScrollView {
                return scrollView
            }
            candidate = current.superview
        }
        return nil
    }
}

struct HiddenScrollerScrollView<Content: View>: NSViewRepresentable {
    var content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSScrollView()
        scrollView.drawsBackground = false
        scrollView.hasVerticalScroller = false
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.scrollerStyle = .overlay
        scrollView.verticalScrollElasticity = .allowed
        scrollView.horizontalScrollElasticity = .none

        let hostingView = NSHostingView(rootView: content)
        hostingView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.documentView = hostingView

        NSLayoutConstraint.activate([
            hostingView.leadingAnchor.constraint(equalTo: scrollView.contentView.leadingAnchor),
            hostingView.trailingAnchor.constraint(equalTo: scrollView.contentView.trailingAnchor),
            hostingView.topAnchor.constraint(equalTo: scrollView.contentView.topAnchor),
            hostingView.widthAnchor.constraint(equalTo: scrollView.contentView.widthAnchor)
        ])

        context.coordinator.hostingView = hostingView
        return scrollView
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        scrollView.hasVerticalScroller = false
        scrollView.hasHorizontalScroller = false
        context.coordinator.hostingView?.rootView = content
    }

    final class Coordinator {
        var hostingView: NSHostingView<Content>?
    }
}
