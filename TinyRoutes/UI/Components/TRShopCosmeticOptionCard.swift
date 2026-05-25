import SwiftUI

struct TRShopCosmeticOptionCard: View {
    let option: ShopCosmeticOption
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 9) {
                ZStack(alignment: .topTrailing) {
                    TRShopMiniCosmeticPreview(option: option)
                        .frame(height: 76)

                    if option.isSelected {
                        TRShopSelectionBadge(size: 23)
                            .offset(x: 7, y: -7)
                    } else if option.isUnlocked {
                        Circle()
                            .stroke(TRGameplayStyle.Colors.primaryBlue.opacity(0.36), lineWidth: 2)
                            .frame(width: 20, height: 20)
                            .background {
                                Circle()
                                    .fill(.white.opacity(0.78))
                            }
                            .offset(x: 6, y: -6)
                            .accessibilityHidden(true)
                    } else {
                        Image(systemName: "lock.fill")
                            .font(.system(size: 11, weight: .black))
                            .foregroundStyle(.white)
                            .frame(width: 23, height: 23)
                            .background {
                                Circle()
                                    .fill(Color(red: 0.43, green: 0.50, blue: 0.62))
                            }
                            .offset(x: 7, y: -7)
                            .accessibilityHidden(true)
                    }
                }

                Text(option.title)
                    .font(.system(size: 14, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.68)
                    .frame(maxWidth: .infinity)

                if let price = option.price, !option.isUnlocked {
                    TRShopCoinPriceLabel(price: price)
                } else {
                    Text(option.isSelected ? "In Use" : "Owned")
                        .font(.system(size: 12, weight: .black, design: .rounded))
                        .foregroundStyle(option.isSelected ? TRGameplayStyle.Colors.primaryBlue : TRGameplayStyle.Colors.secondaryText)
                        .lineLimit(1)
                        .minimumScaleFactor(0.78)
                        .frame(height: 30)
                        .padding(.horizontal, 10)
                        .background {
                            Capsule()
                                .fill(Color(red: 0.92, green: 0.96, blue: 1.00).opacity(option.isSelected ? 1.0 : 0.72))
                        }
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity)
            .frame(height: 162)
            .background {
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(.white.opacity(option.isUnlocked ? 0.92 : 0.82))
                    .overlay {
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(option.isSelected ? TRGameplayStyle.Colors.primaryBlue : .white.opacity(0.72), lineWidth: option.isSelected ? 3 : 1)
                    }
                    .shadow(color: .black.opacity(option.isSelected ? 0.12 : 0.07), radius: 10, x: 0, y: 5)
            }
            .contentShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(option.title))
        .accessibilityValue(Text(accessibilityValue))
        .accessibilityHint(Text(option.isUnlocked ? "Select cosmetic." : "Unlock cosmetic."))
        .accessibilityAddTraits(option.isSelected ? [.isSelected] : [])
    }

    private var accessibilityValue: String {
        if option.isSelected {
            return "Selected and owned"
        }

        if option.isUnlocked {
            return "Owned"
        }

        if let price = option.price {
            return "Locked, \(price.formatted(.number.grouping(.automatic))) coins"
        }

        return "Locked"
    }
}

private struct TRShopMiniCosmeticPreview: View {
    let option: ShopCosmeticOption

    var body: some View {
        ZStack {
            TRShopRoutePreviewView(accent: option.accent, compact: true)

            switch option.categoryID {
            case ShopCosmeticCategoryID.deliveryDots:
                deliveryDotPreview
            case ShopCosmeticCategoryID.trails:
                trailPreview
            case ShopCosmeticCategoryID.confetti:
                confettiPreview
            case ShopCosmeticCategoryID.destinations:
                destinationPreview
            default:
                EmptyView()
            }
        }
    }

    private var deliveryDotPreview: some View {
        Circle()
            .fill(option.accent.routeColor)
            .overlay {
                Circle()
                    .stroke(.white, lineWidth: 5)
            }
            .frame(width: 34, height: 34)
            .shadow(color: option.accent.routeColor.opacity(0.28), radius: 6, x: 0, y: 4)
    }

    private var trailPreview: some View {
        HStack(spacing: 7) {
            ForEach(0..<4, id: \.self) { index in
                Image(systemName: index.isMultiple(of: 2) ? "sparkle" : "circle.fill")
                    .font(.system(size: index.isMultiple(of: 2) ? 15 : 8, weight: .black))
                    .foregroundStyle(.white)
                    .shadow(color: option.accent.routeShadowColor.opacity(0.35), radius: 4, x: 0, y: 2)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background {
            Capsule()
                .fill(option.accent.routeColor.opacity(0.80))
        }
    }

    private var confettiPreview: some View {
        HStack(spacing: 5) {
            ForEach(0..<5, id: \.self) { index in
                Image(systemName: index.isMultiple(of: 2) ? "star.fill" : "circle.fill")
                    .font(.system(size: index.isMultiple(of: 2) ? 13 : 8, weight: .black))
                    .foregroundStyle(index.isMultiple(of: 2) ? TRGameplayStyle.Colors.resultGold : option.accent.routeColor)
                    .rotationEffect(.degrees(Double(index * 13)))
            }
        }
        .padding(9)
        .background {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(.white.opacity(0.78))
        }
    }

    private var destinationPreview: some View {
        ZStack {
            Circle()
                .fill(.white.opacity(0.92))
                .frame(width: 42, height: 42)

            if option.id == "destinationFlag" {
                SpriteImage(name: "finish_flag_pin")
                    .scaledToFit()
                    .frame(width: 34, height: 34)
            } else {
                Image(systemName: option.id == "destinationCabin" ? "house.fill" : "mappin.circle.fill")
                    .font(.system(size: 25, weight: .black))
                    .foregroundStyle(option.accent.routeColor)
            }
        }
        .shadow(color: option.accent.routeColor.opacity(0.22), radius: 6, x: 0, y: 4)
    }
}

#Preview("Shop Cosmetic Option Cards") {
    let options = ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.routeThemes)

    return LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
        ForEach(options) { option in
            TRShopCosmeticOptionCard(option: option, action: {})
        }
    }
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
