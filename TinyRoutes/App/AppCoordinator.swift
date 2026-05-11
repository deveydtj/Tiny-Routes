import Combine

/// Owns top-level navigation and coordinates transitions between app states.
@MainActor
final class AppCoordinator: ObservableObject {
    @Published private(set) var state: AppState = .boot

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
             let .levelComplete(levelID),
             let .levelFailed(levelID):
            state = .gameplay(levelID: levelID)
        default:
            break
        }
    }

    func exitGameplayToMenu() {
        state = .mainMenu
    }

    func completeLevel() {
        switch state {
        case let .gameplay(levelID), let .pause(levelID):
            state = .levelComplete(levelID: levelID)
        default:
            break
        }
    }

    func failLevel() {
        switch state {
        case let .gameplay(levelID), let .pause(levelID):
            state = .levelFailed(levelID: levelID)
        default:
            break
        }
    }

    func openShop() {
        state = .shop
    }

    func openSettings() {
        state = .settings
    }

    func backToMainMenu() {
        state = .mainMenu
    }
}
