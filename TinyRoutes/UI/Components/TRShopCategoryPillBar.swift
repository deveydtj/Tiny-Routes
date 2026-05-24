import SwiftUI

struct TRShopCategoryPillBar: View {
    let categories: [ShopCosmeticCategory]
    let selectedCategoryID: String
    let onCategorySelected: (String) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(categories) { category in
                    categoryButton(category)
                }
            }
            .padding(.vertical, 2)
        }
        .accessibilityElement(children: .contain)
    }

    private func categoryButton(_ category: ShopCosmeticCategory) -> some View {
        let isSelected = category.id == selectedCategoryID

        return Button {
            onCategorySelected(category.id)
        } label: {
            HStack(spacing: 7) {
                Image(systemName: category.systemImage)
                    .font(.system(size: 13, weight: .black))
                    .accessibilityHidden(true)

                Text(category.title)
                    .font(.system(size: 13, weight: .black, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)

                if isSelected {
                    Image(systemName: "checkmark")
                        .font(.system(size: 11, weight: .black))
                        .accessibilityHidden(true)
                }
            }
            .foregroundStyle(isSelected ? .white : TRGameplayStyle.Colors.titleNavy)
            .padding(.horizontal, 14)
            .frame(height: 42)
            .background {
                Capsule()
                    .fill(isSelected ? TRGameplayStyle.Colors.primaryBlue : .white.opacity(0.88))
                    .overlay {
                        Capsule()
                            .stroke(isSelected ? .white.opacity(0.38) : .white.opacity(0.70), lineWidth: 1)
                    }
                    .shadow(color: .black.opacity(isSelected ? 0.12 : 0.07), radius: 8, x: 0, y: 4)
            }
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
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
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
