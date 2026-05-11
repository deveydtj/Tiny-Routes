import SwiftUI

/// Settings screen.
struct SettingsScreen: View {
    let onBackTapped: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text("Settings")
                .font(.title)
            Text("Placeholder content")
            Button("Back", action: onBackTapped)
        }
    }
}

#Preview {
    SettingsScreen(onBackTapped: {})
}
