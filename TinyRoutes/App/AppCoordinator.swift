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
        case .boot, .gameplay, .experiments, .experiment:
            nil
        }
    }

    func launch() {
        state = .mainMenu
        #if DEBUG
        // `-OpenLevelSelect` starts on the level map, for screenshots.
        if ProcessInfo.processInfo.arguments.contains("-OpenLevelSelect") { state = .levelSelect }
        // `-OpenScreen shop|profile|settings` starts on that menu, likewise.
        switch UserDefaults.standard.string(forKey: "OpenScreen") {
        case "shop": state = .shop
        case "profile": state = .profile
        case "settings": openSettings()
        default: break
        }
        #endif
        #if DEBUG || MULTIVAN_INTERNAL
        // Profiling launches go straight into their level; see MultiVanAutoplay.
        if let autoplay = MultiVanAutoplay.launchConfiguration {
            let isExperiment = autoplay.levelID.hasPrefix(MultiVanLevelRepository.experimentPrefix)
            state = isExperiment ? .experiment(levelID: autoplay.levelID) : .gameplay(levelID: autoplay.levelID)
        }
        // `-OpenExperiment <id>` starts on that experiment board; `-OpenExperiments` on their list.
        if let id = UserDefaults.standard.string(forKey: "OpenExperiment") { state = .experiment(levelID: id) }
        if ProcessInfo.processInfo.arguments.contains("-OpenExperiments") { state = .experiments }
        #endif
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
        case .boot, .gameplay, .experiments, .experiment:
            settingsReturnState = .mainMenu
        }

        state = .settings
    }

    func openExperiments() {
        state = .experiments
    }

    func startExperiment(levelID: String) {
        state = .experiment(levelID: levelID)
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
