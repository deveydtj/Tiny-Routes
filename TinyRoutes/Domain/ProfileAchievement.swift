import Foundation

struct ProfileAchievement: Identifiable, Equatable {
    let id: String
    let title: String
    let subtitle: String
    let systemImage: String
    let accent: ProfileAchievementAccent
    let isUnlocked: Bool

    static func conceptPreviewAchievements(
        totalStars: Int,
        bestStreakDays: Int,
        fastestTime: TimeInterval?,
        perfectRoutesUnlocked: Bool = true
    ) -> [ProfileAchievement] {
        [
            ProfileAchievement(
                id: "star-collector",
                title: "Star Collector",
                subtitle: "150 Stars",
                systemImage: "trophy.fill",
                accent: .gold,
                isUnlocked: totalStars >= 150
            ),
            ProfileAchievement(
                id: "speed-runner",
                title: "Speed Runner",
                subtitle: "Complete in 1:00",
                systemImage: "stopwatch.fill",
                accent: .blue,
                isUnlocked: (fastestTime ?? .infinity) <= 60
            ),
            ProfileAchievement(
                id: "perfect-routes",
                title: "Perfect Routes",
                subtitle: "No mistakes",
                systemImage: "point.topleft.down.curvedto.point.bottomright.up.fill",
                accent: .purple,
                isUnlocked: perfectRoutesUnlocked
            ),
            ProfileAchievement(
                id: "daily-driver",
                title: "Daily Driver",
                subtitle: "7 Day Streak",
                systemImage: "flame.fill",
                accent: .orange,
                isUnlocked: bestStreakDays >= 7
            )
        ]
    }
}

enum ProfileAchievementAccent: String, Equatable {
    case gold
    case blue
    case purple
    case orange
}
