import SwiftUI

struct TRMenuHeader: View {
    let pageTitle: String
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    var body: some View {
        VStack(spacing: 18) {
            HStack(alignment: .center) {
                settingsButton

                Spacer(minLength: 12)

                TRCurrencyPill(
                    coinTotal: coinTotal,
                    onAddTapped: onAddCurrencyTapped,
                    size: .menuHeader
                )
            }

            TRTinyRoutesLogo(
                subtitle: pageTitle,
                size: .large,
                showsPin: false
            )
            .frame(maxWidth: .infinity)
            .accessibilityAddTraits(.isHeader)
        }
        .padding(.top, 8)
    }

    private var settingsButton: some View {
        Button(action: onSettingsTapped) {
            Image(systemName: "gearshape.fill")
                .font(.system(size: 28, weight: .bold))
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
        .accessibilityLabel(Text("Settings"))
    }
}

#Preview("Menu Header Variants") {
    VStack(spacing: 28) {
        TRMenuHeader(pageTitle: "Levels", coinTotal: 1_250, onSettingsTapped: {}, onAddCurrencyTapped: {})
        TRMenuHeader(pageTitle: "Shop", coinTotal: 1_250, onSettingsTapped: {}, onAddCurrencyTapped: {})
        TRMenuHeader(pageTitle: "Profile", coinTotal: 1_250, onSettingsTapped: {}, onAddCurrencyTapped: {})
    }
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
