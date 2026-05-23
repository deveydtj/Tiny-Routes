import Foundation

/// Tracks and persists level completion, stars, and unlocks.
final class ProgressService {
    private let userDefaults: UserDefaults
    private let bestStarsByLevelIDKey: String

    init(
        userDefaults: UserDefaults = .standard,
        bestStarsByLevelIDKey: String = "bestStarsByLevelID"
    ) {
        self.userDefaults = userDefaults
        self.bestStarsByLevelIDKey = bestStarsByLevelIDKey
    }

    func bestStars(for levelID: String) -> Int {
        min(max(bestStarsByLevelID()[levelID] ?? 0, 0), 3)
    }

    func bestStarsSnapshot() -> [String: Int] {
        bestStarsByLevelID().mapValues { min(max($0, 0), 3) }
    }

    func totalStars() -> Int {
        bestStarsSnapshot().values.reduce(0, +)
    }

    func completedLevelCount() -> Int {
        bestStarsSnapshot().values.filter { $0 > 0 }.count
    }

    @discardableResult
    func saveBestStars(_ stars: Int, for levelID: String) -> Int {
        guard !levelID.isEmpty else {
            return 0
        }

        let clampedStars = min(max(stars, 0), 3)
        var bestStars = bestStarsByLevelID()
        let updatedBestStars = max(bestStars[levelID] ?? 0, clampedStars)

        if updatedBestStars != bestStars[levelID] {
            bestStars[levelID] = updatedBestStars
            userDefaults.set(bestStars, forKey: bestStarsByLevelIDKey)
        }

        return updatedBestStars
    }

    private func bestStarsByLevelID() -> [String: Int] {
        userDefaults.dictionary(forKey: bestStarsByLevelIDKey) as? [String: Int] ?? [:]
    }
}
