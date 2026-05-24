import XCTest
@testable import TinyRoutes

final class UserSettingsServiceTests: XCTestCase {
    func testUserSettingsDefaultValue() {
        let settings = UserSettings.defaultValue

        XCTAssertTrue(settings.isMusicEnabled)
        XCTAssertEqual(settings.musicVolume, 0.75)
        XCTAssertTrue(settings.areSoundEffectsEnabled)
        XCTAssertEqual(settings.soundEffectsVolume, 0.85)
        XCTAssertTrue(settings.areHapticsEnabled)
        XCTAssertTrue(settings.showsTutorialTips)
        XCTAssertTrue(settings.showsRouteHints)
        XCTAssertFalse(settings.reducesExtraAnimations)
        XCTAssertFalse(settings.confirmsBeforeRestarting)
        XCTAssertFalse(settings.isDailyReminderEnabled)
        XCTAssertEqual(settings.dailyReminderHour, 18)
        XCTAssertEqual(settings.dailyReminderMinute, 0)
    }

    func testUserSettingsNormalizationClampsInvalidValues() {
        let settings = UserSettings(
            musicVolume: -2,
            soundEffectsVolume: 9,
            dailyReminderHour: 99,
            dailyReminderMinute: -4
        )

        XCTAssertEqual(settings.musicVolume, 0)
        XCTAssertEqual(settings.soundEffectsVolume, 1)
        XCTAssertEqual(settings.dailyReminderHour, 23)
        XCTAssertEqual(settings.dailyReminderMinute, 0)
    }

    func testUserSettingsNormalizationUsesFallbackForNonFiniteVolumes() {
        let settings = UserSettings(
            musicVolume: .nan,
            soundEffectsVolume: .infinity
        )

        XCTAssertEqual(settings.musicVolume, 0.75)
        XCTAssertEqual(settings.soundEffectsVolume, 0.85)
    }

    @MainActor
    func testServiceUpdateMethodsPersistValues() {
        let repository = makeRepository()
        let service = UserSettingsService(repository: repository)

        service.setMusicEnabled(false)
        service.setMusicVolume(0.2)
        service.setSoundEffectsEnabled(false)
        service.setSoundEffectsVolume(0.3)
        service.setHapticsEnabled(false)
        service.setShowsTutorialTips(false)
        service.setShowsRouteHints(false)
        service.setReducesExtraAnimations(true)
        service.setConfirmsBeforeRestarting(true)
        service.setDailyReminderEnabled(true)
        service.setDailyReminderTime(hour: 7, minute: 45)

        let loadedSettings = repository.load()
        XCTAssertFalse(loadedSettings.isMusicEnabled)
        XCTAssertEqual(loadedSettings.musicVolume, 0.2)
        XCTAssertFalse(loadedSettings.areSoundEffectsEnabled)
        XCTAssertEqual(loadedSettings.soundEffectsVolume, 0.3)
        XCTAssertFalse(loadedSettings.areHapticsEnabled)
        XCTAssertFalse(loadedSettings.showsTutorialTips)
        XCTAssertFalse(loadedSettings.showsRouteHints)
        XCTAssertTrue(loadedSettings.reducesExtraAnimations)
        XCTAssertTrue(loadedSettings.confirmsBeforeRestarting)
        XCTAssertTrue(loadedSettings.isDailyReminderEnabled)
        XCTAssertEqual(loadedSettings.dailyReminderHour, 7)
        XCTAssertEqual(loadedSettings.dailyReminderMinute, 45)
    }

    @MainActor
    func testServiceReloadsSavedValues() {
        let repository = makeRepository()
        let savedSettings = UserSettings(isMusicEnabled: false, musicVolume: 0.4)
        repository.save(savedSettings)

        let service = UserSettingsService(repository: repository)

        XCTAssertEqual(service.settings, savedSettings)
    }

    @MainActor
    func testServiceResetReturnsDefaults() {
        let repository = makeRepository()
        let service = UserSettingsService(repository: repository)
        service.setMusicEnabled(false)

        service.resetToDefaults()

        XCTAssertEqual(service.settings, .defaultValue)
        XCTAssertEqual(repository.load(), .defaultValue)
    }

    private func makeRepository() -> UserSettingsRepository {
        let suiteName = "UserSettingsServiceTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        addTeardownBlock {
            defaults.removePersistentDomain(forName: suiteName)
        }
        return UserSettingsRepository(userDefaults: defaults, storageKey: "userSettings.service.test")
    }
}
