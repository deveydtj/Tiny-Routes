import XCTest
@testable import TinyRoutes

final class TRProfileSummaryTests: XCTestCase {
    func testXPProgressClampsToZeroWhenXPIsNegative() {
        let summary = makeSummary(currentXP: -100, nextLevelXP: 1_000)
        XCTAssertEqual(summary.xpProgress, 0, accuracy: 0.001)
    }

    func testXPProgressClampsToOneWhenCurrentXPExceedsNextLevelXP() {
        let summary = makeSummary(currentXP: 1_500, nextLevelXP: 1_000)
        XCTAssertEqual(summary.xpProgress, 1, accuracy: 0.001)
    }

    func testXPProgressReturnsZeroWhenNextLevelXPIsZero() {
        let summary = makeSummary(currentXP: 100, nextLevelXP: 0)
        XCTAssertEqual(summary.xpProgress, 0, accuracy: 0.001)
    }

    func testRewardProgressClampsToRange() {
        XCTAssertEqual(TRProfileRewardProgress(title: "Reward", subtitle: "Test", currentValue: -5, targetValue: 10, rewardCoins: 100).progress, 0, accuracy: 0.001)
        XCTAssertEqual(TRProfileRewardProgress(title: "Reward", subtitle: "Test", currentValue: 12, targetValue: 10, rewardCoins: 100).progress, 1, accuracy: 0.001)
        XCTAssertEqual(TRProfileRewardProgress(title: "Reward", subtitle: "Test", currentValue: 5, targetValue: 10, rewardCoins: 100).progress, 0.5, accuracy: 0.001)
    }

    func testFastestTimeFormatsWholeSeconds() {
        let summary = makeSummary(fastestTime: 48)
        XCTAssertEqual(summary.fastestTimeText, "00:48")
    }

    func testFastestTimeFormatsNilAsPlaceholder() {
        let summary = makeSummary(fastestTime: nil)
        XCTAssertEqual(summary.fastestTimeText, "--:--")
    }

    func testRewardProgressTextUsesCurrentAndTargetValues() {
        let progress = TRProfileRewardProgress(
            title: "Star Collector",
            subtitle: "Collect 150 stars to earn a reward!",
            currentValue: 128,
            targetValue: 150,
            rewardCoins: 250
        )

        XCTAssertEqual(progress.progressText, "128 / 150")
        XCTAssertGreaterThan(progress.progress, 0)
        XCTAssertLessThan(progress.progress, 1)
    }

    private func makeSummary(
        currentXP: Int = 2_150,
        nextLevelXP: Int = 3_000,
        fastestTime: TimeInterval? = 48
    ) -> TRProfileSummary {
        TRProfileSummary(
            playerName: "Player One",
            rankTitle: "Route Master",
            memberSinceText: "Member since 2026",
            level: 24,
            currentXP: currentXP,
            nextLevelXP: nextLevelXP,
            totalStars: 128,
            completedLevelCount: 42,
            bestStreakDays: 7,
            fastestTime: fastestTime,
            coinTotal: 1_250,
            achievements: [],
            collectionSelections: [],
            rewardProgress: TRProfileRewardProgress(
                title: "Star Collector",
                subtitle: "Collect 150 stars to earn a reward!",
                currentValue: 128,
                targetValue: 150,
                rewardCoins: 250
            )
        )
    }
}
