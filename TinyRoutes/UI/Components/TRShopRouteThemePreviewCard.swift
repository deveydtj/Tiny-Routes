import SwiftUI

/// The cosmetic in use, tried out large on a real board.
struct TRShopRouteThemePreviewCard: View {
    let selectedOption: ShopCosmeticOption
    /// Everything else the player has on, so the preview is their own table.
    var cosmetics = MultiVanCosmetics.standard

    private var isConfetti: Bool { selectedOption.categoryID == ShopCosmeticCategoryID.confetti }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 10) {
                VStack(alignment: .leading, spacing: 2) {
                    Text((isConfetti ? "Win Confetti" : "On Your Table").uppercased())
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .tracking(1)
                        .foregroundStyle(TRVillagePalette.teal)
                        .lineLimit(1)

                    Text(selectedOption.title)
                        .font(.system(size: 23, weight: .bold, design: .rounded))
                        .foregroundStyle(TRVillagePalette.navy)
                        .lineLimit(1)
                        .minimumScaleFactor(0.70)
                }

                Spacer(minLength: 8)

                if selectedOption.isSelected {
                    TRCozyTag(text: "In Use", systemImage: "checkmark", tint: TRVillagePalette.blue)
                        .accessibilityHidden(true)
                }
            }

            TRShopBoardPreview(cosmetics: cosmetics.trying(selectedOption), showsConfetti: isConfetti)
                .frame(height: 230)
        }
        .padding(16)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 26)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(isConfetti ? "Win confetti" : "Table theme"), \(selectedOption.title), shown on a board"))
        .accessibilityValue(Text(selectedOption.isSelected ? "Selected" : "Preview"))
    }
}

#Preview("Shop Theme Preview Card") {
    TRShopRouteThemePreviewCard(
        selectedOption: ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.routeThemes)[1]
    )
    .padding(20)
    .background(TRVillageSky())
}
