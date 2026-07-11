import Foundation

/// Selects the contract used to decide which route switches a player may change.
enum SwitchInteractionMode: String, Codable, Equatable {
    case legacyGlobal
    case liveLookahead
}

/// Versioned gameplay settings serialized with a level.
struct LevelRules: Codable, Equatable {
    static let legacyDefaults = LevelRules(
        switchInteractionMode: .legacyGlobal,
        switchLookaheadSeconds: 1.35,
        switchTapCooldownSeconds: 0.12
    )

    var switchInteractionMode: SwitchInteractionMode
    var switchLookaheadSeconds: Double
    var switchTapCooldownSeconds: Double
}
