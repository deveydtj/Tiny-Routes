import Foundation

struct UserSettings: Codable, Equatable {
    var isMusicEnabled: Bool
    var musicVolume: Double
    var areSoundEffectsEnabled: Bool
    var soundEffectsVolume: Double
    var areHapticsEnabled: Bool
    var showsTutorialTips: Bool
    var showsRouteHints: Bool
    var reducesExtraAnimations: Bool
    var confirmsBeforeRestarting: Bool
    var isDailyReminderEnabled: Bool
    var dailyReminderHour: Int
    var dailyReminderMinute: Int

    static let defaultValue = UserSettings()

    init(
        isMusicEnabled: Bool = true,
        musicVolume: Double = 0.75,
        areSoundEffectsEnabled: Bool = true,
        soundEffectsVolume: Double = 0.85,
        areHapticsEnabled: Bool = true,
        showsTutorialTips: Bool = true,
        showsRouteHints: Bool = true,
        reducesExtraAnimations: Bool = false,
        confirmsBeforeRestarting: Bool = false,
        isDailyReminderEnabled: Bool = false,
        dailyReminderHour: Int = 18,
        dailyReminderMinute: Int = 0
    ) {
        self.isMusicEnabled = isMusicEnabled
        self.musicVolume = Self.clampedVolume(musicVolume, fallback: 0.75)
        self.areSoundEffectsEnabled = areSoundEffectsEnabled
        self.soundEffectsVolume = Self.clampedVolume(soundEffectsVolume, fallback: 0.85)
        self.areHapticsEnabled = areHapticsEnabled
        self.showsTutorialTips = showsTutorialTips
        self.showsRouteHints = showsRouteHints
        self.reducesExtraAnimations = reducesExtraAnimations
        self.confirmsBeforeRestarting = confirmsBeforeRestarting
        self.isDailyReminderEnabled = isDailyReminderEnabled
        self.dailyReminderHour = Self.clamped(dailyReminderHour, to: 0...23)
        self.dailyReminderMinute = Self.clamped(dailyReminderMinute, to: 0...59)
    }

    func normalized() -> UserSettings {
        UserSettings(
            isMusicEnabled: isMusicEnabled,
            musicVolume: musicVolume,
            areSoundEffectsEnabled: areSoundEffectsEnabled,
            soundEffectsVolume: soundEffectsVolume,
            areHapticsEnabled: areHapticsEnabled,
            showsTutorialTips: showsTutorialTips,
            showsRouteHints: showsRouteHints,
            reducesExtraAnimations: reducesExtraAnimations,
            confirmsBeforeRestarting: confirmsBeforeRestarting,
            isDailyReminderEnabled: isDailyReminderEnabled,
            dailyReminderHour: dailyReminderHour,
            dailyReminderMinute: dailyReminderMinute
        )
    }

    private static func clampedVolume(_ value: Double, fallback: Double) -> Double {
        guard value.isFinite else { return fallback }
        return min(max(value, 0), 1)
    }

    private static func clamped(_ value: Int, to range: ClosedRange<Int>) -> Int {
        min(max(value, range.lowerBound), range.upperBound)
    }
}
