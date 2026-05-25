import XCTest
@testable import TinyRoutes

final class ProfileSummaryServiceTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!
    private var repository: SaveDataRepository!
    private var progressService: ProgressService!
    private var economyService: EconomyService!
    private var cosmeticService: CosmeticService!
    private var summaryService: ProfileSummaryService!

    override func setUp() {
        super.setUp()
        suiteName = "ProfileSummaryServiceTests.\(name)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        repository = SaveDataRepository(userDefaults: defaults)
        progressService = ProgressService(repository: repository)
        economyService = EconomyService(repository: repository)
        cosmeticService = CosmeticService(repository: repository, economyService: economyService)
        summaryService = ProfileSummaryService(
            repository: repository,
            progressService: progressService,
            economyService: economyService,
            cosmeticService: cosmeticService
        )
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        summaryService = nil
        cosmeticService = nil
        economyService = nil
        progressService = nil
        repository = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testTotalStarsAreSummedCorrectly() {
        repository.save(PlayerProfile(bestStarsByLevelID: ["level_001": 3, "level_002": 2, "level_003": 1]))

        XCTAssertEqual(progressService.totalStars(), 6)

        let summary = summaryService.makeSummary()
        XCTAssertEqual(summary.totalStars, 6)
    }

    func testCompletedLevelsCountOnlyLevelsWithMoreThanZeroStars() {
        repository.save(PlayerProfile(bestStarsByLevelID: ["level_001": 3, "level_002": 0, "level_003": 1]))

        XCTAssertEqual(progressService.completedLevelCount(), 2)

        let summary = summaryService.makeSummary()
        XCTAssertEqual(summary.completedLevelCount, 2)
    }

    func testCorruptStarValuesAreClampedInSnapshotAndTotals() {
        repository.save(PlayerProfile(bestStarsByLevelID: ["level_001": 9, "level_002": -4, "level_003": 2]))

        XCTAssertEqual(progressService.bestStarsSnapshot(), ["level_001": 3, "level_002": 0, "level_003": 2])
        XCTAssertEqual(progressService.totalStars(), 5)
        XCTAssertEqual(progressService.completedLevelCount(), 2)
    }

    func testStarCollectorUnlocksAt150Stars() {
        let stars = Dictionary(uniqueKeysWithValues: (1...50).map { ("level_\($0)", 3) })
        repository.save(PlayerProfile(bestStarsByLevelID: stars))

        let summary = summaryService.makeSummary()
        let starCollector = summary.achievements.first { $0.id == "star-collector" }

        XCTAssertEqual(summary.totalStars, 150)
        XCTAssertEqual(starCollector?.isUnlocked, true)
    }

    func testDailyDriverUnlocksWhenBestStreakIsAtLeastSeven() {
        repository.update { profile in
            profile.bestStreakDays = 7
        }

        let summary = summaryService.makeSummary()
        let dailyDriver = summary.achievements.first { $0.id == "daily-driver" }

        XCTAssertEqual(summary.bestStreakDays, 7)
        XCTAssertEqual(dailyDriver?.isUnlocked, true)
    }

    func testSummaryReturnsAchievementsWhenNoProgressExists() {
        let summary = summaryService.makeSummary()

        XCTAssertFalse(summary.achievements.isEmpty)
        XCTAssertEqual(summary.totalStars, 0)
        XCTAssertEqual(summary.completedLevelCount, 0)
        XCTAssertEqual(summary.coinTotal, 0)
    }

    func testSummaryReadsPlayerNameAndCoinTotalFromSavedProfile() {
        repository.update { profile in
            profile.playerName = "Avery"
            profile.coinTotal = 345
        }

        let summary = summaryService.makeSummary()

        XCTAssertEqual(summary.playerName, "Avery")
        XCTAssertEqual(summary.coinTotal, 345)
    }

    func testSummaryReadsFastestTimeFromSavedProfile() {
        repository.update { profile in
            profile.fastestCompletionTimeByLevelID = [
                "level_001": 42,
                "level_002": 18
            ]
        }

        let summary = summaryService.makeSummary()

        XCTAssertEqual(summary.fastestTime, 18)
    }
}
