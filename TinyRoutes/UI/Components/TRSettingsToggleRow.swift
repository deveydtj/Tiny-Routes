import SwiftUI

struct TRSettingsToggleRow: View {
    let title: String
    let subtitle: String?
    let iconSystemName: String
    let isOn: Bool
    let onChanged: (Bool) -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    init(
        title: String,
        subtitle: String? = nil,
        iconSystemName: String,
        isOn: Bool,
        onChanged: @escaping (Bool) -> Void
    ) {
        self.title = title
        self.subtitle = subtitle
        self.iconSystemName = iconSystemName
        self.isOn = isOn
        self.onChanged = onChanged
    }

    var body: some View {
        Toggle(isOn: binding) {
            HStack(spacing: 12) {
                TRSettingsIconCircle(
                    systemName: iconSystemName,
                    tint: TRGameplayStyle.Colors.primaryBlue
                )

                TRSettingsTextBlock(title: title, subtitle: subtitle)
            }
            .frame(maxWidth: .infinity, minHeight: 54, alignment: .leading)
        }
        .toggleStyle(.switch)
        .tint(TRGameplayStyle.Colors.primaryBlue)
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.16), value: isOn)
        .accessibilityLabel(Text(title))
    }

    private var binding: Binding<Bool> {
        Binding(
            get: { isOn },
            set: onChanged
        )
    }
}

#Preview("Settings Toggle Row") {
    TRSettingsToggleRow(
        title: "Route Hints",
        subtitle: "Show a little help on early puzzles",
        iconSystemName: "signpost.right.fill",
        isOn: true,
        onChanged: { _ in }
    )
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
