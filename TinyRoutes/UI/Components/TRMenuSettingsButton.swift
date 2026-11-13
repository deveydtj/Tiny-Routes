import SwiftUI

/// The round cream gear in a cozy menu's banner.
struct TRMenuSettingsButton: View {
    let action: () -> Void

    var body: some View {
        TRCozyCircleButton(systemName: "gearshape", label: "Settings", action: action)
    }
}

#Preview("Menu Settings Button") {
    TRMenuSettingsButton(action: {})
        .padding(20)
        .background(TRVillagePalette.teal)
}
