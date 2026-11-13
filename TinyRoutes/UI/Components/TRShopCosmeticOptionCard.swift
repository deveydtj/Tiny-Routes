import SwiftUI

/// A cosmetic on a small cream card: its preview in a sunken window, its name,
/// and its price or whether it's in use.
struct TRShopCosmeticOptionCard: View {
    let option: ShopCosmeticOption
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                ZStack(alignment: .topTrailing) {
                    TRShopMiniCosmeticPreview(option: option)
                        .frame(height: 76)
                        .saturation(option.isUnlocked ? 1 : 0.75)

                    if option.isSelected {
                        TRShopSelectionBadge(size: 24)
                            .offset(x: 7, y: -7)
                    } else if !option.isUnlocked {
                        Image(systemName: "lock.fill")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(TRVillagePalette.cream)
                            .frame(width: 24, height: 24)
                            .background {
                                Circle()
                                    .fill(TRVillagePalette.slate)
                                    .overlay { Circle().strokeBorder(TRVillagePalette.cream, lineWidth: 2) }
                            }
                            .offset(x: 7, y: -7)
                            .accessibilityHidden(true)
                    }
                }

                Text(option.title)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.navy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.68)
                    .frame(maxWidth: .infinity)

                if let price = option.price, !option.isUnlocked {
                    TRShopCoinPriceLabel(price: price)
                } else if option.isSelected {
                    TRCozyTag(text: "In Use", systemImage: "checkmark", tint: TRVillagePalette.blue)
                        .frame(height: 35)
                } else {
                    Text("Owned")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundStyle(TRVillagePalette.slate)
                        .padding(.horizontal, 10)
                        .frame(height: 24)
                        .background { TRCozyWellBackground(shape: Capsule()) }
                        .frame(height: 35)
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity)
            .frame(height: 172)
            .background {
                MultiVanHUDCardBackground(cornerRadius: 22)
                    .overlay {
                        if option.isSelected {
                            RoundedRectangle(cornerRadius: 22, style: .continuous)
                                .strokeBorder(TRVillagePalette.blue, lineWidth: 3)
                        }
                    }
            }
            .contentShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
        }
        .buttonStyle(TRVillagePressStyle())
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(option.title))
        .accessibilityValue(Text(accessibilityValue))
        .accessibilityHint(Text(accessibilityHint))
        .accessibilityAddTraits(option.isSelected ? [.isButton, .isSelected] : [.isButton])
        .accessibilityAction { action() }
    }

    private var accessibilityValue: String {
        if option.isSelected {
            return "Equipped and owned"
        }

        if option.isUnlocked {
            return "Owned"
        }

        if let price = option.price {
            return "Locked, \(price.formatted(.number.grouping(.automatic))) coins"
        }

        return "Locked"
    }

    private var accessibilityHint: String {
        if option.isSelected {
            return "Already equipped."
        }

        if option.isUnlocked {
            return "Equip cosmetic."
        }

        return "Unlock cosmetic."
    }
}

/// The cosmetic at thumbnail size: a table theme's sky and base, or a confetti's
/// paper over the standard table.
private struct TRShopMiniCosmeticPreview: View {
    let option: ShopCosmeticOption

    var body: some View {
        ZStack {
            TRShopTableSwatch(table: MultiVanTableTheme(rawValue: option.id) ?? .standard)
            if let confetti = MultiVanConfettiStyle(rawValue: option.id) {
                TRShopConfettiScatter(style: confetti)
            }
        }
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
    .background(TRVillageSky())
}
