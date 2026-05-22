import SwiftUI

struct TRMilestoneRewardsPlaceholderCard: View {
    private let primaryBlue = Color(red: 0.05, green: 0.48, blue: 0.95)
    private let successGreen = Color(red: 0.16, green: 0.72, blue: 0.60)
    private let titleColor = Color(red: 0.05, green: 0.18, blue: 0.43)
    private let mutedTextColor = Color(red: 0.40, green: 0.49, blue: 0.62)
    private let milestones = [10, 25, 50, 75]

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("MILESTONE REWARDS")
                .font(.system(size: 12, weight: .black, design: .rounded))
                .foregroundStyle(primaryBlue)
                .tracking(0.8)

            ZStack {
                GeometryReader { geometry in
                    Path { path in
                        let y = geometry.size.height * 0.33
                        path.move(to: CGPoint(x: 28, y: y))
                        path.addLine(to: CGPoint(x: geometry.size.width - 28, y: y))
                    }
                    .stroke(
                        Color(red: 0.72, green: 0.79, blue: 0.88),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round, dash: [4, 7])
                    )
                }
                .allowsHitTesting(false)

                HStack(alignment: .top, spacing: 0) {
                    ForEach(Array(milestones.enumerated()), id: \.element) { index, milestone in
                        milestoneNode(levelCount: milestone, isCompleted: index == 0)
                            .frame(maxWidth: .infinity)
                    }
                }
            }
            .frame(height: 76)
        }
        .padding(18)
        .background {
            TRGlassCardBackground()
        }
    }

    private func milestoneNode(levelCount: Int, isCompleted: Bool) -> some View {
        VStack(spacing: 7) {
            ZStack {
                Circle()
                    .fill(isCompleted ? successGreen : Color(red: 0.94, green: 0.97, blue: 1.0))
                    .frame(width: 42, height: 42)
                    .overlay {
                        Circle()
                            .stroke(.white, lineWidth: 4)
                    }
                    .shadow(color: .black.opacity(0.08), radius: 6, x: 0, y: 3)

                Image(systemName: isCompleted ? "checkmark" : "gift.fill")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(isCompleted ? .white : primaryBlue)
            }

            Text("\(levelCount) Levels")
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundStyle(isCompleted ? titleColor : mutedTextColor)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
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
