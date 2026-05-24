import SwiftUI

struct TRSettingsHeader: View {
    let onBackTapped: () -> Void

    var body: some View {
        HStack(alignment: .center) {
            backButton

            Spacer(minLength: 12)

            TRTinyRoutesLogo(
                subtitle: "Settings",
                size: .large,
                showsPin: false
            )
            .frame(maxWidth: .infinity)
            .accessibilityAddTraits(.isHeader)

            Spacer(minLength: 12)

            Color.clear
                .frame(width: 64, height: 64)
                .accessibilityHidden(true)
        }
        .padding(.top, 8)
    }

    private var backButton: some View {
        Button(action: onBackTapped) {
            Image(systemName: "chevron.left")
                .font(.system(size: 26, weight: .black))
                .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                .frame(width: 64, height: 64)
                .background {
                    Circle()
                        .fill(.white.opacity(0.92))
                        .overlay {
                            Circle()
                                .stroke(.white.opacity(0.75), lineWidth: 1)
                        }
                        .shadow(color: .black.opacity(0.08), radius: 10, x: 0, y: 5)
                }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text("Back"))
    }
}

#Preview("Settings Header") {
    TRSettingsHeader(onBackTapped: {})
        .padding(20)
        .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
