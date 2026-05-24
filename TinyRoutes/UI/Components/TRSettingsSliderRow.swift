import SwiftUI

struct TRSettingsSliderRow: View {
    let title: String
    let iconSystemName: String
    let value: Double
    let isEnabled: Bool
    let onChanged: (Double) -> Void

    init(
        title: String,
        iconSystemName: String,
        value: Double,
        isEnabled: Bool = true,
        onChanged: @escaping (Double) -> Void
    ) {
        self.title = title
        self.iconSystemName = iconSystemName
        self.value = value
        self.isEnabled = isEnabled
        self.onChanged = onChanged
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                TRSettingsIconCircle(
                    systemName: iconSystemName,
                    tint: TRGameplayStyle.Colors.primaryBlue
                )

                Text(title)
                    .font(.system(size: 16, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)

                Spacer(minLength: 8)

                Text(percentText)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                    .monospacedDigit()
                    .lineLimit(1)
            }

            Slider(value: binding, in: 0...1)
                .tint(TRGameplayStyle.Colors.primaryBlue)
                .disabled(!isEnabled)
                .accessibilityLabel(Text(title))
                .accessibilityValue(Text("\(percentage) percent"))
        }
        .frame(maxWidth: .infinity, minHeight: 72, alignment: .leading)
        .opacity(isEnabled ? 1 : 0.46)
    }

    private var binding: Binding<Double> {
        Binding(
            get: { value },
            set: onChanged
        )
    }

    private var percentage: Int {
        Int((min(max(value, 0), 1) * 100).rounded())
    }

    private var percentText: String {
        "\(percentage)%"
    }
}

#Preview("Settings Slider Row") {
    TRSettingsSliderRow(
        title: "Music Volume",
        iconSystemName: "speaker.wave.2.fill",
        value: 0.75,
        onChanged: { _ in }
    )
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
