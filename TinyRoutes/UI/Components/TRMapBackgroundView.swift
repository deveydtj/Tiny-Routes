import SwiftUI

struct TRMapBackgroundView: View {
    var body: some View {
        ZStack {
            SpriteImage(name: "background")
                .scaledToFill()
                .opacity(0.30)

            Color(red: 0.92, green: 0.96, blue: 1.0)
                .opacity(0.60)
        }
        .clipped()
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
