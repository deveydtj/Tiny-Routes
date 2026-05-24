import SwiftUI

struct TRShopSectionHeader: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.system(size: 25, weight: .black, design: .rounded))
            .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
            .lineLimit(1)
            .minimumScaleFactor(0.82)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityAddTraits(.isHeader)
    }
}

#Preview("Shop Section Header") {
    TRShopSectionHeader(title: "Featured")
        .padding(20)
        .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
