import Foundation

/// High-level states of the Tiny Routes application.
enum AppState: Equatable {
    case boot
    case mainMenu
    case levelSelect
    case gameplay(levelID: String)
    case shop
    case profile
    case settings
    /// Boards on trial, listed for internal builds only.
    case experiments
    /// One experiment board in play. It records no progress and earns nothing.
    case experiment(levelID: String)
}
