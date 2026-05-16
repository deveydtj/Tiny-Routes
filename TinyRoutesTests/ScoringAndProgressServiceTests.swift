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

    func testScoringAwardsThreeStarsWhenUnderTimeAndUnderParTaps() {
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
}
