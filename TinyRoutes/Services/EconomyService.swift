import Foundation

enum EconomyChangeReason: Equatable {
    case levelComplete(levelID: String)
    case cosmeticUnlock(cosmeticID: String)
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

    func previewLevelCompletionReward(levelID: String, earnedStars: Int, isFirstCompletion: Bool) -> Int {
        guard isFirstCompletion,
              !levelID.isEmpty,
              earnedStars > 0,
              hasClaimedLevelCompletionReward(levelID: levelID) == false else {
            return 0
        }

        return min(max(earnedStars, 0), 3) * 50
    }

    @discardableResult
    func awardLevelCompletionReward(
        levelID: String,
        earnedStars: Int,
        isFirstCompletion: Bool
    ) -> Int {
        let reward = previewLevelCompletionReward(
            levelID: levelID,
            earnedStars: earnedStars,
            isFirstCompletion: isFirstCompletion
        )

        guard reward > 0 else {
            return 0
        }

        var awardedCoins = 0
        repository.update { profile in
            let rewardKey = levelCompletionRewardKey(levelID: levelID)
            guard profile.claimedLevelRewardKeys.contains(rewardKey) == false else {
                return
            }

            profile.claimedLevelRewardKeys.insert(rewardKey)
            profile.coinTotal += reward
            profile.lifetimeCoinsEarned += reward
            awardedCoins = reward
        }

        return awardedCoins
    }

    private func hasClaimedLevelCompletionReward(levelID: String) -> Bool {
        repository.load().claimedLevelRewardKeys.contains(levelCompletionRewardKey(levelID: levelID))
    }

    private func levelCompletionRewardKey(levelID: String) -> String {
        "levelComplete:\(levelID)"
    }
}
