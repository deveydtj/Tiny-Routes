import XCTest
@testable import TinyRoutes

final class EconomyServiceTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!
    private var repository: SaveDataRepository!
    private var service: EconomyService!

    override func setUp() {
        super.setUp()
        suiteName = "EconomyServiceTests.\(name)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        repository = SaveDataRepository(userDefaults: defaults)
        service = EconomyService(repository: repository)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        service = nil
        repository = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testDefaultCoinTotalIsZero() {
        XCTAssertEqual(service.coinTotal(), 0)
    }

    func testAddCoinsIncreasesBalanceAndLifetimeEarned() {
        XCTAssertEqual(service.addCoins(150, reason: .debug), 150)

        let profile = repository.load()
        XCTAssertEqual(profile.coinTotal, 150)
        XCTAssertEqual(profile.lifetimeCoinsEarned, 150)
        XCTAssertEqual(profile.lifetimeCoinsSpent, 0)
    }

    func testSpendCoinsDecreasesBalanceAndIncreasesLifetimeSpent() {
        service.addCoins(200, reason: .debug)

        XCTAssertTrue(service.spendCoins(75, reason: .cosmeticUnlock(cosmeticID: "themeForestPath")))

        let profile = repository.load()
        XCTAssertEqual(profile.coinTotal, 125)
        XCTAssertEqual(profile.lifetimeCoinsEarned, 200)
        XCTAssertEqual(profile.lifetimeCoinsSpent, 75)
    }

    func testSpendCoinsFailsWhenBalanceIsTooLow() {
        service.addCoins(50, reason: .debug)

        XCTAssertFalse(service.spendCoins(75, reason: .debug))
        XCTAssertEqual(repository.load().coinTotal, 50)
        XCTAssertEqual(repository.load().lifetimeCoinsSpent, 0)
    }

    func testZeroAndNegativeAmountsDoNotChangeBalance() {
        XCTAssertEqual(service.addCoins(0, reason: .debug), 0)
        XCTAssertEqual(service.addCoins(-10, reason: .debug), 0)
        XCTAssertFalse(service.spendCoins(0, reason: .debug))
        XCTAssertFalse(service.spendCoins(-10, reason: .debug))
        XCTAssertEqual(repository.load().coinTotal, 0)
    }

    func testFirstWinPaysForEveryStar() {
        let reward = service.awardLevelCompletionReward(levelID: "level_001", earnedStars: 3, previousBestStars: 0)

        XCTAssertEqual(reward, 150)
        XCTAssertEqual(service.coinTotal(), 150)
        XCTAssertEqual(repository.load().lifetimeCoinsEarned, 150)
    }

    func testReplayPaysOnlyForTheStarsItAdds() {
        XCTAssertEqual(service.awardLevelCompletionReward(levelID: "level_001", earnedStars: 1, previousBestStars: 0), 50)
        // Better: the difference. The same or worse: nothing.
        XCTAssertEqual(service.previewLevelCompletionReward(levelID: "level_001", earnedStars: 3, previousBestStars: 1), 100)
        XCTAssertEqual(service.awardLevelCompletionReward(levelID: "level_001", earnedStars: 3, previousBestStars: 1), 100)
        XCTAssertEqual(service.awardLevelCompletionReward(levelID: "level_001", earnedStars: 3, previousBestStars: 3), 0)
        XCTAssertEqual(service.awardLevelCompletionReward(levelID: "level_001", earnedStars: 2, previousBestStars: 3), 0)
        XCTAssertEqual(service.coinTotal(), 150)
    }

    func testRewardFollowsTheProgressServiceAcrossReplays() {
        let progress = ProgressService(repository: repository)
        var paid: [Int] = []
        for stars in [1, 1, 2, 3, 3] {
            let update = progress.completeLevel(levelID: "level_002", earnedStars: stars, nextLevelID: nil)
            paid.append(service.awardLevelCompletionReward(
                levelID: "level_002", earnedStars: stars, previousBestStars: update.previousBestStars
            ))
        }
        XCTAssertEqual(paid, [50, 0, 50, 50, 0])
        // A level can never pay more than three stars' worth.
        XCTAssertEqual(service.coinTotal(), 3 * EconomyService.coinsPerStar)
    }

    func testRewardIgnoresStarsOutOfRangeAndNamelessLevels() {
        XCTAssertEqual(service.awardLevelCompletionReward(levelID: "level_001", earnedStars: 9, previousBestStars: -4), 150)
        XCTAssertEqual(service.awardLevelCompletionReward(levelID: "", earnedStars: 3, previousBestStars: 0), 0)
        XCTAssertEqual(service.coinTotal(), 150)
    }
}
