import SwiftUI

struct TRShopRouteThemePreviewCard: View {
    let selectedOption: ShopCosmeticOption

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .center, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Active Theme")
                        .font(.system(size: 11, weight: .black, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                        .textCase(.uppercase)
                        .lineLimit(1)

                    Text(selectedOption.title)
                        .font(.system(size: 24, weight: .black, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                        .lineLimit(1)
                        .minimumScaleFactor(0.70)
                }

                Spacer(minLength: 8)

                if selectedOption.isSelected {
                    HStack(spacing: 5) {
                        Image(systemName: "checkmark")
                            .font(.system(size: 11, weight: .black))
                        Text("Selected")
                            .font(.system(size: 12, weight: .black, design: .rounded))
                    }
                    .foregroundStyle(.white)
                    .padding(.horizontal, 10)
                    .frame(height: 30)
                    .background {
                        Capsule()
                            .fill(TRGameplayStyle.Colors.primaryBlue)
                    }
                    .accessibilityHidden(true)
                }
            }

            TRShopRoutePreviewView(accent: selectedOption.accent)
                .frame(height: 182)

            HStack(spacing: 6) {
                ForEach(0..<3, id: \.self) { index in
                    Capsule()
                        .fill(index == 0 ? TRGameplayStyle.Colors.primaryBlue : Color(red: 0.77, green: 0.84, blue: 0.91))
                        .frame(width: index == 0 ? 22 : 7, height: 7)
                }
            }
            .frame(maxWidth: .infinity)
            .accessibilityHidden(true)
        }
        .padding(18)
        .background {
            TRGlassCardBackground(cornerRadius: 28)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("Active theme, \(selectedOption.title)"))
        .accessibilityValue(Text(selectedOption.isSelected ? "Selected" : "Preview"))
    }
}

#Preview("Shop Theme Preview Card") {
    TRShopRouteThemePreviewCard(
        selectedOption: ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.routeThemes)[1]
    )
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
