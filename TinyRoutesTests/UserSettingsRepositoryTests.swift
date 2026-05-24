import XCTest
@testable import TinyRoutes

final class UserSettingsRepositoryTests: XCTestCase {
    func testLoadReturnsDefaultsWhenNoDataExists() {
        let repository = makeRepository()

        XCTAssertEqual(repository.load(), .defaultValue)
    }

    func testSavedSettingsLoadBackCorrectly() {
        let repository = makeRepository()
        let settings = UserSettings(
            isMusicEnabled: false,
            musicVolume: 0.33,
            areSoundEffectsEnabled: false,
            soundEffectsVolume: 0.44,
            areHapticsEnabled: false,
            showsTutorialTips: false,
            showsRouteHints: false,
            reducesExtraAnimations: true,
            confirmsBeforeRestarting: true,
            isDailyReminderEnabled: true,
            dailyReminderHour: 8,
            dailyReminderMinute: 30
        )

        repository.save(settings)

        XCTAssertEqual(repository.load(), settings)
    }

    func testCorruptStoredDataReturnsDefaults() {
        let storageKey = "userSettings.repository.corrupt"
        let defaults = makeDefaults()
        defaults.set(Data("not-json".utf8), forKey: storageKey)
        let repository = UserSettingsRepository(userDefaults: defaults, storageKey: storageKey)

        XCTAssertEqual(repository.load(), .defaultValue)
    }

    func testDecodedOutOfRangeSettingsAreNormalized() {
        let storageKey = "userSettings.repository.outOfRange"
        let defaults = makeDefaults()
        let json = """
        {
          "isMusicEnabled": true,
          "musicVolume": -4,
          "areSoundEffectsEnabled": true,
          "soundEffectsVolume": 3,
          "areHapticsEnabled": true,
          "showsTutorialTips": true,
          "showsRouteHints": true,
          "reducesExtraAnimations": false,
          "confirmsBeforeRestarting": false,
          "isDailyReminderEnabled": true,
          "dailyReminderHour": 99,
          "dailyReminderMinute": -6
        }
        """
        defaults.set(Data(json.utf8), forKey: storageKey)
        let repository = UserSettingsRepository(userDefaults: defaults, storageKey: storageKey)

        let settings = repository.load()

        XCTAssertEqual(settings.musicVolume, 0)
        XCTAssertEqual(settings.soundEffectsVolume, 1)
        XCTAssertEqual(settings.dailyReminderHour, 23)
        XCTAssertEqual(settings.dailyReminderMinute, 0)
    }

    func testResetClearsCustomValues() {
        let repository = makeRepository()
        repository.save(UserSettings(isMusicEnabled: false, musicVolume: 0.12))

        let resetSettings = repository.resetToDefaults()

        XCTAssertEqual(resetSettings, .defaultValue)
        XCTAssertEqual(repository.load(), .defaultValue)
    }

    private func makeRepository(
        storageKey: String = "userSettings.repository.test"
    ) -> UserSettingsRepository {
        UserSettingsRepository(userDefaults: makeDefaults(), storageKey: storageKey)
    }

    private func makeDefaults() -> UserDefaults {
        let suiteName = "UserSettingsRepositoryTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        addTeardownBlock {
            defaults.removePersistentDomain(forName: suiteName)
        }
        return defaults
    }
}
