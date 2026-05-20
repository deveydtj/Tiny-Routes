import SwiftUI

/// Root view wired to the app coordinator.
@MainActor
struct ContentView: View {
    @StateObject private var coordinator = AppCoordinator()
    private let levelRepository = LevelRepository()
    private let progressService = ProgressService()

    var body: some View {
        ZStack {
            SpriteImage(name: "background")
                .scaledToFill()
                .ignoresSafeArea()

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
                    levelSelectView

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
            .foregroundColor(.black)
            .padding()
        }
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

    @ViewBuilder
    private var levelSelectView: some View {
        switch levelSelectState {
        case let .loaded(levels):
            LevelSelectScreen(
                levels: levels,
                progressService: progressService,
                onBackTapped: coordinator.backToMainMenu,
                onLevelSelected: { levelID in
                    coordinator.startGameplay(levelID: levelID)
                }
            )

        case .empty:
            unavailableLevelsView(message: "No bundled levels are available yet.")

        case let .failed(message):
            unavailableLevelsView(message: message)
        }
    }

    private var levelSelectState: LevelSelectState {
        do {
            let levels = try loadSortedLevels()
            return levels.isEmpty ? .empty : .loaded(levels)
        } catch {
            return .failed("Unable to load bundled levels. \(error.localizedDescription)")
        }
    }

    private func nextLevelID(after currentLevelID: String) -> String? {
        guard let levelIDs = try? loadSortedLevels().map(\.id),
            let currentIndex = levelIDs.firstIndex(of: currentLevelID) else {
            return nil
        }

        let nextIndex = currentIndex + 1
        guard nextIndex < levelIDs.count else {
            return nil
        }

        return levelIDs[nextIndex]
    }

    private func loadSortedLevels() throws -> [LevelData] {
        try levelRepository.loadAllLevels().sorted { $0.id < $1.id }
    }

    private func unavailableLevelsView(message: String) -> some View {
        VStack(spacing: 12) {
            Text("Levels Unavailable")
                .font(.title2)
            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            Button("Back", action: coordinator.backToMainMenu)
        }
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

private enum LevelSelectState {
    case loaded([LevelData])
    case empty
    case failed(String)
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
