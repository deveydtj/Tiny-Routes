import Combine
import Foundation

/// Owns top-level navigation and coordinates transitions between app states.
@MainActor
final class AppCoordinator: ObservableObject {
    @Published private(set) var state: AppState = .boot

    var selectedBottomTab: TRBottomTab? {
        switch state {
        case .mainMenu:
            .home
        case .levelSelect:
            .levels
        case .shop:
            .shop
        case .profile:
            .profile
        case .settings:
            .profile
        case .boot, .gameplay, .pause, .levelComplete, .levelFailed:
            nil
        }
    }

    func launch() {
        state = .mainMenu
    }

    func openLevelSelect() {
        state = .levelSelect
    }

    func startGameplay(levelID: String) {
        state = .gameplay(levelID: levelID)
    }

    func pauseGameplay() {
        guard case let .gameplay(levelID) = state else { return }
        state = .pause(levelID: levelID)
    }

    func resumeGameplay() {
        guard case let .pause(levelID) = state else { return }
        state = .gameplay(levelID: levelID)
    }

    func restartGameplay() {
        switch state {
        case let .gameplay(levelID),
             let .pause(levelID),
             let .levelComplete(levelID, _, _, _),
             let .levelFailed(levelID, _, _, _, _):
            state = .gameplay(levelID: levelID)
        default:
            break
        }
    }

    func exitGameplayToMenu() {
        backToMainMenu()
    }

    func exitGameplayToLevels() {
        openLevelSelect()
    }

    func completeLevel(elapsedTime: TimeInterval, tapCount: Int) {
        switch state {
        case let .gameplay(levelID), let .pause(levelID):
            state = .levelComplete(levelID: levelID, elapsedTime: elapsedTime, tapCount: tapCount, presentationID: UUID())
        default:
            break
        }
    }

    func failLevel(reason: LevelFailureReason, elapsedTime: TimeInterval, tapCount: Int) {
        switch state {
        case let .gameplay(levelID), let .pause(levelID):
            state = .levelFailed(levelID: levelID, reason: reason, elapsedTime: elapsedTime, tapCount: tapCount, presentationID: UUID())
        default:
            break
        }
    }

    func openShop() {
        state = .shop
    }

    func openProfile() {
        state = .profile
    }

    func openSettings() {
        state = .settings
    }

    func selectTab(_ tab: TRBottomTab) {
        switch tab {
        case .home:
            state = .mainMenu
        case .levels:
            state = .levelSelect
        case .shop:
            state = .shop
        case .profile:
            openProfile()
        }
    }

    func backToMainMenu() {
        state = .mainMenu
    }
}
