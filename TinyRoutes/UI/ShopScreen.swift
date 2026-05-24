import SwiftUI

/// In-app shop screen placeholder.
struct ShopScreen: View {
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 16) {
                TRMenuHeader(
                    pageTitle: "Shop",
                    coinTotal: coinTotal,
                    onSettingsTapped: onSettingsTapped,
                    onAddCurrencyTapped: onAddCurrencyTapped
                )
                .padding(.top, 10)

                VStack(spacing: 8) {
                    Text("Shop coming soon")
                        .font(.system(size: 22, weight: .black, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)

                    Text("Coins, cosmetics, and route upgrades will live here.")
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                        .multilineTextAlignment(.center)
                }
                .padding(20)
                .frame(maxWidth: .infinity)
                .background {
                    TRGlassCardBackground(cornerRadius: 28)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 4)
            .padding(.bottom, 10)
        }
        .background {
            LinearGradient(
                colors: [
                    Color.white.opacity(0.24),
                    Color(red: 0.69, green: 0.89, blue: 0.80).opacity(0.12)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        }
    }
}

struct ShopScreen_Previews: PreviewProvider {
    static var previews: some View {
        ShopScreen(
            coinTotal: 1_250,
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )
    }
}
