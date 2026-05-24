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
                    tint: TRGameplayStyle.Colors.primaryBlue
                )

                TRSettingsTextBlock(title: title, subtitle: subtitle)

                Spacer(minLength: 8)

                if let trailingText {
                    Text(trailingText)
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                        .layoutPriority(1)
                }

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .black))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText.opacity(0.55))
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

struct TRSettingsIconCircle: View {
    let systemName: String
    let tint: Color

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: 18, weight: .bold))
            .symbolRenderingMode(.hierarchical)
            .foregroundStyle(tint)
            .frame(width: 42, height: 42)
            .background {
                Circle()
                    .fill(tint.opacity(0.13))
                    .overlay {
                        Circle()
                            .stroke(.white.opacity(0.70), lineWidth: 1)
                    }
            }
            .accessibilityHidden(true)
    }
}

struct TRSettingsTextBlock: View {
    let title: String
    let subtitle: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.system(size: 16, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .lineLimit(1)
                .minimumScaleFactor(0.76)

            if let subtitle {
                Text(subtitle)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
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
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
