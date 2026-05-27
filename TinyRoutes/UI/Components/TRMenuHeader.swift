import SwiftUI

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
        VStack(spacing: 18) {
            HStack(alignment: .center) {
                TRMenuSettingsButton(action: onSettingsTapped)

                Spacer(minLength: 12)

                TRCurrencyPill(
                    coinTotal: coinTotal,
                    onAddTapped: onAddCurrencyTapped,
                    size: .menuHeader
                )
            }

            TRMenuTitleLogo(
                pageTitle: pageTitle,
                subtitleOverride: subtitleOverride
            )
        }
        .padding(.top, 8)
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
