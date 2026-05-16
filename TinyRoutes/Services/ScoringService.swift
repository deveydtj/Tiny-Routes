import Foundation

/// Calculates star rating and score from a completed level attempt.
final class ScoringService {
    func score(
        levelID: String,
        didComplete: Bool,
        elapsedTime: TimeInterval,
        tapCount: Int,
        timeLimit: TimeInterval,
        parTaps: Int
    ) -> ScoreResult {
        ScoreResult(
            levelID: levelID,
            stars: stars(
                didComplete: didComplete,
                elapsedTime: elapsedTime,
                tapCount: tapCount,
                timeLimit: timeLimit,
                parTaps: parTaps
            ),
            timeTaken: max(0, elapsedTime),
            tapCount: max(0, tapCount)
        )
    }

    func stars(
        didComplete: Bool,
        elapsedTime: TimeInterval,
        tapCount: Int,
        timeLimit: TimeInterval,
        parTaps: Int
    ) -> Int {
        guard didComplete else {
            return 0
        }

        let normalizedElapsedTime = max(0, elapsedTime)
        let normalizedTapCount = max(0, tapCount)
        let normalizedTimeLimit = max(0, timeLimit)
        let normalizedParTaps = max(0, parTaps)

        guard normalizedElapsedTime <= normalizedTimeLimit else {
            return 1
        }

        return normalizedTapCount <= normalizedParTaps ? 3 : 2
    }
}
