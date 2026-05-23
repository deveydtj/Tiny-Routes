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
            TRGlassCardBackground(cornerRadius: 28)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(summary.playerName), \(summary.rankTitle), \(summary.levelText), \(summary.xpText)"))
    }

    private var horizontalLayout: some View {
        HStack(spacing: 18) {
            identityRow

            Divider()
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
                    .font(.system(size: 26, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.74)

                Text(summary.rankTitle)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                    .lineLimit(1)

                Text(summary.memberSinceText)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)
            }
        }
    }

    private var xpBlock: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text(summary.levelText)
                .font(.system(size: 13, weight: .black, design: .rounded))
                .foregroundStyle(.white)
                .padding(.horizontal, 12)
                .frame(height: 30)
                .background {
                    Capsule()
                        .fill(TRGameplayStyle.Colors.primaryBlue)
                }

            Text(summary.xpText)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
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
        .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
