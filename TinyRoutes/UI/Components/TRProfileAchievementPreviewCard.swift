import SwiftUI

struct TRProfileAchievementPreviewCard: View {
    let achievements: [ProfileAchievement]
    let onViewAllTapped: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Achievements")
                    .font(.system(size: 22, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)

                Spacer()

                Button(action: onViewAllTapped) {
                    HStack(spacing: 4) {
                        Text("View All")
                        Image(systemName: "chevron.right")
                    }
                    .font(.system(size: 13, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                    .padding(.horizontal, 12)
                    .frame(height: 34)
                    .background {
                        Capsule()
                            .fill(Color(red: 0.91, green: 0.96, blue: 1.00))
                    }
                }
                .buttonStyle(.plain)
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
            TRGlassCardBackground(cornerRadius: 25)
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
                .font(.system(size: 13, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .lineLimit(2)
                .multilineTextAlignment(.center)
                .minimumScaleFactor(0.75)
                .frame(minHeight: 32)

            Text(achievement.subtitle)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .frame(width: 112, height: 142)
        .background {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color(red: 0.94, green: 0.97, blue: 1.00).opacity(0.92))
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
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
