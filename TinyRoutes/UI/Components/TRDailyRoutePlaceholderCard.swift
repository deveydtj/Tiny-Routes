import SwiftUI

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
        ViewThatFits(in: .horizontal) {
            horizontalLayout
            verticalLayout
        }
        .padding(18)
        .background {
            TRGlassCardBackground()
        }
    }

    private var horizontalLayout: some View {
        HStack(alignment: .center, spacing: 14) {
            iconBlock
            textBlock
                .frame(maxWidth: .infinity, alignment: .leading)
            streakBlock
        }
    }

    private var verticalLayout: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 13) {
                iconBlock
                textBlock
            }

            streakBlock
                .frame(maxWidth: .infinity)
        }
    }

    private var iconBlock: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 1.0, green: 0.82, blue: 0.30),
                            Color(red: 1.0, green: 0.58, blue: 0.24)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            SpriteImage(name: "star_calendar")
                .scaledToFit()
                .padding(10)
        }
        .frame(width: 62, height: 62)
        .shadow(color: accentOrange.opacity(0.22), radius: 8, x: 0, y: 5)
    }

    private var textBlock: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("DAILY ROUTE")
                .font(.system(size: 11, weight: .black, design: .rounded))
                .foregroundStyle(primaryBlue)
                .tracking(0.8)

            Text("Deliver Happiness")
                .font(.system(size: 21, weight: .black, design: .rounded))
                .foregroundStyle(titleColor)
                .lineLimit(1)
                .minimumScaleFactor(0.74)

            Text("Complete the route in the fewest moves to earn extra stars!")
                .font(.system(size: 13, weight: .medium, design: .rounded))
                .foregroundStyle(bodyTextColor)
                .fixedSize(horizontal: false, vertical: true)

            Label("New challenge in 09:45:12", systemImage: "clock.fill")
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .foregroundStyle(Color(red: 0.46, green: 0.53, blue: 0.63))
                .padding(.top, 2)
        }
    }

    private var streakBlock: some View {
        VStack(spacing: 8) {
            Label(streakTitle, systemImage: "flame.fill")
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(accentOrange)
                .lineLimit(1)
                .minimumScaleFactor(0.78)

            HStack(spacing: 4) {
                ForEach(0..<7, id: \.self) { index in
                    Circle()
                        .fill(index < activeStreakDotCount ? accentOrange : Color(red: 0.82, green: 0.87, blue: 0.93))
                        .frame(width: 6, height: 6)
                }
            }

            Button(action: {}) {
                Text("Play Daily")
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                    .padding(.horizontal, 14)
                    .frame(height: 34)
                    .background {
                        Capsule()
                            .fill(primaryBlue)
                    }
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .background {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(red: 0.94, green: 0.97, blue: 1.0))
        }
    }

    private var clampedStreakDays: Int {
        max(currentStreakDays, 0)
    }

    private var activeStreakDotCount: Int {
        min(clampedStreakDays, 7)
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
