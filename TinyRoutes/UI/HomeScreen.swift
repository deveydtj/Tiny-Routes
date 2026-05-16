import SwiftUI

/// The home / main menu screen.
struct HomeScreen: View {
    let onPlayTapped: () -> Void
    let onShopTapped: () -> Void
    let onSettingsTapped: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text("Tiny Routes")
                .font(.largeTitle)

            Button("Play", action: onPlayTapped)
            Button("Shop", action: onShopTapped)
            Button("Settings", action: onSettingsTapped)
        }
    }
}

struct HomeScreen_Previews: PreviewProvider {
    static var previews: some View {
        HomeScreen(onPlayTapped: {}, onShopTapped: {}, onSettingsTapped: {})
    }
}
