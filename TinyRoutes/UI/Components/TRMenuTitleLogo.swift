import SwiftUI

/// A cozy menu's title in its banner: the page's name in cream lettering under a
/// mint eyebrow, as the level map names its chapter.
struct TRMenuTitleLogo: View {
    let pageTitle: String
    let subtitleOverride: String?

    init(pageTitle: String, subtitleOverride: String? = nil) {
        self.pageTitle = pageTitle
        self.subtitleOverride = subtitleOverride
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 1) {
            Text((subtitleOverride ?? "Tiny Routes").uppercased())
                .font(.system(size: 12, weight: .medium, design: .rounded))
                .tracking(1)
                .foregroundStyle(TRVillagePalette.mint)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(pageTitle)
                .font(.system(size: 25, weight: .bold, design: .rounded))
                .foregroundStyle(TRVillagePalette.cream)
                .shadow(color: TRVillagePalette.ink.opacity(0.55), radius: 0, x: 0, y: 2)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
    }
}

#Preview("Menu Title Logo Variants") {
    VStack(alignment: .leading, spacing: 20) {
        TRMenuTitleLogo(pageTitle: "Levels")
        TRMenuTitleLogo(pageTitle: "Shop", subtitleOverride: "Customize your journey")
        TRMenuTitleLogo(pageTitle: "Profile")
    }
    .padding(20)
    .background(TRVillagePalette.teal)
}
