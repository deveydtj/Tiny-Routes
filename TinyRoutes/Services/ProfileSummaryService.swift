import Foundation

final class ProfileSummaryService {
    private let repository: SaveDataRepository
    private let progressService: ProgressService
    private let economyService: EconomyService
    private let cosmeticService: CosmeticService
    private let levelRepository: LevelRepository

    init(
        repository: SaveDataRepository = SaveDataRepository(),
        progressService: ProgressService? = nil,
        economyService: EconomyService? = nil,
        cosmeticService: CosmeticService? = nil,
        levelRepository: LevelRepository = LevelRepository()
    ) {
        self.repository = repository
        self.progressService = progressService ?? ProgressService(repository: repository)
        self.economyService = economyService ?? EconomyService(repository: repository)
        self.cosmeticService = cosmeticService ?? CosmeticService(repository: repository, economyService: self.economyService)
        self.levelRepository = levelRepository
    }

    func makeSummary() -> TRProfileSummary {
        _ = levelRepository
        let profile = repository.load()
        let totalStars = progressService.totalStars()
        let completedLevelCount = progressService.completedLevelCount()
        let bestStreakDays = profile.bestStreakDays
        let fastestTime = profile.fastestCompletionTimeByLevelID.values.min()

        // Rank and XP stay concept placeholders until an XP progression system exists.
        let rankTitle = "Route Master"
        let level = 24
        let currentXP = 2_150
        let nextLevelXP = 3_000

        return TRProfileSummary(
            playerName: profile.playerName,
            rankTitle: rankTitle,
            memberSinceText: memberSinceText(for: profile.createdAt),
            level: level,
            currentXP: currentXP,
            nextLevelXP: nextLevelXP,
            totalStars: totalStars,
            completedLevelCount: completedLevelCount,
            bestStreakDays: bestStreakDays,
            fastestTime: fastestTime,
            coinTotal: economyService.coinTotal(),
            achievements: ProfileAchievement.conceptPreviewAchievements(
                totalStars: totalStars,
                bestStreakDays: bestStreakDays,
                fastestTime: fastestTime
            ),
            collectionSelections: cosmeticService.selectedCollectionSelections(),
            rewardProgress: TRProfileRewardProgress(
                title: "Star Collector",
                subtitle: "Collect 150 stars to earn a reward!",
                currentValue: totalStars,
                targetValue: 150,
                rewardCoins: 250
            )
        )
    }

    private func memberSinceText(for date: Date) -> String {
        let year = Calendar.current.component(.year, from: date)
        return "Member since \(year)"
    }
}
