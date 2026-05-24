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
                    tint: TRGameplayStyle.Colors.resultFailureRed
                )

                TRSettingsTextBlock(title: title, subtitle: subtitle)

                Spacer(minLength: 8)

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .black))
                    .foregroundStyle(TRGameplayStyle.Colors.resultFailureRed.opacity(0.72))
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
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
