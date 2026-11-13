import Foundation

/// Stores local player progression, currency, cosmetics, and entitlement state.
struct PlayerProfile: Codable, Equatable {
    /// Version 3 replaced the original 27 levels with the multi-van levels.
    /// Version 4 inserted two teaching levels, at 6 and 9, moving later levels along.
    /// Version 5 retired the cosmetics that never show on a Multi-Van board and
    /// refunded what they cost.
    static let currentSchemaVersion = 5
    static let firstLevelID = "level_001"

    static let defaultOwnedCosmeticIDs: Set<String> = [
        "themeClassic",
        "themeOceanDrive",
        "dotCourierBlue",
        "trailClean",
        "confettiStars",
        "destinationFlag"
    ]

    static let defaultSelectedCosmeticIDByCategoryID: [String: String] = [
        ShopCosmeticCategoryID.routeThemes: "themeOceanDrive",
        ShopCosmeticCategoryID.deliveryDots: "dotCourierBlue",
        ShopCosmeticCategoryID.trails: "trailClean",
        ShopCosmeticCategoryID.confetti: "confettiStars",
        ShopCosmeticCategoryID.destinations: "destinationFlag"
    ]

    static let defaultValue = PlayerProfile()

    var schemaVersion: Int
    var playerName: String
    var createdAt: Date
    var lastUpdatedAt: Date

    var unlockedLevelIDs: Set<String>
    var completedLevelIDs: Set<String>
    var bestStarsByLevelID: [String: Int]

    var coinTotal: Int
    var lifetimeCoinsEarned: Int
    var lifetimeCoinsSpent: Int

    var ownedCosmeticIDs: Set<String>
    var selectedCosmeticIDByCategoryID: [String: String]

    var isRemoveAdsPurchased: Bool
    var bestStreakDays: Int
    var currentStreakDays: Int
    var fastestCompletionTimeByLevelID: [String: TimeInterval]
    var claimedLevelRewardKeys: Set<String>
    var lastDailyBonusClaimDay: String?

    init(
        schemaVersion: Int = PlayerProfile.currentSchemaVersion,
        playerName: String = "Player One",
        createdAt: Date = Date(),
        lastUpdatedAt: Date = Date(),
        unlockedLevelIDs: Set<String> = [PlayerProfile.firstLevelID],
        completedLevelIDs: Set<String> = [],
        bestStarsByLevelID: [String: Int] = [:],
        coinTotal: Int = 0,
        lifetimeCoinsEarned: Int = 0,
        lifetimeCoinsSpent: Int = 0,
        ownedCosmeticIDs: Set<String> = PlayerProfile.defaultOwnedCosmeticIDs,
        selectedCosmeticIDByCategoryID: [String: String] = PlayerProfile.defaultSelectedCosmeticIDByCategoryID,
        isRemoveAdsPurchased: Bool = false,
        bestStreakDays: Int = 0,
        currentStreakDays: Int = 0,
        fastestCompletionTimeByLevelID: [String: TimeInterval] = [:],
        claimedLevelRewardKeys: Set<String> = [],
        lastDailyBonusClaimDay: String? = nil
    ) {
        self.schemaVersion = max(schemaVersion, PlayerProfile.currentSchemaVersion)
        self.playerName = playerName.isEmpty ? "Player One" : playerName
        self.createdAt = createdAt
        self.lastUpdatedAt = lastUpdatedAt
        self.unlockedLevelIDs = unlockedLevelIDs
        self.completedLevelIDs = completedLevelIDs
        self.bestStarsByLevelID = bestStarsByLevelID
        self.coinTotal = coinTotal
        self.lifetimeCoinsEarned = lifetimeCoinsEarned
        self.lifetimeCoinsSpent = lifetimeCoinsSpent
        self.ownedCosmeticIDs = ownedCosmeticIDs
        self.selectedCosmeticIDByCategoryID = selectedCosmeticIDByCategoryID
        self.isRemoveAdsPurchased = isRemoveAdsPurchased
        self.bestStreakDays = bestStreakDays
        self.currentStreakDays = currentStreakDays
        self.fastestCompletionTimeByLevelID = fastestCompletionTimeByLevelID
        self.claimedLevelRewardKeys = claimedLevelRewardKeys
        self.lastDailyBonusClaimDay = lastDailyBonusClaimDay
    }

    func normalized() -> PlayerProfile {
        var profile = self
        let defaultProfile = PlayerProfile.defaultValue

        if profile.schemaVersion < 3 {
            // The new levels reuse the retired levels' IDs, so none of their
            // progress or claimed completion rewards may carry over.
            profile.unlockedLevelIDs = defaultProfile.unlockedLevelIDs
            profile.completedLevelIDs = []
            profile.bestStarsByLevelID = [:]
            profile.fastestCompletionTimeByLevelID = [:]
            profile.claimedLevelRewardKeys = profile.claimedLevelRewardKeys.filter { !$0.hasPrefix("levelComplete:") }
        } else if profile.schemaVersion < 4 {
            profile.moveLevelsForTeachingLevels()
        }
        if profile.schemaVersion < 5 {
            profile.refundRetiredCosmetics()
        }
        profile.schemaVersion = max(profile.schemaVersion, PlayerProfile.currentSchemaVersion)
        if profile.playerName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            profile.playerName = defaultProfile.playerName
        }

        profile.unlockedLevelIDs = Set(profile.unlockedLevelIDs.filter { !$0.isEmpty })
        profile.completedLevelIDs = Set(profile.completedLevelIDs.filter { !$0.isEmpty })

        profile.bestStarsByLevelID = Dictionary(
            uniqueKeysWithValues: profile.bestStarsByLevelID.compactMap { levelID, stars in
                guard !levelID.isEmpty else { return nil }
                return (levelID, min(max(stars, 0), 3))
            }
        )

        for (levelID, stars) in profile.bestStarsByLevelID where stars > 0 {
            profile.completedLevelIDs.insert(levelID)
        }

        profile.unlockedLevelIDs.formUnion(profile.completedLevelIDs)
        if profile.unlockedLevelIDs.isEmpty {
            profile.unlockedLevelIDs = defaultProfile.unlockedLevelIDs
        }

        profile.coinTotal = max(profile.coinTotal, 0)
        profile.lifetimeCoinsEarned = max(profile.lifetimeCoinsEarned, 0)
        profile.lifetimeCoinsSpent = max(profile.lifetimeCoinsSpent, 0)

        profile.ownedCosmeticIDs = Set(profile.ownedCosmeticIDs.filter { !$0.isEmpty })
        profile.ownedCosmeticIDs.formUnion(PlayerProfile.defaultOwnedCosmeticIDs)

        profile.selectedCosmeticIDByCategoryID = Dictionary(
            uniqueKeysWithValues: profile.selectedCosmeticIDByCategoryID.compactMap { categoryID, cosmeticID in
                guard !categoryID.isEmpty, !cosmeticID.isEmpty else { return nil }
                return (categoryID, cosmeticID)
            }
        )

        for (categoryID, defaultCosmeticID) in PlayerProfile.defaultSelectedCosmeticIDByCategoryID {
            let selectedID = profile.selectedCosmeticIDByCategoryID[categoryID]
            if selectedID.map({ profile.ownedCosmeticIDs.contains($0) }) != true {
                profile.selectedCosmeticIDByCategoryID[categoryID] = defaultCosmeticID
            }
        }

        profile.selectedCosmeticIDByCategoryID = profile.selectedCosmeticIDByCategoryID.filter { _, cosmeticID in
            profile.ownedCosmeticIDs.contains(cosmeticID)
        }

        profile.bestStreakDays = max(profile.bestStreakDays, 0)
        profile.currentStreakDays = max(profile.currentStreakDays, 0)
        profile.fastestCompletionTimeByLevelID = Dictionary(
            uniqueKeysWithValues: profile.fastestCompletionTimeByLevelID.compactMap { levelID, time in
                guard !levelID.isEmpty, time >= 0 else { return nil }
                return (levelID, time)
            }
        )
        profile.claimedLevelRewardKeys = Set(profile.claimedLevelRewardKeys.filter { !$0.isEmpty })
        profile.lastDailyBonusClaimDay = profile.lastDailyBonusClaimDay?.trimmingCharacters(in: .whitespacesAndNewlines)
        if profile.lastDailyBonusClaimDay?.isEmpty == true {
            profile.lastDailyBonusClaimDay = nil
        }

        return profile
    }

    /// Hands back the coins spent on cosmetics the shop no longer sells and takes
    /// them out of the collection. Free ones stay; table themes and confetti carry
    /// over as they are.
    private mutating func refundRetiredCosmetics() {
        for (cosmeticID, price) in ShopCatalogService.retiredCosmeticPrices where ownedCosmeticIDs.contains(cosmeticID) {
            ownedCosmeticIDs.remove(cosmeticID)
            coinTotal += price
            lifetimeCoinsSpent = max(lifetimeCoinsSpent - price, 0)
        }
    }

    /// Where each level saved under schema 3 sits now that "Wait for It" is level 6
    /// and "Take a Lap" is level 9.
    static let schemaFourLevelIDs: [String: String] = [
        "level_006": "level_007",
        "level_007": "level_008",
        "level_008": "level_010",
        "level_009": "level_011",
        "level_010": "level_012",
        "level_011": "level_013",
        "level_012": "level_014"
    ]

    /// Carries progress to the levels' new IDs, and opens each new level to
    /// anyone who has finished the level before it.
    private mutating func moveLevelsForTeachingLevels() {
        let move = { (levelID: String) in PlayerProfile.schemaFourLevelIDs[levelID] ?? levelID }
        unlockedLevelIDs = Set(unlockedLevelIDs.map(move))
        completedLevelIDs = Set(completedLevelIDs.map(move))
        bestStarsByLevelID = Dictionary(bestStarsByLevelID.map { (move($0.key), $0.value) }, uniquingKeysWith: max)
        fastestCompletionTimeByLevelID = Dictionary(
            fastestCompletionTimeByLevelID.map { (move($0.key), $0.value) }, uniquingKeysWith: min
        )
        let rewardPrefix = "levelComplete:"
        claimedLevelRewardKeys = Set(claimedLevelRewardKeys.map { key in
            guard key.hasPrefix(rewardPrefix) else { return key }
            return rewardPrefix + move(String(key.dropFirst(rewardPrefix.count)))
        })
        let finished = completedLevelIDs.union(bestStarsByLevelID.filter { $0.value > 0 }.keys)
        for (previous, inserted) in [("level_005", "level_006"), ("level_008", "level_009")] where finished.contains(previous) {
            unlockedLevelIDs.insert(inserted)
        }
    }
}
