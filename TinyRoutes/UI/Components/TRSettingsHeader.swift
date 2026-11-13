import SwiftUI

/// The settings page's banner, with the way back on its left.
struct TRSettingsHeader: View {
    let onBackTapped: () -> Void

    var body: some View {
        TRCozyMenuBanner(eyebrow: "Tiny Routes", title: "Settings", leading: {
            TRCozyCircleButton(systemName: "chevron.left", label: "Back", action: onBackTapped)
        })
    }
}

#Preview("Settings Header") {
    ZStack(alignment: .top) {
        TRCozySkyBackground()
        TRSettingsHeader(onBackTapped: {})
    }
}
