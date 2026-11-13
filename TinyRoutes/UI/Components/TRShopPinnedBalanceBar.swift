import SwiftUI

/// The shop's banner, pinned over its shelves: the coin balance stays in view
/// while browsing.
struct TRShopPinnedBalanceBar: View {
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    var body: some View {
        TRMenuHeader(
            pageTitle: "Shop",
            subtitleOverride: "Customize your journey",
            coinTotal: coinTotal,
            onSettingsTapped: onSettingsTapped,
            onAddCurrencyTapped: onAddCurrencyTapped
        )
    }
}

#Preview("Shop Pinned Balance Bar") {
    ZStack(alignment: .top) {
        TRCozySkyBackground()
        TRShopPinnedBalanceBar(coinTotal: 12_500, onSettingsTapped: {}, onAddCurrencyTapped: {})
    }
}
