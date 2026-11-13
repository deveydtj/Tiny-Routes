import SwiftUI

/// A tab's banner: its title, the coin count and the settings gear, pinned over
/// the page as on the level map.
struct TRMenuHeader: View {
    let pageTitle: String
    let subtitleOverride: String?
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    init(
        pageTitle: String,
        subtitleOverride: String? = nil,
        coinTotal: Int,
        onSettingsTapped: @escaping () -> Void,
        onAddCurrencyTapped: @escaping () -> Void
    ) {
        self.pageTitle = pageTitle
        self.subtitleOverride = subtitleOverride
        self.coinTotal = coinTotal
        self.onSettingsTapped = onSettingsTapped
        self.onAddCurrencyTapped = onAddCurrencyTapped
    }

    var body: some View {
        TRCozyMenuBanner(eyebrow: subtitleOverride ?? "Tiny Routes", title: pageTitle) {
            EmptyView()
        } trailing: {
            TRCozyCoinButton(coinTotal: coinTotal, action: onAddCurrencyTapped)
            TRMenuSettingsButton(action: onSettingsTapped)
        }
    }
}

#Preview("Menu Header Variants") {
    ZStack(alignment: .top) {
        TRCozySkyBackground()
        VStack(spacing: 40) {
            TRMenuHeader(pageTitle: "Shop", subtitleOverride: "Customize your journey", coinTotal: 1_250, onSettingsTapped: {}, onAddCurrencyTapped: {})
            TRMenuHeader(pageTitle: "Profile", subtitleOverride: "Your driver's log", coinTotal: 12_500, onSettingsTapped: {}, onAddCurrencyTapped: {})
        }
    }
}
