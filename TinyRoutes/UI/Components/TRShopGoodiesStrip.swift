import SwiftUI

struct TRShopGoodiesStrip: View {
    let actions: [ShopGoodieAction]
    let onActionTapped: (ShopGoodieAction) -> Void

    var body: some View {
        ViewThatFits(in: .horizontal) {
            wideLayout
            scrollLayout
        }
        .padding(14)
        .background {
            TRGlassCardBackground(cornerRadius: 28)
        }
    }

    private var wideLayout: some View {
        HStack(spacing: 0) {
            ForEach(Array(actions.enumerated()), id: \.element.id) { index, action in
                goodieTile(action)
                    .frame(maxWidth: .infinity)

                if index < actions.count - 1 {
                    Divider()
                        .frame(height: 118)
                }
            }
        }
        .frame(minWidth: 560)
    }

    private var scrollLayout: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(actions) { action in
                    goodieTile(action)
                        .frame(width: 130)
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
                        .font(.system(size: 14, weight: .black, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                        .lineLimit(1)
                        .minimumScaleFactor(0.68)

                    Text(action.subtitle)
                        .font(.system(size: 11, weight: .semibold, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                }

                Text(action.buttonTitle)
                    .font(.system(size: 12, weight: .black, design: .rounded))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)
                    .padding(.horizontal, 12)
                    .frame(height: 31)
                    .frame(maxWidth: .infinity)
                    .background {
                        Capsule()
                            .fill(TRGameplayStyle.Colors.successGreen)
                    }
            }
            .padding(.horizontal, 9)
            .padding(.vertical, 10)
            .frame(minHeight: 136)
            .contentShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(action.title), \(action.subtitle), \(action.buttonTitle)"))
        .accessibilityHint(Text("Coming soon."))
    }
}

#Preview("Shop Goodies Strip") {
    TRShopGoodiesStrip(actions: ShopCatalogService().goodieActions, onActionTapped: { _ in })
        .padding(20)
        .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
