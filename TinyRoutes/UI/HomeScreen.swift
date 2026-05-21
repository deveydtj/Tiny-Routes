import SwiftUI

/// The home / main menu screen.
struct HomeScreen: View {
    let onPlayTapped: () -> Void
    let onDailyRouteTapped: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 24) {
            Spacer(minLength: 40)

            TinyRoutesLogo()

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

private struct TinyRoutesLogo: View {
    var body: some View {
        VStack(spacing: 5) {
            ZStack(alignment: .topLeading) {
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("Tiny")
                        .foregroundStyle(Color(red: 0.05, green: 0.18, blue: 0.43))

                    Text("Routes")
                        .foregroundStyle(
                            LinearGradient(
                                colors: [
                                    Color(red: 0.10, green: 0.56, blue: 0.97),
                                    Color(red: 0.05, green: 0.42, blue: 0.90)
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                }
                .font(.system(size: 54, weight: .black, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.72)
                .shadow(color: .white.opacity(0.60), radius: 1, x: 0, y: 1)
                .shadow(color: Color(red: 0.12, green: 0.45, blue: 0.82).opacity(0.18), radius: 7, x: 0, y: 5)

                Image(systemName: "mappin.circle.fill")
                    .font(.system(size: 34, weight: .heavy))
                    .symbolRenderingMode(.palette)
                    .foregroundStyle(.white, Color(red: 0.13, green: 0.57, blue: 0.97))
                    .shadow(color: Color(red: 0.04, green: 0.31, blue: 0.72).opacity(0.22), radius: 4, x: 0, y: 3)
                    .offset(x: 90, y: -26)
            }

            Text("One-tap delivery puzzles")
                .font(.system(size: 23, weight: .semibold, design: .rounded))
                .foregroundStyle(Color(red: 0.34, green: 0.40, blue: 0.53))
                .lineLimit(1)
                .minimumScaleFactor(0.82)
        }
        .padding(.top, 14)
        .padding(.bottom, 4)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("Tiny Routes. One-tap delivery puzzles."))
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
