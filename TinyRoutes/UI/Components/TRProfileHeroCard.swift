import SwiftUI

struct TRProfileHeroCard: View {
    let summary: TRProfileSummary

    var body: some View {
        ViewThatFits(in: .horizontal) {
            horizontalLayout
            verticalLayout
        }
        .padding(18)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 26)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(summary.playerName), \(summary.rankTitle), \(summary.levelText), \(summary.xpText)"))
    }

    private var horizontalLayout: some View {
        HStack(spacing: 18) {
            identityRow

            TRCozyDivider()
                .frame(height: 74)

            xpBlock
                .frame(width: 132)
        }
    }

    private var verticalLayout: some View {
        VStack(alignment: .leading, spacing: 16) {
            identityRow
            xpBlock
        }
    }

    private var identityRow: some View {
        HStack(spacing: 15) {
            TRProfileAvatarIcon(size: 78)

            VStack(alignment: .leading, spacing: 4) {
                Text(summary.playerName)
                    .font(.system(size: 25, weight: .bold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.navy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.74)

                Text(summary.rankTitle)
                    .font(.system(size: 15, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.teal)
                    .lineLimit(1)

                Text(summary.memberSinceText)
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(TRVillagePalette.slate)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)
            }
        }
    }

    private var xpBlock: some View {
        VStack(alignment: .leading, spacing: 9) {
            TRCozyTag(text: summary.levelText, systemImage: "star.fill", tint: TRVillagePalette.blue)

            Text(summary.xpText)
                .font(.system(size: 12, weight: .medium, design: .rounded))
                .foregroundStyle(TRVillagePalette.slate)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
                .monospacedDigit()

            TRProgressBar(progress: summary.xpProgress, height: 9)
        }
    }
}

#Preview("Profile Hero Card") {
    TRProfileHeroCard(summary: .conceptPreview)
        .padding(20)
        .background(TRVillageSky())
}
