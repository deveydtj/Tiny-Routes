import SwiftUI

/// A featured offer on a cream card: its picture in a tinted window on the left,
/// its name and a chunky price button on the right.
struct TRShopFeaturedCard: View {
    let offer: ShopFeaturedOffer
    let action: () -> Void

    var body: some View {
        HStack(spacing: 14) {
            iconWindow

            VStack(alignment: .leading, spacing: 5) {
                if let badgeText = offer.badgeText {
                    TRCozyTag(text: badgeText, systemImage: "sparkles", tint: style.badgeTint)
                        .padding(.bottom, 2)
                }

                Text(offer.title)
                    .font(.system(size: 21, weight: .bold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.navy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)

                Text(offer.subtitle)
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(TRVillagePalette.slate)
                    .lineLimit(2)
                    .minimumScaleFactor(0.82)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 8)

                Button(action: action) {
                    HStack(spacing: 7) {
                        Text(offer.displayPrice)
                            .font(.system(size: 17, weight: .bold, design: .rounded))
                            .lineLimit(1)
                            .minimumScaleFactor(0.78)
                        Image(systemName: "arrow.right")
                            .font(.system(size: 14, weight: .bold))
                    }
                    .frame(maxWidth: .infinity, minHeight: 42)
                }
                .buttonStyle(MultiVanHUDButtonStyle(isProminent: true, tint: MultiVanHUDStyle.pine, shape: AnyShape(Capsule())))
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(14)
        .frame(maxWidth: .infinity, minHeight: 168, alignment: .topLeading)
        .background { MultiVanHUDCardBackground(cornerRadius: 26) }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(accessibilityLabel))
        .accessibilityHint(Text("Purchases coming soon."))
        .accessibilityAddTraits(.isButton)
        .accessibilityAction { action() }
    }

    /// The offer's picture, on a little patch of tinted sky.
    private var iconWindow: some View {
        let shape = RoundedRectangle(cornerRadius: 20, style: .continuous)
        return ZStack {
            shape.fill(LinearGradient(colors: style.windowColors, startPoint: .top, endPoint: .bottom))
            TRPaperCloud()
                .frame(width: 54, height: 22)
                .opacity(0.8)
                .offset(x: 24, y: -48)
            icon
        }
        .frame(width: 116)
        .frame(maxHeight: .infinity)
        .clipShape(shape)
        .overlay { shape.strokeBorder(.white.opacity(0.85), lineWidth: 2) }
        .accessibilityHidden(true)
    }

    @ViewBuilder
    private var icon: some View {
        switch offer.style {
        case .starterPack:
            TRShopStarterPackIconGroup()
                .scaleEffect(0.78)
        case .removeAds:
            TRShopNoAdsIcon(size: 74)
        }
    }

    private var accessibilityLabel: String {
        [
            offer.title,
            offer.subtitle,
            offer.badgeText,
            offer.displayPrice
        ]
        .compactMap { $0 }
        .joined(separator: ", ")
    }

    private var style: FeaturedCardStyle {
        FeaturedCardStyle(style: offer.style)
    }
}

private struct FeaturedCardStyle {
    let style: ShopFeaturedOfferStyle

    /// The window behind the picture: warm for the pack, sky for no ads.
    var windowColors: [Color] {
        switch style {
        case .starterPack:
            return [Color(hex: 0xFFE7A8), Color(hex: 0xF9CC66)]
        case .removeAds:
            return [Color(hex: 0xCDE8F8), Color(hex: 0x9ED1F2)]
        }
    }

    var badgeTint: Color {
        switch style {
        case .starterPack:
            return TRVillagePalette.roofs[0]
        case .removeAds:
            return TRVillagePalette.teal
        }
    }
}

#Preview("Shop Featured Cards") {
    let service = ShopCatalogService()

    return VStack(spacing: 14) {
        ForEach(service.featuredOffers) { offer in
            TRShopFeaturedCard(offer: offer, action: {})
        }
    }
    .padding(20)
    .background(TRVillageSky())
}
