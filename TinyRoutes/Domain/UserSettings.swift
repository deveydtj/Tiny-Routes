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
    var boardStyle: MultiVanBoardStyle
    var usesFlatBoardInLowPowerMode: Bool

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
        dailyReminderMinute: Int = 0,
        // 3D by default; 2D stays as a choice and as the Low Power Mode fallback.
        boardStyle: MultiVanBoardStyle = .diorama,
        usesFlatBoardInLowPowerMode: Bool = true
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
        self.boardStyle = boardStyle
        self.usesFlatBoardInLowPowerMode = usesFlatBoardInLowPowerMode
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
            dailyReminderMinute: dailyReminderMinute,
            boardStyle: boardStyle,
            usesFlatBoardInLowPowerMode: usesFlatBoardInLowPowerMode
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

extension UserSettings {
    /// Missing keys take their defaults, so settings saved before a field existed
    /// still load instead of resetting everything.
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let defaults = UserSettings.defaultValue
        self.init(
            isMusicEnabled: try container.decodeIfPresent(Bool.self, forKey: .isMusicEnabled) ?? defaults.isMusicEnabled,
            musicVolume: try container.decodeIfPresent(Double.self, forKey: .musicVolume) ?? defaults.musicVolume,
            areSoundEffectsEnabled: try container.decodeIfPresent(Bool.self, forKey: .areSoundEffectsEnabled)
                ?? defaults.areSoundEffectsEnabled,
            soundEffectsVolume: try container.decodeIfPresent(Double.self, forKey: .soundEffectsVolume)
                ?? defaults.soundEffectsVolume,
            areHapticsEnabled: try container.decodeIfPresent(Bool.self, forKey: .areHapticsEnabled) ?? defaults.areHapticsEnabled,
            showsTutorialTips: try container.decodeIfPresent(Bool.self, forKey: .showsTutorialTips) ?? defaults.showsTutorialTips,
            showsRouteHints: try container.decodeIfPresent(Bool.self, forKey: .showsRouteHints) ?? defaults.showsRouteHints,
            reducesExtraAnimations: try container.decodeIfPresent(Bool.self, forKey: .reducesExtraAnimations)
                ?? defaults.reducesExtraAnimations,
            confirmsBeforeRestarting: try container.decodeIfPresent(Bool.self, forKey: .confirmsBeforeRestarting)
                ?? defaults.confirmsBeforeRestarting,
            isDailyReminderEnabled: try container.decodeIfPresent(Bool.self, forKey: .isDailyReminderEnabled)
                ?? defaults.isDailyReminderEnabled,
            dailyReminderHour: try container.decodeIfPresent(Int.self, forKey: .dailyReminderHour) ?? defaults.dailyReminderHour,
            dailyReminderMinute: try container.decodeIfPresent(Int.self, forKey: .dailyReminderMinute)
                ?? defaults.dailyReminderMinute,
            // A style this build doesn't know, from a newer TestFlight build, falls back
            // to the default rather than discarding every other setting.
            boardStyle: (try? container.decodeIfPresent(MultiVanBoardStyle.self, forKey: .boardStyle)) ?? defaults.boardStyle,
            usesFlatBoardInLowPowerMode: try container.decodeIfPresent(Bool.self, forKey: .usesFlatBoardInLowPowerMode)
                ?? defaults.usesFlatBoardInLowPowerMode
        )
    }
}
