import SwiftUI

/// Today's daily route, on the cozy cream card: the challenge, its countdown and
/// the player's streak, and a big Play Daily button. Still a placeholder: the
/// countdown is fixed and the button does nothing yet.
struct TRDailyRoutePlaceholderCard: View {
    let currentStreakDays: Int

    private let primaryBlue = Color(red: 0.05, green: 0.48, blue: 0.95)
    private let titleColor = Color(red: 0.05, green: 0.18, blue: 0.43)
    private let bodyTextColor = Color(red: 0.35, green: 0.43, blue: 0.56)
    private let accentOrange = Color(red: 1.0, green: 0.44, blue: 0.18)

    init(currentStreakDays: Int = 0) {
        self.currentStreakDays = currentStreakDays
    }

    var body: some View {
        VStack(spacing: 14) {
            HStack(alignment: .top, spacing: 14) {
                iconBlock
                textBlock
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            ViewThatFits(in: .horizontal) {
                HStack(spacing: 8) {
                    countdownPill
                    streakPill
                }
                VStack(spacing: 8) {
                    countdownPill
                    streakPill
                }
            }

            Button(action: {}) {
                Label("Play Daily", systemImage: "play.fill")
                    .font(.system(.title3, design: .rounded, weight: .heavy))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                    .frame(maxWidth: .infinity, minHeight: 52)
            }
            .buttonStyle(MultiVanHUDButtonStyle(isProminent: true, shape: AnyShape(Capsule())))
            .frame(maxWidth: 280)
        }
        .padding(18)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 28)
        }
    }

    private var iconBlock: some View {
        let shape = RoundedRectangle(cornerRadius: 20, style: .continuous)
        // The art sits small in the middle of a tall, padded canvas.
        return SpriteImage(name: "star_calendar")
            .scaledToFit()
            .scaleEffect(2.3)
            .offset(y: 4)
            .frame(width: 70, height: 70)
            .clipShape(shape)
            .background {
                shape.fill(LinearGradient(
                    colors: [Color(red: 1.0, green: 0.80, blue: 0.30), Color(red: 1.0, green: 0.56, blue: 0.20)],
                    startPoint: .topLeading, endPoint: .bottomTrailing
                ))
                .overlay(alignment: .top) {
                    shape.fill(LinearGradient(colors: [.white.opacity(0.35), .clear], startPoint: .top, endPoint: .center))
                }
            }
            .background {
                shape.fill(Color(red: 0.85, green: 0.40, blue: 0.10)).offset(y: 4)
            }
            .shadow(color: accentOrange.opacity(0.28), radius: 8, x: 0, y: 6)
            .padding(.bottom, 4)
            .accessibilityHidden(true)
    }

    private var textBlock: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("DAILY ROUTE")
                .font(.system(size: 12, weight: .black, design: .rounded))
                .foregroundStyle(primaryBlue)
                .tracking(1)

            Text("Deliver Happiness")
                .font(.system(size: 22, weight: .black, design: .rounded))
                .foregroundStyle(titleColor)
                .lineLimit(1)
                .minimumScaleFactor(0.74)

            Text("Complete the route in the fewest moves to earn extra stars!")
                .font(.system(size: 14, weight: .medium, design: .rounded))
                .foregroundStyle(bodyTextColor)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var countdownPill: some View {
        Label("New challenge in 09:45:12", systemImage: "clock.fill")
            .font(.system(size: 13, weight: .semibold, design: .rounded))
            .foregroundStyle(Color(red: 0.36, green: 0.43, blue: 0.53))
            .lineLimit(1)
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background { Capsule().fill(Color(red: 0.36, green: 0.43, blue: 0.53).opacity(0.10)) }
    }

    private var streakPill: some View {
        Label(streakTitle, systemImage: "flame.fill")
            .font(.system(size: 13, weight: .bold, design: .rounded))
            .foregroundStyle(accentOrange)
            .lineLimit(1)
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background { Capsule().fill(accentOrange.opacity(0.13)) }
    }

    private var clampedStreakDays: Int {
        max(currentStreakDays, 0)
    }

    private var streakTitle: String {
        let dayLabel = clampedStreakDays == 1 ? "Day" : "Days"
        return "\(clampedStreakDays) \(dayLabel) Streak"
    }
}

#Preview("Daily Route Placeholder") {
    ZStack {
        Color(red: 0.78, green: 0.90, blue: 0.96)
            .ignoresSafeArea()

        TRDailyRoutePlaceholderCard(currentStreakDays: 5)
            .padding(20)
    }
}
