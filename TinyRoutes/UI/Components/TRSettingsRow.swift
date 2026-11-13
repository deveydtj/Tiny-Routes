import SwiftUI

struct TRSettingsRow: View {
    let title: String
    let subtitle: String?
    let iconSystemName: String
    let trailingText: String?
    let action: () -> Void

    init(
        title: String,
        subtitle: String? = nil,
        iconSystemName: String,
        trailingText: String? = nil,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.subtitle = subtitle
        self.iconSystemName = iconSystemName
        self.trailingText = trailingText
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                TRSettingsIconCircle(
                    systemName: iconSystemName,
                    tint: TRVillagePalette.teal
                )

                TRSettingsTextBlock(title: title, subtitle: subtitle)

                Spacer(minLength: 8)

                if let trailingText {
                    Text(trailingText)
                        .font(.system(size: 15, weight: .medium, design: .rounded))
                        .foregroundStyle(TRVillagePalette.slate)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                        .layoutPriority(1)
                }

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(TRVillagePalette.slate.opacity(0.6))
                    .accessibilityHidden(true)
            }
            .frame(maxWidth: .infinity, minHeight: 54, alignment: .leading)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(accessibilityLabel))
        .accessibilityAddTraits(.isButton)
    }

    private var accessibilityLabel: String {
        [title, subtitle, trailingText]
            .compactMap { $0 }
            .filter { !$0.isEmpty }
            .joined(separator: ", ")
    }
}

/// A settings row's symbol on a round badge.
struct TRSettingsIconCircle: View {
    let systemName: String
    let tint: Color

    var body: some View {
        TRCozyIconBadge(systemName: systemName, tint: tint, size: 38)
    }
}

struct TRSettingsTextBlock: View {
    let title: String
    let subtitle: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.system(size: 16, weight: .semibold, design: .rounded))
                .foregroundStyle(TRVillagePalette.navy)
                .lineLimit(1)
                .minimumScaleFactor(0.76)

            if let subtitle {
                Text(subtitle)
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(TRVillagePalette.slate)
                    .lineLimit(2)
                    .minimumScaleFactor(0.78)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview("Settings Row") {
    TRSettingsRow(
        title: "Player Profile",
        subtitle: "Route Master",
        iconSystemName: "person.crop.circle.fill",
        trailingText: "Player One",
        action: {}
    )
    .padding(20)
    .background(TRVillageSky())
}
