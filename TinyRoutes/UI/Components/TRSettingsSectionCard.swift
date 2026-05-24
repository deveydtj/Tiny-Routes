import SwiftUI

struct TRSettingsSectionCard<Content: View>: View {
    let title: String
    let subtitle: String?
    private let content: Content

    init(
        title: String,
        subtitle: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.subtitle = subtitle
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.system(size: 20, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)

                if let subtitle {
                    Text(subtitle)
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .accessibilityElement(children: .combine)

            VStack(spacing: 4) {
                content
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background {
            TRGlassCardBackground(cornerRadius: 26)
        }
    }
}

#Preview("Settings Section Card") {
    TRSettingsSectionCard(title: "Audio & Haptics") {
        TRSettingsToggleRow(
            title: "Music",
            subtitle: "Background soundtrack",
            iconSystemName: "music.note",
            isOn: true,
            onChanged: { _ in }
        )
    }
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
