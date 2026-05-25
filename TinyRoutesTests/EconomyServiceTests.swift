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

    func testLevelCompletionRewardPaysOnlyFirstCompletion() {
        let firstReward = service.awardLevelCompletionReward(
            levelID: "level_001",
            earnedStars: 3,
            isFirstCompletion: true
        )
        let duplicateReward = service.awardLevelCompletionReward(
            levelID: "level_001",
            earnedStars: 3,
            isFirstCompletion: true
        )

        XCTAssertEqual(firstReward, 150)
        XCTAssertEqual(duplicateReward, 0)
        XCTAssertEqual(service.coinTotal(), 150)
    }

    func testLevelCompletionRewardDoesNotPayForReplay() {
        let reward = service.awardLevelCompletionReward(
            levelID: "level_001",
            earnedStars: 3,
            isFirstCompletion: false
        )

        XCTAssertEqual(reward, 0)
        XCTAssertEqual(service.coinTotal(), 0)
    }
}
