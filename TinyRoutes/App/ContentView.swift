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

            case let .gameplay(levelID), let .pause(levelID):
                gameplayView(levelID: levelID, isPaused: coordinator.state.isPaused)

            case let .levelComplete(levelID, elapsedTime):
                ResultScreen(
                    levelID: levelID,
                    result: .completed,
                    elapsedTime: elapsedTime,
                    failureReason: nil,
                    onRestartTapped: coordinator.restartGameplay,
                    onExitTapped: coordinator.exitGameplayToMenu
                )

            case let .levelFailed(levelID, reason, elapsedTime):
                ResultScreen(
                    levelID: levelID,
                    result: .failed,
                    elapsedTime: elapsedTime,
                    failureReason: reason,
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

private extension AppState {
    var isPaused: Bool {
        if case .pause = self {
            return true
        }
        return false
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
