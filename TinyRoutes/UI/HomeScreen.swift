import SwiftUI

/// The home / main menu screen.
struct HomeScreen: View {
    let onPlayTapped: () -> Void
    let onDailyRouteTapped: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 24) {
            Spacer(minLength: 40)

            TRTinyRoutesLogo()

            VStack(spacing: 10) {
                TRMenuButton(
                    title: "Play",
                    systemImage: nil,
                    spriteName: "play_filled",
                    variant: .play,
                    size: .primary,
                    action: onPlayTapped
                )

                TRMenuButton(
                    title: "Daily Route",
                    systemImage: nil,
                    spriteName: "star_calendar",
                    variant: .dailyRoute,
                    size: .secondary,
                    action: onDailyRouteTapped ?? {}
                )
                .disabled(onDailyRouteTapped == nil)
                .accessibilityHint(onDailyRouteTapped == nil ? Text("Coming soon") : Text(""))
            }
            .frame(maxWidth: 340)

            Spacer(minLength: 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.horizontal, 16)
    }
}

struct HomeScreen_Previews: PreviewProvider {
    static var previews: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.56, green: 0.80, blue: 0.95),
                    Color(red: 0.86, green: 0.94, blue: 0.78)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            HomeScreen(onPlayTapped: {})
        }
    }
}
