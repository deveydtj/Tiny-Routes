import SwiftUI

/// The cosmetic categories as a row of cream pills, the chosen one teal.
struct TRShopCategoryPillBar: View {
    let categories: [ShopCosmeticCategory]
    let selectedCategoryID: String
    let onCategorySelected: (String) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(categories) { category in
                    categoryButton(category)
                }
            }
            // Room for the pills' lips and shadows.
            .padding(.horizontal, 4)
            .padding(.top, 2)
            .padding(.bottom, 8)
        }
        .padding(.horizontal, -4)
        .accessibilityElement(children: .contain)
    }

    private func categoryButton(_ category: ShopCosmeticCategory) -> some View {
        let isSelected = category.id == selectedCategoryID

        return Button {
            onCategorySelected(category.id)
        } label: {
            HStack(spacing: 6) {
                Image(systemName: category.systemImage)
                    .font(.system(size: 13, weight: .semibold))
                    .accessibilityHidden(true)

                Text(category.title)
                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                    .lineLimit(1)
            }
            .foregroundStyle(isSelected ? TRVillagePalette.cream : TRVillagePalette.navy)
            .padding(.horizontal, 14)
            .frame(height: 38)
            .background {
                Capsule()
                    .fill(isSelected
                        ? AnyShapeStyle(TRVillagePalette.teal)
                        : AnyShapeStyle(LinearGradient(colors: [TRVillagePalette.cream, TRVillagePalette.creamDeep], startPoint: .top, endPoint: .bottom)))
                    .overlay { Capsule().strokeBorder(.white.opacity(isSelected ? 0.25 : 0.9), lineWidth: 1) }
                    .background {
                        Capsule()
                            .fill(isSelected ? TRVillagePalette.tealDark : TRVillagePalette.creamLip)
                            .offset(y: 3)
                    }
                    .shadow(color: MultiVanHUDStyle.shadow.opacity(0.14), radius: 5, x: 0, y: 4)
            }
            .contentShape(Capsule())
        }
        .buttonStyle(TRVillagePressStyle())
        .accessibilityLabel(Text(category.title))
        .accessibilityValue(Text(isSelected ? "Selected" : "Not selected"))
        .accessibilityAddTraits(isSelected ? [.isSelected] : [])
    }
}

#Preview("Shop Category Pill Bar") {
    let service = ShopCatalogService()

    return TRShopCategoryPillBar(
        categories: service.categories,
        selectedCategoryID: ShopCosmeticCategoryID.routeThemes,
        onCategorySelected: { _ in }
    )
    .padding(20)
    .background(TRVillageSky())
}
