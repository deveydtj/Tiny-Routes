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
}
