import SwiftUI

struct TRMenuTitleLogo: View {
    let pageTitle: String
    let subtitleOverride: String?

    init(pageTitle: String, subtitleOverride: String? = nil) {
        self.pageTitle = pageTitle
        self.subtitleOverride = subtitleOverride
    }

    var body: some View {
        TRTinyRoutesLogo(
            subtitle: subtitleOverride ?? pageTitle,
            size: .large,
            showsPin: false
        )
        .frame(maxWidth: .infinity)
        .accessibilityAddTraits(.isHeader)
    }
}

#Preview("Menu Title Logo Variants") {
    VStack(spacing: 28) {
        TRMenuTitleLogo(pageTitle: "Levels")
        TRMenuTitleLogo(pageTitle: "Shop", subtitleOverride: "Customize your journey")
        TRMenuTitleLogo(pageTitle: "Profile")
    }
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
