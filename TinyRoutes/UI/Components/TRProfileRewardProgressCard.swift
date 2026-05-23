import SwiftUI

struct TRProfileRewardProgressCard: View {
    let rewardProgress: TRProfileRewardProgress

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 14) {
                mainContent
                rewardTile
            }

            VStack(alignment: .leading, spacing: 14) {
                mainContent
                rewardTile
            }
        }
        .padding(18)
        .background {
            TRGlassCardBackground(cornerRadius: 25)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(rewardProgress.title), \(rewardProgress.progressText), reward \(rewardProgress.rewardCoins) coins"))
    }

    private var mainContent: some View {
        HStack(spacing: 14) {
            TRProfileStatIcon(systemImage: "trophy.fill", color: TRGameplayStyle.Colors.resultGold, size: 58)

            VStack(alignment: .leading, spacing: 7) {
                Text(rewardProgress.title)
                    .font(.system(size: 20, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)

                Text(rewardProgress.subtitle)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                    .lineLimit(2)
                    .minimumScaleFactor(0.76)

                TRProgressBar(
                    progress: rewardProgress.progress,
                    height: 9,
                    fillColor: TRGameplayStyle.Colors.successGreen
                )

                Text(rewardProgress.progressText)
                    .font(.system(size: 12, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                    .monospacedDigit()
            }
        }
    }

    private var rewardTile: some View {
        VStack(spacing: 5) {
            TRProfileRewardChestIcon(size: 48)

            HStack(spacing: 3) {
                SpriteImage(name: "gold_coin")
                    .scaledToFit()
                    .frame(width: 18, height: 18)

                Text("\(rewardProgress.rewardCoins)")
                    .font(.system(size: 15, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .monospacedDigit()
            }
        }
        .frame(width: 78, height: 94)
        .background {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color(red: 0.94, green: 0.97, blue: 1.00).opacity(0.95))
        }
    }
}

#Preview("Reward Progress Card") {
    VStack {
        TRProfileRewardProgressCard(rewardProgress: TRProfileSummary.conceptPreview.rewardProgress)
        TRProfileRewardProgressCard(rewardProgress: TRProfileSummary.emptyPreview.rewardProgress)
    }
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
