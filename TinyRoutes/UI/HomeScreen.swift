import SwiftUI

/// The home / main menu screen.
struct HomeScreen: View {
    let onPlayTapped: () -> Void
    let onDailyRouteTapped: (() -> Void)? = nil
    let onShopTapped: () -> Void
    let onSettingsTapped: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Spacer(minLength: 40)

            Text("Tiny Routes")
                .font(.system(size: 44, weight: .heavy, design: .rounded))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.22), radius: 4, x: 0, y: 3)

            VStack(spacing: 14) {
                TRMenuButton(
                    title: "Play",
                    systemImage: "play.fill",
                    variant: .play,
                    size: .primary,
                    action: onPlayTapped
                )

                TRMenuButton(
                    title: "Daily Route",
                    systemImage: "calendar",
                    variant: .dailyRoute,
                    size: .secondary,
                    action: onDailyRouteTapped ?? {}
                )
                .disabled(onDailyRouteTapped == nil)
                .accessibilityHint(onDailyRouteTapped == nil ? Text("Coming soon") : Text(""))

                TRMenuButton(
                    title: "Shop",
                    systemImage: "bag.fill",
                    variant: .shop,
                    size: .secondary,
                    action: onShopTapped
                )

                TRMenuButton(
                    title: "Settings",
                    systemImage: "gearshape.fill",
                    variant: .settings,
                    size: .secondary,
                    action: onSettingsTapped
                )
            }
            .frame(maxWidth: 414)

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

            HomeScreen(onPlayTapped: {}, onShopTapped: {}, onSettingsTapped: {})
        }
    }
}
