import SwiftUI

/// A shop shelf's heading, on the sky between the cards.
struct TRShopSectionHeader: View {
    let title: String

    var body: some View {
        TRCozySectionTitle(title: title)
    }
}

#Preview("Shop Section Header") {
    TRShopSectionHeader(title: "Featured")
        .padding(20)
        .background(TRVillageSky())
}
