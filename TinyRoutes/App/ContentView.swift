import SwiftUI

/// Root view wired to the app coordinator.
@MainActor
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
                gameplayView(levelID: levelID, isPaused: false)

            case let .pause(levelID):
                gameplayView(levelID: levelID, isPaused: true)

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

    @ViewBuilder
    private func gameplayView(levelID: String, isPaused: Bool) -> some View {
        GameplayScreen(
            levelID: levelID,
            isPaused: isPaused,
            onPauseResumeTapped: isPaused ? coordinator.resumeGameplay : coordinator.pauseGameplay,
            onCompleteTapped: coordinator.completeLevel,
            onFailTapped: coordinator.failLevel,
            onExitTapped: coordinator.exitGameplayToMenu
        )
    }
}

#Preview {
    ContentView()
}
