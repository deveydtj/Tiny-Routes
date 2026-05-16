import SwiftUI

/// Post-level result screen.
struct ResultScreen: View {

    enum ResultType {
        case completed
        case failed
    }

    let levelID: String
    let result: ResultType
    let elapsedTime: TimeInterval
    let tapCount: Int
    let failureReason: LevelFailureReason?
    let onRestartTapped: () -> Void
    let onExitTapped: () -> Void
    private let levelRepository: LevelRepository
    private let scoringService: ScoringService
    private let progressService: ProgressService

    @State private var awardedStars: Int = 0
    @State private var bestStars: Int = 0

    init(
        levelID: String,
        result: ResultType,
        elapsedTime: TimeInterval,
        tapCount: Int,
        failureReason: LevelFailureReason?,
        onRestartTapped: @escaping () -> Void,
        onExitTapped: @escaping () -> Void,
        levelRepository: LevelRepository = LevelRepository(),
        scoringService: ScoringService = ScoringService(),
        progressService: ProgressService = ProgressService()
    ) {
        self.levelID = levelID
        self.result = result
        self.elapsedTime = elapsedTime
        self.tapCount = tapCount
        self.failureReason = failureReason
        self.onRestartTapped = onRestartTapped
        self.onExitTapped = onExitTapped
        self.levelRepository = levelRepository
        self.scoringService = scoringService
        self.progressService = progressService
    }

    private var titleText: String {
        switch result {
        case .completed: "Level Complete"
        case .failed: "Level Failed"
        }
    }

    private var starsRefreshKey: String {
        let resultKey: String
        switch result {
        case .completed:
            resultKey = "completed"
        case .failed:
            resultKey = "failed"
        }
        return "\(levelID)|\(resultKey)|\(elapsedTime)|\(tapCount)"
    }

    var body: some View {
        VStack(spacing: 12) {
            Text(titleText)
                .font(.title)
            Text("Level: \(levelID)")
            Text("Final Time: \(GameTimeFormatter.elapsed(elapsedTime))")
                .font(.subheadline)
                .foregroundColor(.secondary)
            Text("Final Taps: \(tapCount)")
                .font(.subheadline)
                .foregroundColor(.secondary)
            if case .completed = result {
                Text("Stars: \(starString(for: awardedStars))")
                    .font(.headline)
                Text("Best: \(starString(for: bestStars))")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            if let failureReason, case .failed = result {
                Text(failureReason.message)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Button("Restart", action: onRestartTapped)
            Button("Back to Menu", action: onExitTapped)
        }
        .task(id: starsRefreshKey) {
            updateStars()
        }
    }

    private func starString(for stars: Int) -> String {
        let clampedStars = min(max(stars, 0), 3)
        return String(repeating: "★", count: clampedStars) + String(repeating: "☆", count: 3 - clampedStars)
    }

    private func updateStars() {
        guard case .completed = result else {
            awardedStars = 0
            bestStars = progressService.bestStars(for: levelID)
            return
        }

        do {
            let levelData = try levelRepository.loadLevel(id: levelID)
            let scoreResult = scoringService.score(
                levelID: levelID,
                didComplete: true,
                elapsedTime: elapsedTime,
                tapCount: tapCount,
                timeLimit: TimeInterval(levelData.timeLimitSeconds),
                parTaps: levelData.parTaps
            )
            awardedStars = scoreResult.stars
            bestStars = progressService.saveBestStars(scoreResult.stars, for: levelID)
        } catch {
            awardedStars = 1
            bestStars = progressService.saveBestStars(awardedStars, for: levelID)
        }
    }
}

#Preview {
    ResultScreen(
        levelID: "level_001",
        result: .completed,
        elapsedTime: 18.4,
        tapCount: 12,
        failureReason: nil,
        onRestartTapped: {},
        onExitTapped: {}
    )
}
