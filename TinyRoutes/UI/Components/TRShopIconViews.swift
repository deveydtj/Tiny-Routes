import SwiftUI

struct TRShopGemIcon: View {
    var size: CGFloat = 34

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.12, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 0.87, green: 0.60, blue: 1.00),
                            Color(red: 0.47, green: 0.23, blue: 0.92)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .rotationEffect(.degrees(45))
                .overlay {
                    RoundedRectangle(cornerRadius: size * 0.12, style: .continuous)
                        .stroke(.white.opacity(0.72), lineWidth: max(size * 0.08, 2))
                        .rotationEffect(.degrees(45))
                }

            Image(systemName: "sparkle")
                .font(.system(size: size * 0.34, weight: .bold))
                .foregroundStyle(.white.opacity(0.86))
                .offset(x: -size * 0.08, y: -size * 0.08)
        }
        .frame(width: size, height: size)
        .shadow(color: Color(red: 0.47, green: 0.23, blue: 0.92).opacity(0.28), radius: 6, x: 0, y: 4)
        .accessibilityHidden(true)
    }
}

struct TRShopStarterPackIconGroup: View {
    var body: some View {
        ZStack {
            Circle()
                .fill(.white.opacity(0.38))
                .frame(width: 104, height: 104)
                .offset(x: 7, y: 4)

            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: 78, height: 78)
                .shadow(color: .black.opacity(0.12), radius: 6, x: 0, y: 5)

            SpriteImage(name: "gold_coin")
                .scaledToFit()
                .frame(width: 35, height: 35)
                .offset(x: -45, y: 25)
                .rotationEffect(.degrees(-12))

            SpriteImage(name: "gold_coin")
                .scaledToFit()
                .frame(width: 28, height: 28)
                .offset(x: -30, y: -33)
                .rotationEffect(.degrees(15))

            TRShopGemIcon(size: 30)
                .offset(x: 43, y: -26)
        }
        .frame(height: 116)
        .accessibilityHidden(true)
    }
}

struct TRShopNoAdsIcon: View {
    var size: CGFloat = 104

    var body: some View {
        ZStack {
            Circle()
                .fill(.white.opacity(0.96))
                .overlay {
                    Circle()
                        .stroke(.white.opacity(0.78), lineWidth: 4)
                }
                .shadow(color: Color(red: 0.32, green: 0.18, blue: 0.78).opacity(0.22), radius: 10, x: 0, y: 6)

            Text("ADS")
                .font(.system(size: size * 0.26, weight: .bold, design: .rounded))
                .foregroundStyle(Color(red: 0.35, green: 0.24, blue: 0.70))
                .lineLimit(1)
                .minimumScaleFactor(0.75)

            Circle()
                .stroke(Color(red: 0.95, green: 0.20, blue: 0.26), lineWidth: size * 0.08)

            Capsule()
                .fill(Color(red: 0.95, green: 0.20, blue: 0.26))
                .frame(width: size * 0.92, height: size * 0.08)
                .rotationEffect(.degrees(-45))
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

struct TRShopCoinStackIcon: View {
    var size: CGFloat = 50

    var body: some View {
        ZStack {
            SpriteImage(name: "gold_coin")
                .scaledToFit()
                .frame(width: size * 0.62, height: size * 0.62)
                .offset(x: -size * 0.18, y: size * 0.12)

            SpriteImage(name: "gold_coin")
                .scaledToFit()
                .frame(width: size * 0.70, height: size * 0.70)
                .offset(x: size * 0.16, y: size * 0.07)

            SpriteImage(name: "gold_coin")
                .scaledToFit()
                .frame(width: size * 0.58, height: size * 0.58)
                .offset(x: 0, y: -size * 0.18)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

struct TRShopDailyDealsIcon: View {
    var size: CGFloat = 50

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 0.24, green: 0.74, blue: 1.00),
                            Color(red: 0.08, green: 0.45, blue: 0.94)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            RoundedRectangle(cornerRadius: size * 0.09, style: .continuous)
                .fill(.white.opacity(0.26))
                .frame(width: size * 0.72, height: size * 0.32)
                .offset(y: size * 0.10)

            Image(systemName: "tag.fill")
                .font(.system(size: size * 0.34, weight: .bold))
                .foregroundStyle(.white)
                .rotationEffect(.degrees(-8))
        }
        .frame(width: size, height: size)
        .shadow(color: TRVillagePalette.blue.opacity(0.18), radius: 7, x: 0, y: 4)
        .accessibilityHidden(true)
    }
}

struct TRShopGoodieIconView: View {
    let icon: ShopGoodieIcon
    var size: CGFloat = 52

    var body: some View {
        ZStack {
            switch icon {
            case .coins:
                TRShopCoinStackIcon(size: size)
            case .gems:
                TRShopGemIcon(size: size * 0.78)
            case .dailyDeals:
                TRShopDailyDealsIcon(size: size)
            case .dailyBonus:
                SpriteImage(name: "star_calendar")
                    .scaledToFit()
                    .frame(width: size, height: size)
            }
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

/// The blue tick on the cosmetic in use, ringed in cream like the plaques.
struct TRShopSelectionBadge: View {
    var size: CGFloat = 22

    var body: some View {
        Image(systemName: "checkmark")
            .font(.system(size: size * 0.44, weight: .bold))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background {
                Circle()
                    .fill(TRVillagePalette.blue)
                    .overlay { Circle().strokeBorder(TRVillagePalette.cream, lineWidth: 2) }
                    .background { Circle().fill(TRVillagePalette.blueDark).offset(y: 2) }
            }
            .accessibilityHidden(true)
    }
}

/// A cosmetic's price as a cream coin pill, like the banner's count.
struct TRShopCoinPriceLabel: View {
    let price: Int

    var body: some View {
        TRVillagePill {
            TRVillageCoin(size: 14)
            Text(price.formatted(.number.grouping(.automatic)))
        }
        // Room for the pill's lip.
        .padding(.bottom, 3)
    }
}

#Preview("Shop Icons") {
    HStack(spacing: 18) {
        TRShopStarterPackIconGroup()
        TRShopNoAdsIcon(size: 84)
        TRShopGoodieIconView(icon: .coins)
        TRShopGoodieIconView(icon: .gems)
        TRShopGoodieIconView(icon: .dailyDeals)
        TRShopGoodieIconView(icon: .dailyBonus)
    }
    .padding(24)
    .background(TRVillageSky())
}
