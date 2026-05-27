import SwiftUI

struct TRShopPinnedBalanceBar: View {
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    var body: some View {
        HStack(alignment: .center) {
            TRMenuSettingsButton(action: onSettingsTapped)

            Spacer(minLength: 12)

            TRCurrencyPill(
                coinTotal: coinTotal,
                onAddTapped: onAddCurrencyTapped,
                size: .menuHeader
            )
        }
        .frame(maxWidth: 760)
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 20)
        .padding(.top, 10)
        .padding(.bottom, 8)
        .background {
            LinearGradient(
                colors: [
                    Color.white.opacity(0.34),
                    Color.white.opacity(0.10)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea(edges: .top)
        }
    }
}

#Preview("Shop Pinned Balance Bar") {
    ZStack(alignment: .top) {
        LinearGradient(
            colors: [
                Color(red: 0.82, green: 0.93, blue: 0.98),
                Color(red: 0.71, green: 0.90, blue: 0.80)
            ],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()

        VStack(spacing: 16) {
            ForEach(0..<8) { index in
                RoundedRectangle(cornerRadius: 8)
                    .fill(.white.opacity(index == 0 ? 0.26 : 0.40))
                    .frame(height: index == 0 ? 120 : 88)
                    .padding(.horizontal, 20)
            }
        }
        .padding(.top, 92)

        TRShopPinnedBalanceBar(
            coinTotal: 12_500,
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )
    }
}
