import SwiftUI

struct TRSettingsDangerRow: View {
    let title: String
    let subtitle: String?
    let iconSystemName: String
    let action: () -> Void

    init(
        title: String,
        subtitle: String? = nil,
        iconSystemName: String,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.subtitle = subtitle
        self.iconSystemName = iconSystemName
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                TRSettingsIconCircle(
                    systemName: iconSystemName,
                    tint: TRVillagePalette.roofs[0]
                )

                TRSettingsTextBlock(title: title, subtitle: subtitle)

                Spacer(minLength: 8)

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(TRVillagePalette.roofs[0].opacity(0.72))
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
        [title, subtitle]
            .compactMap { $0 }
            .filter { !$0.isEmpty }
            .joined(separator: ", ")
    }
}

#Preview("Settings Danger Row") {
    TRSettingsDangerRow(
        title: "Reset Progress",
        subtitle: "Clear local level stars",
        iconSystemName: "exclamationmark.triangle.fill",
        action: {}
    )
    .padding(20)
    .background(TRVillageSky())
}
