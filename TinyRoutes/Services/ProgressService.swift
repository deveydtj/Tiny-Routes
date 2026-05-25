import Foundation

struct LevelProgressUpdate: Equatable {
    let levelID: String
    let earnedStars: Int
    let bestStars: Int
    let previousBestStars: Int
    let didImproveBestStars: Bool
    let wasCompletedBefore: Bool
    let isCompleted: Bool
    let unlockedNextLevelID: String?

    var wasFirstCompletion: Bool {
        isCompleted && wasCompletedBefore == false
    }
}

/// Tracks and persists level completion, stars, and unlocks.
final class ProgressService {
    private let repository: SaveDataRepository

    init(repository: SaveDataRepository = SaveDataRepository()) {
        self.repository = repository
    }

    convenience init(
        userDefaults: UserDefaults = .standard,
        bestStarsByLevelIDKey: String = "bestStarsByLevelID"
    ) {
        self.init(
            repository: SaveDataRepository(
                userDefaults: userDefaults,
                legacyBestStarsKey: bestStarsByLevelIDKey
            )
        )
    }

    func bestStars(for levelID: String) -> Int {
        repository.load().bestStarsByLevelID[levelID] ?? 0
    }

    func bestStarsSnapshot() -> [String: Int] {
        repository.load().bestStarsByLevelID
    }

    func totalStars() -> Int {
        bestStarsSnapshot().values.reduce(0, +)
    }

    func completedLevelCount() -> Int {
        repository.load().completedLevelIDs.count
    }

    func isLevelUnlocked(_ levelID: String) -> Bool {
        repository.load().unlockedLevelIDs.contains(levelID)
    }

    func isLevelCompleted(_ levelID: String) -> Bool {
        repository.load().completedLevelIDs.contains(levelID)
    }

    func unlockedLevelIDs() -> Set<String> {
        repository.load().unlockedLevelIDs
    }

    func resetProgress() {
        repository.update { profile in
            profile.unlockedLevelIDs = PlayerProfile.defaultValue.unlockedLevelIDs
            profile.completedLevelIDs = []
            profile.bestStarsByLevelID = [:]
            profile.fastestCompletionTimeByLevelID = [:]
        }
    }

    @discardableResult
    func saveBestStars(_ stars: Int, for levelID: String) -> Int {
        guard !levelID.isEmpty else {
            return 0
        }

        let clampedStars = min(max(stars, 0), 3)
        return repository.update { profile in
            let currentBestStars = profile.bestStarsByLevelID[levelID] ?? 0
            let updatedBestStars = max(currentBestStars, clampedStars)
            profile.bestStarsByLevelID[levelID] = updatedBestStars
            if updatedBestStars > 0 {
                profile.completedLevelIDs.insert(levelID)
                profile.unlockedLevelIDs.insert(levelID)
            }
        }.bestStarsByLevelID[levelID] ?? 0
    }

    @discardableResult
    func completeLevel(
        levelID: String,
        earnedStars: Int,
        nextLevelID: String?,
        elapsedTime: TimeInterval? = nil
    ) -> LevelProgressUpdate {
        guard !levelID.isEmpty else {
            return LevelProgressUpdate(
                levelID: levelID,
                earnedStars: 0,
                bestStars: 0,
                previousBestStars: 0,
                didImproveBestStars: false,
                wasCompletedBefore: false,
                isCompleted: false,
                unlockedNextLevelID: nil
            )
        }

        let clampedStars = min(max(earnedStars, 0), 3)
        var previousBestStars = 0
        var updatedBestStars = 0
        var wasCompletedBefore = false
        var isCompleted = false
        var unlockedNextLevelID: String?

        let savedProfile = repository.update { profile in
            previousBestStars = profile.bestStarsByLevelID[levelID] ?? 0
            wasCompletedBefore = profile.completedLevelIDs.contains(levelID) || previousBestStars > 0
            updatedBestStars = max(previousBestStars, clampedStars)
            profile.bestStarsByLevelID[levelID] = updatedBestStars
            profile.unlockedLevelIDs.insert(levelID)

            if clampedStars > 0 {
                profile.completedLevelIDs.insert(levelID)
                isCompleted = true

                if let nextLevelID, !nextLevelID.isEmpty {
                    profile.unlockedLevelIDs.insert(nextLevelID)
                    unlockedNextLevelID = nextLevelID
                }
            } else {
                isCompleted = profile.completedLevelIDs.contains(levelID)
            }

            if let elapsedTime, elapsedTime >= 0 {
                let currentFastestTime = profile.fastestCompletionTimeByLevelID[levelID]
                if currentFastestTime == nil || elapsedTime < currentFastestTime! {
                    profile.fastestCompletionTimeByLevelID[levelID] = elapsedTime
                }
            }
        }

        updatedBestStars = savedProfile.bestStarsByLevelID[levelID] ?? updatedBestStars
        isCompleted = savedProfile.completedLevelIDs.contains(levelID)
        unlockedNextLevelID = nextLevelID.flatMap { savedProfile.unlockedLevelIDs.contains($0) ? $0 : nil }

        return LevelProgressUpdate(
            levelID: levelID,
            earnedStars: clampedStars,
            bestStars: updatedBestStars,
            previousBestStars: previousBestStars,
            didImproveBestStars: updatedBestStars > previousBestStars,
            wasCompletedBefore: wasCompletedBefore,
            isCompleted: isCompleted,
            unlockedNextLevelID: unlockedNextLevelID
        )
    }
}
