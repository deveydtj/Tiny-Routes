import Foundation

enum EconomyChangeReason: Equatable {
    case levelComplete(levelID: String)
    case cosmeticUnlock(cosmeticID: String)
    case dailyBonus
    case debug
}

/// Manages the player's coin balance and spending.
final class EconomyService {
    private let repository: SaveDataRepository

    init(repository: SaveDataRepository = SaveDataRepository()) {
        self.repository = repository
    }

    func coinTotal() -> Int {
        repository.load().coinTotal
    }

    @discardableResult
    func addCoins(_ amount: Int, reason: EconomyChangeReason) -> Int {
        guard amount > 0 else {
            return coinTotal()
        }

        return repository.update { profile in
            profile.coinTotal += amount
            profile.lifetimeCoinsEarned += amount
        }.coinTotal
    }

    func canSpend(_ amount: Int) -> Bool {
        guard amount > 0 else {
            return false
        }

        return coinTotal() >= amount
    }

    @discardableResult
    func spendCoins(_ amount: Int, reason: EconomyChangeReason) -> Bool {
        guard amount > 0 else {
            return false
        }

        var didSpend = false
        repository.update { profile in
            guard profile.coinTotal >= amount else {
                return
            }

            profile.coinTotal -= amount
            profile.lifetimeCoinsSpent += amount
            didSpend = true
        }

        return didSpend
    }

    static let coinsPerStar = 50

    /// Coins a win is worth: 50 for each star above the level's best so far. A
    /// first win pays for every star; a replay pays only for the improvement.
    func previewLevelCompletionReward(levelID: String, earnedStars: Int, previousBestStars: Int) -> Int {
        guard !levelID.isEmpty else {
            return 0
        }

        let earned = min(max(earnedStars, 0), 3)
        let alreadyPaid = min(max(previousBestStars, 0), 3)
        return max(earned - alreadyPaid, 0) * Self.coinsPerStar
    }

    /// Pays `previewLevelCompletionReward`. `previousBestStars` is the level's best
    /// before this win, as `LevelProgressUpdate` reports it.
    @discardableResult
    func awardLevelCompletionReward(
        levelID: String,
        earnedStars: Int,
        previousBestStars: Int
    ) -> Int {
        let reward = previewLevelCompletionReward(
            levelID: levelID,
            earnedStars: earnedStars,
            previousBestStars: previousBestStars
        )

        guard reward > 0 else {
            return 0
        }

        repository.update { profile in
            profile.claimedLevelRewardKeys.insert(levelCompletionRewardKey(levelID: levelID))
            profile.coinTotal += reward
            profile.lifetimeCoinsEarned += reward
        }

        return reward
    }

    private func levelCompletionRewardKey(levelID: String) -> String {
        "levelComplete:\(levelID)"
    }
}
