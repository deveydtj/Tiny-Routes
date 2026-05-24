import Foundation

final class UserSettingsRepository {
    private let userDefaults: UserDefaults
    private let storageKey: String
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init(
        userDefaults: UserDefaults = .standard,
        storageKey: String = "userSettings.v1"
    ) {
        self.userDefaults = userDefaults
        self.storageKey = storageKey
    }

    func load() -> UserSettings {
        guard let data = userDefaults.data(forKey: storageKey) else {
            return .defaultValue
        }

        guard let decodedSettings = try? decoder.decode(UserSettings.self, from: data) else {
            return .defaultValue
        }

        return decodedSettings.normalized()
    }

    func save(_ settings: UserSettings) {
        guard let data = try? encoder.encode(settings.normalized()) else {
            return
        }

        userDefaults.set(data, forKey: storageKey)
    }

    @discardableResult
    func resetToDefaults() -> UserSettings {
        userDefaults.removeObject(forKey: storageKey)
        return .defaultValue
    }
}
