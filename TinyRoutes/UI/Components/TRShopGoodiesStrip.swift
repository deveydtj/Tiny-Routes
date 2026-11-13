import SwiftUI

struct TRShopGoodiesStrip: View {
    let actions: [ShopGoodieAction]
    let onActionTapped: (ShopGoodieAction) -> Void

    var body: some View {
        ViewThatFits(in: .horizontal) {
            wideLayout
            scrollLayout
        }
        .padding(12)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 26)
        }
    }

    private var wideLayout: some View {
        HStack(spacing: 10) {
            ForEach(actions) { action in
                goodieTile(action)
                    .frame(maxWidth: .infinity)
            }
        }
        .frame(minWidth: 560)
    }

    private var scrollLayout: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(actions) { action in
                    goodieTile(action)
                        .frame(width: 128)
                }
            }
            .padding(.vertical, 1)
        }
    }

    private func goodieTile(_ action: ShopGoodieAction) -> some View {
        Button {
            onActionTapped(action)
        } label: {
            VStack(spacing: 8) {
                TRShopGoodieIconView(icon: action.icon, size: 52)

                VStack(spacing: 2) {
                    Text(action.title)
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(TRVillagePalette.navy)
                        .lineLimit(1)
                        .minimumScaleFactor(0.68)

                    Text(action.subtitle)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(TRVillagePalette.slate)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                }

                Text(action.buttonTitle)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.cream)
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)
                    .padding(.horizontal, 12)
                    .frame(height: 30)
                    .frame(maxWidth: .infinity)
                    .background {
                        Capsule()
                            .fill(MultiVanHUDStyle.pine)
                            .background { Capsule().fill(MultiVanHUDStyle.pineDark).overlay { Capsule().fill(.black.opacity(0.2)) }.offset(y: 2.5) }
                    }
                    .padding(.bottom, 2.5)
            }
            .padding(.horizontal, 9)
            .padding(.vertical, 10)
            .frame(minHeight: 136)
            .background { TRCozyWellBackground(cornerRadius: 18) }
            .contentShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        }
        .buttonStyle(TRVillagePressStyle())
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(action.title), \(action.subtitle), \(action.buttonTitle)"))
        .accessibilityHint(Text(action.id == "dailyBonus" ? "Claim daily coin bonus." : "Coming soon."))
        .accessibilityAddTraits(.isButton)
        .accessibilityAction { onActionTapped(action) }
    }
}

#Preview("Shop Goodies Strip") {
    TRShopGoodiesStrip(actions: ShopCatalogService().goodieActions, onActionTapped: { _ in })
        .padding(20)
        .background(TRVillageSky())
}
