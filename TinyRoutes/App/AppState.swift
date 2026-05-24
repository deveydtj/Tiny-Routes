import Foundation

/// High-level states of the Tiny Routes application.
enum AppState: Equatable {
    case boot
    case mainMenu
    case levelSelect
    case gameplay(levelID: String)
    case pause(levelID: String)
    case levelComplete(levelID: String, elapsedTime: TimeInterval, tapCount: Int, presentationID: UUID)
    case levelFailed(levelID: String, reason: LevelFailureReason, elapsedTime: TimeInterval, tapCount: Int, presentationID: UUID)
    case shop
    case profile
    case settings
}
