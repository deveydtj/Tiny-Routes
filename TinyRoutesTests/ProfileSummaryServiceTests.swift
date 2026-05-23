import XCTest
@testable import TinyRoutes

final class ProfileSummaryServiceTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        suiteName = "ProfileSummaryServiceTests.\(name)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testTotalStarsAreSummedCorrectly() {
        defaults.set(["level_001": 3, "level_002": 2, "level_003": 1], forKey: "bestStarsByLevelID")
        let progressService = ProgressService(userDefaults: defaults)

        XCTAssertEqual(progressService.totalStars(), 6)

        let summary = ProfileSummaryService(progressService: progressService).makeSummary()
        XCTAssertEqual(summary.totalStars, 6)
    }

    func testCompletedLevelsCountOnlyLevelsWithMoreThanZeroStars() {
        defaults.set(["level_001": 3, "level_002": 0, "level_003": 1], forKey: "bestStarsByLevelID")
        let progressService = ProgressService(userDefaults: defaults)

        XCTAssertEqual(progressService.completedLevelCount(), 2)

        let summary = ProfileSummaryService(progressService: progressService).makeSummary()
        XCTAssertEqual(summary.completedLevelCount, 2)
    }

    func testCorruptStarValuesAreClampedInSnapshotAndTotals() {
        defaults.set(["level_001": 9, "level_002": -4, "level_003": 2], forKey: "bestStarsByLevelID")
        let progressService = ProgressService(userDefaults: defaults)

        XCTAssertEqual(progressService.bestStarsSnapshot(), ["level_001": 3, "level_002": 0, "level_003": 2])
        XCTAssertEqual(progressService.totalStars(), 5)
        XCTAssertEqual(progressService.completedLevelCount(), 2)
    }

    func testStarCollectorUnlocksAt150Stars() {
        let stars = Dictionary(uniqueKeysWithValues: (1...50).map { ("level_\($0)", 3) })
        defaults.set(stars, forKey: "bestStarsByLevelID")

        let summary = ProfileSummaryService(progressService: ProgressService(userDefaults: defaults)).makeSummary()
        let starCollector = summary.achievements.first { $0.id == "star-collector" }

        XCTAssertEqual(summary.totalStars, 150)
        XCTAssertEqual(starCollector?.isUnlocked, true)
    }

    func testDailyDriverUnlocksWhenBestStreakIsAtLeastSeven() {
        let summary = ProfileSummaryService(progressService: ProgressService(userDefaults: defaults)).makeSummary()
        let dailyDriver = summary.achievements.first { $0.id == "daily-driver" }

        XCTAssertEqual(summary.bestStreakDays, 7)
        XCTAssertEqual(dailyDriver?.isUnlocked, true)
    }

    func testSummaryReturnsAchievementsWhenNoProgressExists() {
        let summary = ProfileSummaryService(progressService: ProgressService(userDefaults: defaults)).makeSummary()

        XCTAssertFalse(summary.achievements.isEmpty)
        XCTAssertEqual(summary.totalStars, 0)
        XCTAssertEqual(summary.completedLevelCount, 0)
    }
}
