import Foundation

final class ProfileSummaryService {
    private let progressService: ProgressService
    private let levelRepository: LevelRepository

    init(
        progressService: ProgressService = ProgressService(),
        levelRepository: LevelRepository = LevelRepository()
    ) {
        self.progressService = progressService
        self.levelRepository = levelRepository
    }

    func makeSummary() -> TRProfileSummary {
        _ = levelRepository
        let totalStars = progressService.totalStars()
        let completedLevelCount = progressService.completedLevelCount()

        // TODO: Replace placeholder profile, economy, streak, timing, and cosmetic values
        // with SaveDataRepository, EconomyService, StreakService, ProgressService history,
        // and CosmeticService once those services persist real player data.
        let playerName = "Player One"
        let rankTitle = "Route Master"
        let memberSinceText = "Member since 2026"
        let level = 24
        let currentXP = 2_150
        let nextLevelXP = 3_000
        let bestStreakDays = 7
        let fastestTime: TimeInterval = 48
        let coinTotal = 1_250

        return TRProfileSummary(
            playerName: playerName,
            rankTitle: rankTitle,
            memberSinceText: memberSinceText,
            level: level,
            currentXP: currentXP,
            nextLevelXP: nextLevelXP,
            totalStars: totalStars,
            completedLevelCount: completedLevelCount,
            bestStreakDays: bestStreakDays,
            fastestTime: fastestTime,
            coinTotal: coinTotal,
            achievements: ProfileAchievement.conceptPreviewAchievements(
                totalStars: totalStars,
                bestStreakDays: bestStreakDays,
                fastestTime: fastestTime
            ),
            collectionSelections: ProfileCollectionSelection.conceptDefaults,
            rewardProgress: TRProfileRewardProgress(
                title: "Star Collector",
                subtitle: "Collect 150 stars to earn a reward!",
                currentValue: totalStars,
                targetValue: 150,
                rewardCoins: 250
            )
        )
    }
}
