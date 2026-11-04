import Combine
import Foundation

/// Owns top-level navigation and coordinates transitions between app states.
@MainActor
final class AppCoordinator: ObservableObject {
    @Published private(set) var state: AppState = .boot

    private var settingsReturnState: AppState = .mainMenu

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
            nil
        case .boot, .gameplay:
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

    func exitGameplayToLevels() {
        openLevelSelect()
    }

    func openShop() {
        state = .shop
    }

    func openProfile() {
        state = .profile
    }

    func openSettings() {
        switch state {
        case .mainMenu, .levelSelect, .shop, .profile:
            settingsReturnState = state
        case .settings:
            break
        case .boot, .gameplay:
            settingsReturnState = .mainMenu
        }

        state = .settings
    }

    func closeSettings() {
        guard state == .settings else { return }
        state = settingsReturnState
        settingsReturnState = .mainMenu
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
