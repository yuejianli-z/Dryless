import SwiftUI

struct AppCard<Content: View>: View {
    var spacing: CGFloat = 12
    var fillsHeight = false
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: spacing) {
            content
        }
        .frame(
            maxWidth: .infinity,
            maxHeight: fillsHeight ? .infinity : nil,
            alignment: .topLeading
        )
        .padding(16)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(.quaternary)
        }
    }
}

struct MetricCard: View {
    var title: String
    var value: String
    var unit: String
    var systemImage: String
    var tint: Color = BrandPalette.sage

    var body: some View {
        AppCard(spacing: 10) {
            Label(title, systemImage: systemImage)
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(value)
                    .font(.system(size: 28, weight: .semibold, design: .rounded))
                    .foregroundStyle(tint)
                    .contentTransition(.numericText())

                if !unit.isEmpty {
                    Text(unit)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct SectionHeader: View {
    var title: String
    var subtitle: String? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.headline)
            if let subtitle {
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
