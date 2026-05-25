import Foundation

/// Reads and writes the local player save profile as one JSON payload.
final class SaveDataRepository {
    private let userDefaults: UserDefaults
    private let storageKey: String
    private let legacyBestStarsKey: String
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init(
        userDefaults: UserDefaults = .standard,
        storageKey: String = "playerProfile.v1",
        legacyBestStarsKey: String = "bestStarsByLevelID"
    ) {
        self.userDefaults = userDefaults
        self.storageKey = storageKey
        self.legacyBestStarsKey = legacyBestStarsKey
    }

    func load() -> PlayerProfile {
        if let data = userDefaults.data(forKey: storageKey) {
            guard let decodedProfile = try? decoder.decode(PlayerProfile.self, from: data) else {
                return .defaultValue
            }

            return decodedProfile.normalized()
        }

        if let migratedProfile = migratedLegacyStarsProfile() {
            save(migratedProfile)
            return migratedProfile
        }

        return .defaultValue
    }

    func save(_ profile: PlayerProfile) {
        let normalizedProfile = profile.normalized()
        guard let data = try? encoder.encode(normalizedProfile) else {
            return
        }

        userDefaults.set(data, forKey: storageKey)
    }

    @discardableResult
    func reset() -> PlayerProfile {
        userDefaults.removeObject(forKey: storageKey)
        return .defaultValue
    }

    func hasSaveData() -> Bool {
        userDefaults.data(forKey: storageKey) != nil
    }

    @discardableResult
    func update(_ transform: (inout PlayerProfile) -> Void) -> PlayerProfile {
        var profile = load()
        transform(&profile)
        profile.lastUpdatedAt = Date()
        let normalizedProfile = profile.normalized()
        save(normalizedProfile)
        return normalizedProfile
    }

    private func migratedLegacyStarsProfile() -> PlayerProfile? {
        guard let legacyStars = legacyBestStarsByLevelID(),
              legacyStars.isEmpty == false else {
            return nil
        }

        var profile = PlayerProfile.defaultValue
        profile.bestStarsByLevelID = legacyStars
        return profile.normalized()
    }

    private func legacyBestStarsByLevelID() -> [String: Int]? {
        guard let dictionary = userDefaults.dictionary(forKey: legacyBestStarsKey),
              dictionary.isEmpty == false else {
            return nil
        }

        var starsByLevelID: [String: Int] = [:]
        for (levelID, value) in dictionary {
            if let stars = value as? Int {
                starsByLevelID[levelID] = stars
            } else if let stars = value as? NSNumber {
                starsByLevelID[levelID] = stars.intValue
            }
        }

        return starsByLevelID.isEmpty ? nil : starsByLevelID
    }
}
