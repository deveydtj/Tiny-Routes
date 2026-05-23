import Foundation

struct TRResultSummary: Equatable {
    let levelID: String
    let levelTitle: String
    let resultType: ResultScreen.ResultType
    let headline: String
    let subtitle: String
    let elapsedTimeText: String
    let tapCountText: String
    let earnedStars: Int
    let displayedStars: Int
    let bestStars: Int
    let coinReward: Int
    let coinTotal: Int
    let streakDays: Int
    let streakBonus: Int
    let hintCount: Int
    let timeGoalText: String
    let movesGoalText: String
    let failureTitle: String?
    let failureBody: String?
    let encouragementText: String?
}

struct TRResultSummaryFactory {
    let levelRepository: LevelRepository
    let scoringService: ScoringService
    let progressService: ProgressService

    init(
        levelRepository: LevelRepository = LevelRepository(),
        scoringService: ScoringService = ScoringService(),
        progressService: ProgressService = ProgressService()
    ) {
        self.levelRepository = levelRepository
        self.scoringService = scoringService
        self.progressService = progressService
    }

    func makeSummary(
        levelID: String,
        resultType: ResultScreen.ResultType,
        elapsedTime: TimeInterval,
        tapCount: Int,
        failureReason: LevelFailureReason?,
        persistCompletion: Bool = true
    ) -> TRResultSummary {
        let levelData = try? levelRepository.loadLevel(id: levelID)
        let levelTitle = GameplayLevelNumberFormatter.title(for: levelID)
        let elapsedTimeText = GameTimeFormatter.elapsed(elapsedTime)
        let tapCountText = "\(max(tapCount, 0))"
        let timeGoalText = levelData.map { GameTimeFormatter.elapsed(TimeInterval($0.timeLimitSeconds)) } ?? "-"
        let movesGoalText = levelData.map { "\($0.parTaps)" } ?? "-"

        switch resultType {
        case .completed:
            let earnedStars = completedStars(
                levelID: levelID,
                levelData: levelData,
                elapsedTime: elapsedTime,
                tapCount: tapCount
            )
            let bestStars = bestStarsAfterCompletion(
                levelID: levelID,
                earnedStars: earnedStars,
                persistCompletion: persistCompletion
            )

            return TRResultSummary(
                levelID: levelID,
                levelTitle: levelTitle,
                resultType: resultType,
                headline: "Level Complete!",
                subtitle: "Package delivered successfully",
                elapsedTimeText: elapsedTimeText,
                tapCountText: tapCountText,
                earnedStars: earnedStars,
                displayedStars: earnedStars,
                bestStars: bestStars,
                coinReward: earnedStars * 50,
                coinTotal: 1_250,
                streakDays: 7,
                streakBonus: 50,
                hintCount: 3,
                timeGoalText: timeGoalText,
                movesGoalText: movesGoalText,
                failureTitle: nil,
                failureBody: nil,
                encouragementText: nil
            )

        case .failed:
            let failureCopy = FailureCopy(reason: failureReason)
            return TRResultSummary(
                levelID: levelID,
                levelTitle: levelTitle,
                resultType: resultType,
                headline: "Route Failed",
                subtitle: failureCopy.subtitle,
                elapsedTimeText: elapsedTimeText,
                tapCountText: tapCountText,
                earnedStars: 0,
                displayedStars: 1,
                bestStars: progressService.bestStars(for: levelID),
                coinReward: 0,
                coinTotal: 1_250,
                streakDays: 7,
                streakBonus: 50,
                hintCount: 3,
                timeGoalText: timeGoalText,
                movesGoalText: movesGoalText,
                failureTitle: failureCopy.title,
                failureBody: failureCopy.body,
                encouragementText: failureCopy.encouragement
            )
        }
    }

    private func completedStars(
        levelID: String,
        levelData: LevelData?,
        elapsedTime: TimeInterval,
        tapCount: Int
    ) -> Int {
        guard let levelData else {
            return 0
        }

        return scoringService.score(
            levelID: levelID,
            didComplete: true,
            elapsedTime: elapsedTime,
            tapCount: tapCount,
            timeLimit: TimeInterval(levelData.timeLimitSeconds),
            parTaps: levelData.parTaps
        ).stars
    }

    private func bestStarsAfterCompletion(
        levelID: String,
        earnedStars: Int,
        persistCompletion: Bool
    ) -> Int {
        if persistCompletion {
            return progressService.saveBestStars(earnedStars, for: levelID)
        }

        return max(progressService.bestStars(for: levelID), earnedStars)
    }
}

private struct FailureCopy {
    let subtitle: String
    let title: String
    let body: String
    let encouragement: String

    init(reason: LevelFailureReason?) {
        switch reason {
        case .timeExpired:
            subtitle = "The package wasn't delivered in time."
            title = "Out of time"
            body = "You ran out of time before delivering the package."
            encouragement = "You're close! Try a different route."
        case .deadEnd:
            subtitle = "The delivery route hit a dead end."
            title = "Dead end"
            body = "The delivery dot stopped where no route was available."
            encouragement = "Rotate an earlier arrow and try again."
        case .reachedDestinationWithoutPackage:
            subtitle = "The package was not picked up first."
            title = "Package missed"
            body = "Reach the package before heading to the destination."
            encouragement = "Try routing through the box first."
        case nil:
            subtitle = "The package did not reach its destination."
            title = "Route stopped"
            body = "The delivery could not be completed this time."
            encouragement = "Adjust the route and try again."
        }
    }
}
