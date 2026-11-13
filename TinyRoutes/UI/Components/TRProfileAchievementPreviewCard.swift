import SwiftUI

struct TRProfileAchievementPreviewCard: View {
    let achievements: [ProfileAchievement]
    let onViewAllTapped: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                TRCozyCardTitle(title: "Achievements")

                Spacer()

                Button(action: onViewAllTapped) {
                    HStack(spacing: 4) {
                        Text("View All")
                        Image(systemName: "chevron.right")
                    }
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.teal)
                    .padding(.horizontal, 12)
                    .frame(height: 32)
                }
                .buttonStyle(MultiVanHUDButtonStyle(shape: AnyShape(Capsule())))
                .accessibilityLabel(Text("View all achievements"))
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(achievements.prefix(4)) { achievement in
                        AchievementTile(achievement: achievement)
                    }
                }
                .padding(.vertical, 2)
            }
        }
        .padding(18)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 26)
        }
    }
}

private struct AchievementTile: View {
    let achievement: ProfileAchievement

    var body: some View {
        VStack(spacing: 8) {
            ZStack(alignment: .topTrailing) {
                TRProfileAchievementIcon(achievement: achievement, size: 56)

                if achievement.isUnlocked {
                    TRProfileCheckBadge(size: 20)
                        .offset(x: 5, y: -5)
                }
            }

            Text(achievement.title)
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(TRVillagePalette.navy)
                .lineLimit(2)
                .multilineTextAlignment(.center)
                .minimumScaleFactor(0.75)
                .frame(minHeight: 32)

            Text(achievement.subtitle)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .foregroundStyle(TRVillagePalette.slate)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .frame(width: 112, height: 142)
        .background {
            TRCozyWellBackground(cornerRadius: 20)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(achievement.title), \(achievement.subtitle), \(achievement.isUnlocked ? "unlocked" : "locked")"))
    }
}

#Preview("Achievement Preview Card") {
    TRProfileAchievementPreviewCard(
        achievements: TRProfileSummary.conceptPreview.achievements,
        onViewAllTapped: {}
    )
    .padding(20)
    .background(TRVillageSky())
}
