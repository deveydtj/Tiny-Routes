import SwiftUI

/// The rewards for clearing 10, 25, 50 and 75 levels, as raised tiles along a
/// dashed road. Still a placeholder: the first is shown as earned.
struct TRMilestoneRewardsPlaceholderCard: View {
    private let primaryBlue = Color(red: 0.05, green: 0.48, blue: 0.95)
    private let titleColor = Color(red: 0.05, green: 0.18, blue: 0.43)
    private let mutedTextColor = Color(red: 0.40, green: 0.49, blue: 0.62)

    private enum Reward: CaseIterable {
        case badge, gift, coins, chest

        var levels: Int {
            switch self {
            case .badge: 10
            case .gift: 25
            case .coins: 50
            case .chest: 75
            }
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("MILESTONE REWARDS")
                .font(.system(size: 12, weight: .black, design: .rounded))
                .foregroundStyle(primaryBlue)
                .tracking(1)

            ZStack(alignment: .top) {
                GeometryReader { geometry in
                    Path { path in
                        let y: CGFloat = 28
                        path.move(to: CGPoint(x: geometry.size.width / 8, y: y))
                        path.addLine(to: CGPoint(x: geometry.size.width * 7 / 8, y: y))
                    }
                    .stroke(
                        MultiVanHUDStyle.creamLip,
                        style: StrokeStyle(lineWidth: 3, lineCap: .round, dash: [5, 7])
                    )
                }
                .allowsHitTesting(false)

                HStack(alignment: .top, spacing: 0) {
                    ForEach(Reward.allCases, id: \.levels) { reward in
                        milestoneNode(reward, isEarned: reward == .badge)
                            .frame(maxWidth: .infinity)
                    }
                }
            }
            .frame(height: 86)
        }
        .padding(18)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 28)
        }
    }

    private func milestoneNode(_ reward: Reward, isEarned: Bool) -> some View {
        VStack(spacing: 8) {
            icon(for: reward, isEarned: isEarned)
                .frame(width: 52, height: 52)
                .background {
                    tileShape.fill(isEarned
                        ? AnyShapeStyle(LinearGradient(colors: [Color(red: 0.30, green: 0.76, blue: 0.44), Color(red: 0.14, green: 0.58, blue: 0.33)], startPoint: .top, endPoint: .bottom))
                        : AnyShapeStyle(LinearGradient(colors: [.white, MultiVanHUDStyle.cream], startPoint: .top, endPoint: .bottom)))
                        .overlay { tileShape.strokeBorder(.white.opacity(0.9), lineWidth: 2) }
                }
                .background {
                    tileShape.fill(isEarned ? Color(red: 0.07, green: 0.40, blue: 0.22) : MultiVanHUDStyle.creamLip).offset(y: 3)
                }
                .shadow(color: MultiVanHUDStyle.shadow.opacity(0.14), radius: 5, x: 0, y: 4)

            Text("\(reward.levels) Levels")
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(isEarned ? titleColor : mutedTextColor)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(reward.levels) levels reward")
        .accessibilityValue(isEarned ? "Earned" : "Not yet earned")
    }

    /// Three gold coins, stacked and overlapping.
    private var coinStack: some View {
        let gold = Color(red: 1.0, green: 0.78, blue: 0.18), deep = Color(red: 0.86, green: 0.56, blue: 0.08)
        return ZStack {
            ForEach(0..<3, id: \.self) { index in
                Ellipse()
                    .fill(gold)
                    .overlay { Ellipse().strokeBorder(deep, lineWidth: 1.5) }
                    .frame(width: 22, height: 9)
                    .background { Ellipse().fill(deep).frame(width: 22, height: 9).offset(y: 2.5) }
                    .offset(x: index == 2 ? 6 : -3, y: index == 2 ? 3 : CGFloat(5 - index * 6))
            }
        }
    }

    private var tileShape: RoundedRectangle {
        RoundedRectangle(cornerRadius: 15, style: .continuous)
    }

    @ViewBuilder
    private func icon(for reward: Reward, isEarned: Bool) -> some View {
        if isEarned {
            Image(systemName: "checkmark")
                .font(.system(size: 22, weight: .black))
                .foregroundStyle(.white)
        } else {
            switch reward {
            case .badge:
                Image(systemName: "rosette")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(primaryBlue)
            case .gift:
                Image(systemName: "gift.fill")
                    .font(.system(size: 24, weight: .bold))
                    .symbolRenderingMode(.palette)
                    .foregroundStyle(Color(red: 1.0, green: 0.78, blue: 0.18), primaryBlue)
            case .coins:
                coinStack
            case .chest:
                Image(systemName: "shippingbox.fill")
                    .font(.system(size: 24, weight: .bold))
                    .symbolRenderingMode(.palette)
                    .foregroundStyle(Color(red: 0.62, green: 0.40, blue: 0.22), Color(red: 1.0, green: 0.78, blue: 0.18))
            }
        }
    }
}

#Preview("Milestone Rewards Placeholder") {
    ZStack {
        Color(red: 0.78, green: 0.90, blue: 0.96)
            .ignoresSafeArea()

        TRMilestoneRewardsPlaceholderCard()
            .padding(20)
    }
}
