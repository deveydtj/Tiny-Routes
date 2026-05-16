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

            case let .levelComplete(levelID, elapsedTime, tapCount):
                let nextLevelID = nextLevelID(after: levelID)
                ResultScreen(
                    levelID: levelID,
                    result: .completed,
                    elapsedTime: elapsedTime,
                    tapCount: tapCount,
                    failureReason: nil,
                    canAdvanceToNextLevel: nextLevelID != nil,
                    onRestartTapped: coordinator.restartGameplay,
                    onNextLevelTapped: {
                        guard let nextLevelID else { return }
                        coordinator.startGameplay(levelID: nextLevelID)
                    },
                    onExitTapped: coordinator.exitGameplayToMenu
                )

            case let .levelFailed(levelID, reason, elapsedTime, tapCount):
                ResultScreen(
                    levelID: levelID,
                    result: .failed,
                    elapsedTime: elapsedTime,
                    tapCount: tapCount,
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

    private func nextLevelID(after currentLevelID: String) -> String? {
        let levelRepository = LevelRepository()
        guard let levelIDs = try? levelRepository.loadAllLevels()
            .map(\.id)
            .sorted(),
            let currentIndex = levelIDs.firstIndex(of: currentLevelID) else {
            return nil
        }

        let nextIndex = currentIndex + 1
        guard nextIndex < levelIDs.count else {
            return nil
        }

        return levelIDs[nextIndex]
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
