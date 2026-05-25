import XCTest
@testable import TinyRoutes

final class TRResultSummaryTests: XCTestCase {
    func testSuccessSummaryScoresAndPersistsBestStars() throws {
        let suiteName = "TRResultSummaryTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let saveRepository = SaveDataRepository(userDefaults: defaults)
        let progressService = ProgressService(repository: saveRepository)
        let economyService = EconomyService(repository: saveRepository)
        let factory = TRResultSummaryFactory(
            levelRepository: repository(returning: level(id: "level_012", timeLimitSeconds: 60, parTaps: 4)),
            progressService: progressService,
            economyService: economyService,
            saveDataRepository: saveRepository
        )

        let summary = factory.makeSummary(
            levelID: "level_012",
            resultType: .completed,
            elapsedTime: 32,
            tapCount: 4,
            failureReason: nil
        )

        XCTAssertEqual(summary.levelTitle, "Level 12")
        XCTAssertEqual(summary.headline, "Level Complete!")
        XCTAssertEqual(summary.subtitle, "Package delivered successfully")
        XCTAssertEqual(summary.earnedStars, 3)
        XCTAssertEqual(summary.displayedStars, 3)
        XCTAssertEqual(summary.bestStars, 3)
        XCTAssertEqual(summary.coinReward, 150)
        XCTAssertEqual(summary.coinTotal, 150)
        XCTAssertEqual(summary.streakDays, 0)
        XCTAssertEqual(summary.streakBonus, 0)
        XCTAssertEqual(summary.hintCount, 3)
        XCTAssertEqual(summary.timeGoalText, "1:00.0")
        XCTAssertEqual(summary.movesGoalText, "4")
        XCTAssertEqual(progressService.bestStars(for: "level_012"), 3)
        XCTAssertTrue(progressService.isLevelCompleted("level_012"))
    }

    func testSuccessSummaryCanPreviewBestStarsWithoutPersisting() throws {
        let suiteName = "TRResultSummaryTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let saveRepository = SaveDataRepository(userDefaults: defaults)
        let progressService = ProgressService(repository: saveRepository)
        let economyService = EconomyService(repository: saveRepository)
        let factory = TRResultSummaryFactory(
            levelRepository: repository(returning: level(id: "level_001", timeLimitSeconds: 30, parTaps: 2)),
            progressService: progressService,
            economyService: economyService,
            saveDataRepository: saveRepository
        )

        let summary = factory.makeSummary(
            levelID: "level_001",
            resultType: .completed,
            elapsedTime: 10,
            tapCount: 2,
            failureReason: nil,
            persistCompletion: false
        )

        XCTAssertEqual(summary.bestStars, 3)
        XCTAssertEqual(summary.coinReward, 150)
        XCTAssertEqual(progressService.bestStars(for: "level_001"), 0)
        XCTAssertEqual(economyService.coinTotal(), 0)
    }

    func testTimeExpiredFailureCopyIsFriendly() throws {
        let summary = failureSummary(reason: .timeExpired)

        XCTAssertEqual(summary.subtitle, "The package wasn't delivered in time.")
        XCTAssertEqual(summary.failureTitle, "Out of time")
        XCTAssertEqual(summary.failureBody, "You ran out of time before delivering the package.")
        XCTAssertEqual(summary.encouragementText, "You're close! Try a different route.")
    }

    func testDeadEndFailureCopyIsFriendly() throws {
        let summary = failureSummary(reason: .deadEnd)

        XCTAssertEqual(summary.subtitle, "The delivery route hit a dead end.")
        XCTAssertEqual(summary.failureTitle, "Dead end")
        XCTAssertEqual(summary.failureBody, "The delivery dot stopped where no route was available.")
        XCTAssertEqual(summary.encouragementText, "Rotate an earlier arrow and try again.")
    }

    func testReachedDestinationWithoutPackageFailureCopyIsFriendly() throws {
        let summary = failureSummary(reason: .reachedDestinationWithoutPackage)

        XCTAssertEqual(summary.subtitle, "The package was not picked up first.")
        XCTAssertEqual(summary.failureTitle, "Package missed")
        XCTAssertEqual(summary.failureBody, "Reach the package before heading to the destination.")
        XCTAssertEqual(summary.encouragementText, "Try routing through the box first.")
    }

    func testFailureSummaryDoesNotPersistDisplayedStars() throws {
        let suiteName = "TRResultSummaryTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let saveRepository = SaveDataRepository(userDefaults: defaults)
        let progressService = ProgressService(repository: saveRepository)
        let economyService = EconomyService(repository: saveRepository)
        let factory = TRResultSummaryFactory(
            levelRepository: repository(returning: level(id: "level_003", timeLimitSeconds: 45, parTaps: 7)),
            progressService: progressService,
            economyService: economyService,
            saveDataRepository: saveRepository
        )

        let summary = factory.makeSummary(
            levelID: "level_003",
            resultType: .failed,
            elapsedTime: 45,
            tapCount: 9,
            failureReason: .timeExpired
        )

        XCTAssertEqual(summary.earnedStars, 0)
        XCTAssertEqual(summary.displayedStars, 1)
        XCTAssertEqual(summary.bestStars, 0)
        XCTAssertEqual(summary.coinReward, 0)
        XCTAssertEqual(summary.coinTotal, 0)
        XCTAssertEqual(progressService.bestStars(for: "level_003"), 0)
        XCTAssertEqual(economyService.coinTotal(), 0)
    }

    func testCompletionUnlocksNextLevelAndAwardsCoinsOnce() throws {
        let suiteName = "TRResultSummaryTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let saveRepository = SaveDataRepository(userDefaults: defaults)
        let progressService = ProgressService(repository: saveRepository)
        let economyService = EconomyService(repository: saveRepository)
        let factory = TRResultSummaryFactory(
            levelRepository: repository(returning: level(id: "level_001", timeLimitSeconds: 60, parTaps: 4)),
            progressService: progressService,
            economyService: economyService,
            saveDataRepository: saveRepository
        )

        let firstSummary = factory.makeSummary(
            levelID: "level_001",
            resultType: .completed,
            elapsedTime: 30,
            tapCount: 4,
            failureReason: nil,
            nextLevelID: "level_002",
            persistCompletion: true
        )
        let duplicateSummary = factory.makeSummary(
            levelID: "level_001",
            resultType: .completed,
            elapsedTime: 30,
            tapCount: 4,
            failureReason: nil,
            nextLevelID: "level_002",
            persistCompletion: true
        )

        XCTAssertEqual(firstSummary.coinReward, 150)
        XCTAssertEqual(duplicateSummary.coinReward, 0)
        XCTAssertEqual(economyService.coinTotal(), 150)
        XCTAssertTrue(progressService.isLevelUnlocked("level_002"))
    }

    func testPreviewSummaryNeverMutatesSavedData() throws {
        let suiteName = "TRResultSummaryTests.\(#function)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let saveRepository = SaveDataRepository(userDefaults: defaults)
        let progressService = ProgressService(repository: saveRepository)
        let economyService = EconomyService(repository: saveRepository)
        let factory = TRResultSummaryFactory(
            levelRepository: repository(returning: level(id: "level_004", timeLimitSeconds: 60, parTaps: 4)),
            progressService: progressService,
            economyService: economyService,
            saveDataRepository: saveRepository
        )

        _ = factory.makeSummary(
            levelID: "level_004",
            resultType: .completed,
            elapsedTime: 30,
            tapCount: 4,
            failureReason: nil,
            nextLevelID: "level_005",
            persistCompletion: false
        )

        XCTAssertEqual(progressService.bestStars(for: "level_004"), 0)
        XCTAssertFalse(progressService.isLevelUnlocked("level_005"))
        XCTAssertEqual(economyService.coinTotal(), 0)
    }

    private func failureSummary(reason: LevelFailureReason) -> TRResultSummary {
        let suiteName = "TRResultSummaryTests.\(#function).\(reason.message)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let saveRepository = SaveDataRepository(userDefaults: defaults)
        let progressService = ProgressService(repository: saveRepository)
        let economyService = EconomyService(repository: saveRepository)
        let factory = TRResultSummaryFactory(
            levelRepository: repository(returning: level(id: "level_002", timeLimitSeconds: 50, parTaps: 5)),
            progressService: progressService,
            economyService: economyService,
            saveDataRepository: saveRepository
        )

        return factory.makeSummary(
            levelID: "level_002",
            resultType: .failed,
            elapsedTime: 18,
            tapCount: 6,
            failureReason: reason
        )
    }

    private func repository(returning level: LevelData) -> LevelRepository {
        let data = try! JSONEncoder().encode(level)
        return LevelRepository(
            urlResolver: { _ in URL(fileURLWithPath: "/tmp/\(level.id).json") },
            dataLoader: { _ in data }
        )
    }

    private func level(id: String, timeLimitSeconds: Int, parTaps: Int) -> LevelData {
        LevelData(
            id: id,
            name: "Test Level",
            graph: RouteGraph(),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: timeLimitSeconds,
            parTaps: parTaps
        )
    }
}
