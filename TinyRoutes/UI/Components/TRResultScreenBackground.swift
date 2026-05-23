import SwiftUI

struct TRResultScreenBackground: View {
    var body: some View {
        ZStack {
            SpriteImage(name: "background")
                .scaledToFill()
                .opacity(0.52)
                .blur(radius: 1.2)

            LinearGradient(
                colors: [
                    Color(red: 0.88, green: 0.96, blue: 1.00).opacity(0.86),
                    Color.white.opacity(0.58),
                    Color(red: 0.78, green: 0.93, blue: 0.82).opacity(0.42)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        }
        .ignoresSafeArea()
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

#Preview("Result Background") {
    TRResultScreenBackground()
}
