import SwiftUI

struct TRResultInfoBanner: View {
    enum Kind {
        case streak
        case failure
    }

    let kind: Kind
    let systemImage: String
    let title: String
    let bodyText: String
    let progressCount: Int
    let activeProgressCount: Int
    let coinBonus: Int?
    let encouragementText: String?

    var body: some View {
        HStack(spacing: 12) {
            iconView

            VStack(alignment: .leading, spacing: 5) {
                Text(title)
                    .font(.system(size: 17, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)

                Text(bodyText)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                    .lineLimit(2)
                    .minimumScaleFactor(0.78)

                if kind == .streak {
                    progressDots
                }
            }
            .layoutPriority(1)

            trailingContent
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 13)
        .background {
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(backgroundFill)
                .overlay {
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .stroke(.white.opacity(0.76), lineWidth: 1)
                }
        }
        .accessibilityElement(children: .combine)
    }

    private var iconView: some View {
        ZStack {
            Circle()
                .fill(iconBackground)
                .frame(width: 42, height: 42)

            Image(systemName: systemImage)
                .font(.system(size: 20, weight: .black, design: .rounded))
                .foregroundStyle(iconForeground)
        }
        .accessibilityHidden(true)
    }

    private var progressDots: some View {
        HStack(spacing: 4) {
            ForEach(0..<max(progressCount, 0), id: \.self) { index in
                Circle()
                    .fill(index < activeProgressCount ? TRGameplayStyle.Colors.resultWarningOrange : Color.white.opacity(0.78))
                    .frame(width: 7, height: 7)
                    .overlay {
                        Circle()
                            .stroke(TRGameplayStyle.Colors.resultWarningOrange.opacity(0.24), lineWidth: 1)
                    }
            }
        }
        .accessibilityHidden(true)
    }

    @ViewBuilder
    private var trailingContent: some View {
        if let coinBonus {
            VStack(spacing: 2) {
                Text("Bonus")
                    .font(.system(size: 10, weight: .heavy, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)

                HStack(spacing: 3) {
                    SpriteImage(name: "gold_coin")
                        .scaledToFit()
                        .frame(width: 16, height: 16)

                    Text("\(coinBonus)")
                        .font(.system(size: 15, weight: .black, design: .rounded))
                        .monospacedDigit()
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background {
                Capsule()
                    .fill(.white.opacity(0.78))
            }
        } else if let encouragementText {
            Text(encouragementText)
                .font(.system(size: 11, weight: .heavy, design: .rounded))
                .foregroundStyle(kind == .failure ? TRGameplayStyle.Colors.resultFailureRed : TRGameplayStyle.Colors.successGreen)
                .multilineTextAlignment(.trailing)
                .lineLimit(3)
                .minimumScaleFactor(0.70)
                .frame(maxWidth: 96, alignment: .trailing)
        }
    }

    private var backgroundFill: LinearGradient {
        switch kind {
        case .streak:
            return LinearGradient(
                colors: [
                    TRGameplayStyle.Colors.resultSoftYellow.opacity(0.62),
                    Color(red: 1.00, green: 0.84, blue: 0.47).opacity(0.34)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        case .failure:
            return LinearGradient(
                colors: [
                    Color(red: 1.00, green: 0.91, blue: 0.86).opacity(0.76),
                    Color(red: 0.95, green: 0.98, blue: 1.00).opacity(0.82)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
    }

    private var iconBackground: Color {
        switch kind {
        case .streak:
            return .white.opacity(0.82)
        case .failure:
            return .white.opacity(0.86)
        }
    }

    private var iconForeground: Color {
        switch kind {
        case .streak:
            return TRGameplayStyle.Colors.resultWarningOrange
        case .failure:
            return TRGameplayStyle.Colors.resultFailureRed
        }
    }
}

#Preview("Result Banners") {
    VStack(spacing: 16) {
        TRResultInfoBanner(
            kind: .streak,
            systemImage: "flame.fill",
            title: "7 Day Streak!",
            bodyText: "Keep it going!",
            progressCount: 7,
            activeProgressCount: 7,
            coinBonus: 50,
            encouragementText: nil
        )
        TRResultInfoBanner(
            kind: .failure,
            systemImage: "timer",
            title: "Out of time",
            bodyText: "You ran out of time before delivering the package.",
            progressCount: 0,
            activeProgressCount: 0,
            coinBonus: nil,
            encouragementText: "You're close! Try a different route."
        )
    }
    .padding()
    .background(Color(red: 0.88, green: 0.95, blue: 1.0))
}
