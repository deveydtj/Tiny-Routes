import Combine
import Foundation

@MainActor
final class UserSettingsService: ObservableObject {
    @Published private(set) var settings: UserSettings

    private let repository: UserSettingsRepository

    init(repository: UserSettingsRepository = UserSettingsRepository()) {
        self.repository = repository
        self.settings = repository.load()
    }

    func setMusicEnabled(_ isEnabled: Bool) {
        update { $0.isMusicEnabled = isEnabled }
    }

    func setMusicVolume(_ volume: Double) {
        update { $0.musicVolume = volume }
    }

    func setSoundEffectsEnabled(_ isEnabled: Bool) {
        update { $0.areSoundEffectsEnabled = isEnabled }
    }

    func setSoundEffectsVolume(_ volume: Double) {
        update { $0.soundEffectsVolume = volume }
    }

    func setHapticsEnabled(_ isEnabled: Bool) {
        update { $0.areHapticsEnabled = isEnabled }
    }

    func setShowsTutorialTips(_ showsTutorialTips: Bool) {
        update { $0.showsTutorialTips = showsTutorialTips }
    }

    func setShowsRouteHints(_ showsRouteHints: Bool) {
        update { $0.showsRouteHints = showsRouteHints }
    }

    func setReducesExtraAnimations(_ reducesExtraAnimations: Bool) {
        update { $0.reducesExtraAnimations = reducesExtraAnimations }
    }

    func setConfirmsBeforeRestarting(_ confirmsBeforeRestarting: Bool) {
        update { $0.confirmsBeforeRestarting = confirmsBeforeRestarting }
    }

    func setDailyReminderEnabled(_ isEnabled: Bool) {
        update { $0.isDailyReminderEnabled = isEnabled }
    }

    func setDailyReminderTime(hour: Int, minute: Int) {
        update {
            $0.dailyReminderHour = hour
            $0.dailyReminderMinute = minute
        }
    }

    func resetToDefaults() {
        settings = repository.resetToDefaults()
    }

    private func update(_ transform: (inout UserSettings) -> Void) {
        var updatedSettings = settings
        transform(&updatedSettings)
        updatedSettings = updatedSettings.normalized()
        settings = updatedSettings
        repository.save(updatedSettings)
    }
}
