import SwiftUI

struct TRProfileRewardProgressCard: View {
    let rewardProgress: TRProfileRewardProgress

    var body: some View {
        // The text wraps to make room for the chest, even on a narrow phone.
        HStack(spacing: 14) {
            mainContent
                .frame(maxWidth: .infinity, alignment: .leading)
            rewardTile
        }
        .padding(18)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 26)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(rewardProgress.title), \(rewardProgress.progressText), reward \(rewardProgress.rewardCoins) coins"))
    }

    private var mainContent: some View {
        HStack(spacing: 14) {
            TRProfileStatIcon(systemImage: "trophy.fill", color: Color(hex: 0xE3A51C), size: 54)

            VStack(alignment: .leading, spacing: 7) {
                Text(rewardProgress.title)
                    .font(.system(size: 19, weight: .bold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.navy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)

                Text(rewardProgress.subtitle)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.slate)
                    .lineLimit(2)
                    .minimumScaleFactor(0.76)

                TRProgressBar(
                    progress: rewardProgress.progress,
                    height: 9,
                    fillColor: MultiVanHUDStyle.pine
                )

                Text(rewardProgress.progressText)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.slate)
                    .monospacedDigit()
            }
        }
    }

    private var rewardTile: some View {
        VStack(spacing: 5) {
            TRProfileRewardChestIcon(size: 48)

            HStack(spacing: 3) {
                TRVillageCoin(size: 15)

                Text("\(rewardProgress.rewardCoins)")
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.navy)
                    .monospacedDigit()
            }
        }
        .frame(width: 78, height: 94)
        .background {
            TRCozyWellBackground(cornerRadius: 20)
        }
    }
}

#Preview("Reward Progress Card") {
    VStack {
        TRProfileRewardProgressCard(rewardProgress: TRProfileSummary.conceptPreview.rewardProgress)
        TRProfileRewardProgressCard(rewardProgress: TRProfileSummary.emptyPreview.rewardProgress)
    }
    .padding(20)
    .background(TRVillageSky())
}
