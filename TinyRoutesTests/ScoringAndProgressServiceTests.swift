import XCTest
@testable import TinyRoutes

final class ScoringAndProgressServiceTests: XCTestCase {
    func testScoringAwardsZeroStarsWhenAttemptFails() {
        let service = ScoringService()

        let stars = service.stars(
            didComplete: false,
            elapsedTime: 12,
            tapCount: 3,
            timeLimit: 30,
            parTaps: 4
        )

        XCTAssertEqual(stars, 0)
    }

    func testScoringAwardsOneStarForCompletedButOverTimeLimit() {
        let service = ScoringService()

        let stars = service.stars(
            didComplete: true,
            elapsedTime: 31,
            tapCount: 3,
            timeLimit: 30,
            parTaps: 4
        )

        XCTAssertEqual(stars, 1)
    }

    func testScoringAwardsTwoStarsWhenUnderTimeButOverParTaps() {
        let service = ScoringService()

        let stars = service.stars(
            didComplete: true,
            elapsedTime: 20,
            tapCount: 5,
            timeLimit: 30,
            parTaps: 4
        )

        XCTAssertEqual(stars, 2)
    }

    func testScoringAwardsThreeStarsWhenUnderTimeAndAtOrUnderParTaps() {
        let service = ScoringService()

        let score = service.score(
            levelID: "level_001",
            didComplete: true,
            elapsedTime: 20,
            tapCount: 4,
            timeLimit: 30,
            parTaps: 4
        )

        XCTAssertEqual(score.stars, 3)
        XCTAssertEqual(score.levelID, "level_001")
        XCTAssertEqual(score.timeTaken, 20)
        XCTAssertEqual(score.tapCount, 4)
    }

    func testProgressServiceBestStarsOnlyMovesUpwardAndPersists() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)

        let service = ProgressService(userDefaults: defaults)
        let levelID = "level_001"

        XCTAssertEqual(service.bestStars(for: levelID), 0)
        XCTAssertEqual(service.saveBestStars(1, for: levelID), 1)
        XCTAssertEqual(service.saveBestStars(3, for: levelID), 3)
        XCTAssertEqual(service.saveBestStars(2, for: levelID), 3)
        XCTAssertEqual(service.bestStars(for: levelID), 3)

        let reloadedService = ProgressService(userDefaults: defaults)
        XCTAssertEqual(reloadedService.bestStars(for: levelID), 3)
    }

    func testProgressServiceBestStarsReadIsClampedToThreeForCorruptValues() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        defaults.set(["level_001": 9], forKey: "bestStarsByLevelID")

        let service = ProgressService(userDefaults: defaults)
        XCTAssertEqual(service.bestStars(for: "level_001"), 3)
    }

    func testProgressServiceResetClearsSavedStars() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)

        let service = ProgressService(userDefaults: defaults)
        service.saveBestStars(3, for: "level_001")

        service.resetProgress()

        XCTAssertEqual(service.bestStars(for: "level_001"), 0)
        XCTAssertEqual(service.totalStars(), 0)
        XCTAssertEqual(service.completedLevelCount(), 0)
    }

    func testProgressServiceResetKeepsCoinsAndCosmetics() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let repository = SaveDataRepository(userDefaults: defaults)
        let service = ProgressService(repository: repository)
        repository.update { profile in
            profile.coinTotal = 250
            profile.ownedCosmeticIDs.insert("themeForestPath")
        }
        service.saveBestStars(3, for: "level_001")

        service.resetProgress()

        let profile = repository.load()
        XCTAssertEqual(profile.bestStarsByLevelID, [:])
        XCTAssertEqual(profile.unlockedLevelIDs, Set(["level_001"]))
        XCTAssertEqual(profile.coinTotal, 250)
        XCTAssertTrue(profile.ownedCosmeticIDs.contains("themeForestPath"))
    }

    func testProgressServiceResetIsSafeWhenNoProgressExists() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)

        let service = ProgressService(userDefaults: defaults)

        service.resetProgress()

        XCTAssertEqual(service.bestStarsSnapshot(), [:])
    }

    func testCompleteLevelUnlocksNextLevel() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let service = ProgressService(userDefaults: defaults)

        let update = service.completeLevel(
            levelID: "level_001",
            earnedStars: 2,
            nextLevelID: "level_002"
        )

        XCTAssertEqual(update.bestStars, 2)
        XCTAssertTrue(update.wasFirstCompletion)
        XCTAssertEqual(update.unlockedNextLevelID, "level_002")
        XCTAssertTrue(service.isLevelCompleted("level_001"))
        XCTAssertTrue(service.isLevelUnlocked("level_002"))
    }

    func testReplayDoesNotRegressBestStars() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let service = ProgressService(userDefaults: defaults)
        service.completeLevel(levelID: "level_001", earnedStars: 3, nextLevelID: "level_002")

        let update = service.completeLevel(levelID: "level_001", earnedStars: 1, nextLevelID: "level_002")

        XCTAssertEqual(update.bestStars, 3)
        XCTAssertFalse(update.wasFirstCompletion)
        XCTAssertEqual(service.bestStars(for: "level_001"), 3)
    }

    func testCompletingFinalLevelWithoutNextLevelDoesNotCrash() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let service = ProgressService(userDefaults: defaults)

        let update = service.completeLevel(levelID: "level_011", earnedStars: 1, nextLevelID: nil)

        XCTAssertEqual(update.unlockedNextLevelID, nil)
        XCTAssertTrue(service.isLevelCompleted("level_011"))
    }

    func testZeroStarCompletionDoesNotUnlockNextLevel() {
        let suiteName = "ScoringAndProgressServiceTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let service = ProgressService(userDefaults: defaults)

        let update = service.completeLevel(
            levelID: "level_001",
            earnedStars: 0,
            nextLevelID: "level_002"
        )

        XCTAssertFalse(update.wasFirstCompletion)
        XCTAssertFalse(service.isLevelCompleted("level_001"))
        XCTAssertFalse(service.isLevelUnlocked("level_002"))
    }
}
