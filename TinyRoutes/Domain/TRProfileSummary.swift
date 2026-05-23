import CoreGraphics
import Foundation

struct TRProfileSummary: Equatable {
    let playerName: String
    let rankTitle: String
    let memberSinceText: String
    let level: Int
    let currentXP: Int
    let nextLevelXP: Int
    let totalStars: Int
    let completedLevelCount: Int
    let bestStreakDays: Int
    let fastestTime: TimeInterval?
    let coinTotal: Int
    let achievements: [ProfileAchievement]
    let collectionSelections: [ProfileCollectionSelection]
    let rewardProgress: TRProfileRewardProgress

    var xpProgress: CGFloat {
        guard nextLevelXP > 0 else { return 0 }
        return CGFloat(currentXP).clamped(to: 0...CGFloat(nextLevelXP)) / CGFloat(nextLevelXP)
    }

    var fastestTimeText: String {
        guard let fastestTime else { return "--:--" }
        let wholeSeconds = max(Int(fastestTime.rounded(.down)), 0)
        let minutes = wholeSeconds / 60
        let seconds = wholeSeconds % 60
        return "\(String(format: "%02d", minutes)):\(String(format: "%02d", seconds))"
    }

    var levelText: String {
        "Level \(level)"
    }

    var xpText: String {
        "\(currentXP.formatted(.number.grouping(.automatic))) / \(nextLevelXP.formatted(.number.grouping(.automatic))) XP"
    }

    static let conceptPreview = TRProfileSummary(
        playerName: "Player One",
        rankTitle: "Route Master",
        memberSinceText: "Member since 2026",
        level: 24,
        currentXP: 2_150,
        nextLevelXP: 3_000,
        totalStars: 128,
        completedLevelCount: 42,
        bestStreakDays: 7,
        fastestTime: 48,
        coinTotal: 1_250,
        achievements: ProfileAchievement.conceptPreviewAchievements(
            totalStars: 128,
            bestStreakDays: 7,
            fastestTime: 48
        ),
        collectionSelections: ProfileCollectionSelection.conceptDefaults,
        rewardProgress: TRProfileRewardProgress(
            title: "Star Collector",
            subtitle: "Collect 150 stars to earn a reward!",
            currentValue: 128,
            targetValue: 150,
            rewardCoins: 250
        )
    )

    static let emptyPreview = TRProfileSummary(
        playerName: "Player One",
        rankTitle: "New Driver",
        memberSinceText: "Member since 2026",
        level: 1,
        currentXP: 0,
        nextLevelXP: 500,
        totalStars: 0,
        completedLevelCount: 0,
        bestStreakDays: 0,
        fastestTime: nil,
        coinTotal: 1_250,
        achievements: ProfileAchievement.conceptPreviewAchievements(
            totalStars: 0,
            bestStreakDays: 0,
            fastestTime: nil,
            perfectRoutesUnlocked: false
        ),
        collectionSelections: ProfileCollectionSelection.conceptDefaults,
        rewardProgress: TRProfileRewardProgress(
            title: "Star Collector",
            subtitle: "Collect 150 stars to earn a reward!",
            currentValue: 0,
            targetValue: 150,
            rewardCoins: 250
        )
    )
}

struct TRProfileRewardProgress: Equatable {
    let title: String
    let subtitle: String
    let currentValue: Int
    let targetValue: Int
    let rewardCoins: Int

    var progress: CGFloat {
        guard targetValue > 0 else { return 0 }
        return CGFloat(currentValue).clamped(to: 0...CGFloat(targetValue)) / CGFloat(targetValue)
    }

    var progressText: String {
        "\(currentValue) / \(targetValue)"
    }
}

private extension CGFloat {
    func clamped(to range: ClosedRange<CGFloat>) -> CGFloat {
        Swift.min(Swift.max(self, range.lowerBound), range.upperBound)
    }
}
