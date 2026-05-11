import SwiftUI

/// Root view wired to the app coordinator.
struct ContentView: View {
    @StateObject private var coordinator = AppCoordinator()

    var body: some View {
        Group {
            switch coordinator.state {
            case .boot:
                ProgressView("Loading Tiny Routes…")
                    .task {
                        coordinator.launch()
                    }

            case .mainMenu:
                HomeScreen(
                    onPlayTapped: coordinator.openLevelSelect,
                    onShopTapped: coordinator.openShop,
                    onSettingsTapped: coordinator.openSettings
                )

            case .levelSelect:
                LevelSelectScreen(
                    onBackTapped: coordinator.backToMainMenu,
                    onLevelSelected: { levelID in
                        coordinator.startGameplay(levelID: levelID)
                    }
                )

            case let .gameplay(levelID):
                GameplayScreen(
                    levelID: levelID,
                    isPaused: false,
                    onPauseTapped: coordinator.pauseGameplay,
                    onCompleteTapped: coordinator.completeLevel,
                    onFailTapped: coordinator.failLevel,
                    onExitTapped: coordinator.exitGameplayToMenu
                )

            case let .pause(levelID):
                GameplayScreen(
                    levelID: levelID,
                    isPaused: true,
                    onPauseTapped: coordinator.resumeGameplay,
                    onCompleteTapped: coordinator.completeLevel,
                    onFailTapped: coordinator.failLevel,
                    onExitTapped: coordinator.exitGameplayToMenu
                )

            case let .levelComplete(levelID):
                ResultScreen(
                    levelID: levelID,
                    result: .completed,
                    onRestartTapped: coordinator.restartGameplay,
                    onExitTapped: coordinator.exitGameplayToMenu
                )

            case let .levelFailed(levelID):
                ResultScreen(
                    levelID: levelID,
                    result: .failed,
                    onRestartTapped: coordinator.restartGameplay,
                    onExitTapped: coordinator.exitGameplayToMenu
                )

            case .shop:
                ShopScreen(onBackTapped: coordinator.backToMainMenu)

            case .settings:
                SettingsScreen(onBackTapped: coordinator.backToMainMenu)
            }
        }
        .padding()
    }
}

#Preview {
    ContentView()
}
