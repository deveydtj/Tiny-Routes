import SwiftUI

/// Settings screen.
struct SettingsScreen: View {
    var body: some View {
        VStack(spacing: 12) {
            Spacer()
            Text("Profile")
                .font(.title)
            Text("Profile and settings coming soon")
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct SettingsScreen_Previews: PreviewProvider {
    static var previews: some View {
        SettingsScreen()
    }
}
