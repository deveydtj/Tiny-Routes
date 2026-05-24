import SwiftUI

struct TRShopCosmeticGrid: View {
    let options: [ShopCosmeticOption]
    let onOptionTapped: (ShopCosmeticOption) -> Void

    private let columns = [
        GridItem(.flexible(), spacing: 10),
        GridItem(.flexible(), spacing: 10)
    ]

    var body: some View {
        LazyVGrid(columns: columns, spacing: 10) {
            ForEach(options) { option in
                TRShopCosmeticOptionCard(option: option) {
                    onOptionTapped(option)
                }
            }
        }
    }
}

#Preview("Shop Cosmetic Grid") {
    TRShopCosmeticGrid(
        options: ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.routeThemes),
        onOptionTapped: { _ in }
    )
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
