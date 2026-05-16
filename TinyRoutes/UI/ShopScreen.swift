import SwiftUI

/// In-app shop screen placeholder.
struct ShopScreen: View {
    let onBackTapped: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text("Shop")
                .font(.title)
            Text("Placeholder content")
            Button("Back", action: onBackTapped)
        }
    }
}

struct ShopScreen_Previews: PreviewProvider {
    static var previews: some View {
        ShopScreen(onBackTapped: {})
    }
}
