import SwiftUI

struct TRShopFeaturedCard: View {
    let offer: ShopFeaturedOffer
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 13) {
                HStack(alignment: .top) {
                    if let badgeText = offer.badgeText {
                        Text(badgeText)
                            .font(.system(size: 11, weight: .black, design: .rounded))
                            .foregroundStyle(style.badgeForeground)
                            .lineLimit(1)
                            .minimumScaleFactor(0.76)
                            .padding(.horizontal, 10)
                            .frame(height: 28)
                            .background {
                                Capsule()
                                    .fill(style.badgeBackground)
                            }
                    }

                    Spacer(minLength: 8)
                }
                .frame(height: 28)

                icon
                    .frame(maxWidth: .infinity)

                VStack(alignment: .leading, spacing: 5) {
                    Text(offer.title)
                        .font(.system(size: 23, weight: .black, design: .rounded))
                        .foregroundStyle(style.titleColor)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)

                    Text(offer.subtitle)
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundStyle(style.subtitleColor)
                        .lineLimit(2)
                        .minimumScaleFactor(0.82)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)

                HStack(spacing: 8) {
                    Text(offer.displayPrice)
                        .font(.system(size: 18, weight: .black, design: .rounded))
                        .foregroundStyle(.white)
                        .lineLimit(1)
                        .minimumScaleFactor(0.78)

                    Image(systemName: "arrow.right")
                        .font(.system(size: 15, weight: .black))
                        .foregroundStyle(.white.opacity(0.92))
                }
                .frame(maxWidth: .infinity)
                .frame(height: 46)
                .background {
                    Capsule()
                        .fill(TRGameplayStyle.Colors.successGreen)
                        .shadow(color: TRGameplayStyle.Colors.successGreen.opacity(0.22), radius: 7, x: 0, y: 4)
                }
            }
            .padding(18)
            .frame(maxWidth: .infinity, minHeight: 278, alignment: .topLeading)
            .background {
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(style.backgroundGradient)
                    .overlay {
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .stroke(.white.opacity(0.64), lineWidth: 1)
                    }
                    .shadow(color: style.shadowColor, radius: 16, x: 0, y: 8)
            }
            .contentShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(accessibilityLabel))
        .accessibilityHint(Text("Purchases coming soon."))
    }

    @ViewBuilder
    private var icon: some View {
        switch offer.style {
        case .starterPack:
            TRShopStarterPackIconGroup()
        case .removeAds:
            TRShopNoAdsIcon(size: 104)
                .padding(.vertical, 6)
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

    var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: backgroundColors,
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    var backgroundColors: [Color] {
        switch style {
        case .starterPack:
            return [
                Color(red: 1.00, green: 0.88, blue: 0.41),
                Color(red: 1.00, green: 0.64, blue: 0.24)
            ]
        case .removeAds:
            return [
                Color(red: 0.76, green: 0.57, blue: 1.00),
                Color(red: 0.47, green: 0.30, blue: 0.91)
            ]
        }
    }

    var titleColor: Color {
        switch style {
        case .starterPack:
            return TRGameplayStyle.Colors.titleNavy
        case .removeAds:
            return .white
        }
    }

    var subtitleColor: Color {
        switch style {
        case .starterPack:
            return Color(red: 0.36, green: 0.25, blue: 0.17)
        case .removeAds:
            return .white.opacity(0.86)
        }
    }

    var badgeForeground: Color {
        switch style {
        case .starterPack:
            return Color(red: 0.42, green: 0.24, blue: 0.05)
        case .removeAds:
            return .white
        }
    }

    var badgeBackground: Color {
        switch style {
        case .starterPack:
            return .white.opacity(0.82)
        case .removeAds:
            return .white.opacity(0.22)
        }
    }

    var shadowColor: Color {
        switch style {
        case .starterPack:
            return Color(red: 0.70, green: 0.34, blue: 0.05).opacity(0.20)
        case .removeAds:
            return Color(red: 0.31, green: 0.15, blue: 0.74).opacity(0.24)
        }
    }
}

#Preview("Shop Featured Cards") {
    let service = ShopCatalogService()

    return HStack(spacing: 14) {
        ForEach(service.featuredOffers) { offer in
            TRShopFeaturedCard(offer: offer, action: {})
        }
    }
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
