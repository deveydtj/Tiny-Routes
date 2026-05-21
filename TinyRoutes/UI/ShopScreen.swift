import SwiftUI

/// In-app shop screen placeholder.
struct ShopScreen: View {
    var body: some View {
        VStack(spacing: 12) {
            Spacer()
            Text("Shop")
                .font(.title)
            Text("Shop content coming soon")
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ShopScreen_Previews: PreviewProvider {
    static var previews: some View {
        ShopScreen()
    }
}
