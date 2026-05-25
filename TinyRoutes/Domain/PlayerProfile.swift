import Foundation

/// Stores local player progression, currency, cosmetics, and entitlement state.
struct PlayerProfile: Codable, Equatable {
    static let currentSchemaVersion = 1

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

    init(
        schemaVersion: Int = PlayerProfile.currentSchemaVersion,
        playerName: String = "Player One",
        createdAt: Date = Date(),
        lastUpdatedAt: Date = Date(),
        unlockedLevelIDs: Set<String> = ["level_001"],
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
        claimedLevelRewardKeys: Set<String> = []
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
    }

    func normalized() -> PlayerProfile {
        var profile = self
        let defaultProfile = PlayerProfile.defaultValue

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

        return profile
    }
}
