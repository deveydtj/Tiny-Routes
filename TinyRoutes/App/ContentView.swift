import SwiftUI

/// Root view wired to the app coordinator.
@MainActor
struct ContentView: View {
    @StateObject private var coordinator = AppCoordinator()
    private let levelRepository = LevelRepository()
    private let progressService = ProgressService()
    private let profileSummaryService = ProfileSummaryService()
    private let bottomNavigationReservedHeight: CGFloat = 96

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
                        onPlayTapped: coordinator.openLevelSelect
                    )

                case .levelSelect:
                    levelSelectView

                case let .gameplay(levelID), let .pause(levelID):
                    gameplayView(levelID: levelID, isPaused: coordinator.state.isPaused)

                case let .levelComplete(levelID, elapsedTime, tapCount, presentationID):
                    let nextLevelID = nextLevelID(after: levelID)
                    ResultScreen(
                        levelID: levelID,
                        result: .completed,
                        presentationID: presentationID,
                        elapsedTime: elapsedTime,
                        tapCount: tapCount,
                        failureReason: nil,
                        canAdvanceToNextLevel: nextLevelID != nil,
                        onRestartTapped: coordinator.restartGameplay,
                        onNextLevelTapped: {
                            guard let nextLevelID else { return }
                            coordinator.startGameplay(levelID: nextLevelID)
                        },
                        onExitTapped: coordinator.exitGameplayToMenu,
                        onBackToLevelsTapped: coordinator.exitGameplayToLevels,
                        onHomeTapped: coordinator.backToMainMenu,
                        onShareTapped: {}
                    )

                case let .levelFailed(levelID, reason, elapsedTime, tapCount, presentationID):
                    let nextLevelID = nextLevelID(after: levelID)
                    ResultScreen(
                        levelID: levelID,
                        result: .failed,
                        presentationID: presentationID,
                        elapsedTime: elapsedTime,
                        tapCount: tapCount,
                        failureReason: reason,
                        canAdvanceToNextLevel: nextLevelID != nil,
                        onRestartTapped: coordinator.restartGameplay,
                        onNextLevelTapped: {
                            guard let nextLevelID else { return }
                            coordinator.startGameplay(levelID: nextLevelID)
                        },
                        onExitTapped: coordinator.exitGameplayToMenu,
                        onBackToLevelsTapped: coordinator.exitGameplayToLevels,
                        onHomeTapped: coordinator.backToMainMenu,
                        onShareTapped: {},
                        onUseHintTapped: {},
                        onSkipLevelTapped: {
                            guard let nextLevelID else { return }
                            coordinator.startGameplay(levelID: nextLevelID)
                        }
                    )

                case .shop:
                    ShopScreen(
                        coinTotal: currentCoinTotal,
                        onSettingsTapped: coordinator.openSettings,
                        onAddCurrencyTapped: coordinator.openShop
                    )

                case .profile:
                    ProfileScreen(
                        summary: profileSummaryService.makeSummary(),
                        onSettingsTapped: coordinator.openSettings,
                        onAddCurrencyTapped: coordinator.openShop,
                        onEditProfileTapped: {},
                        onAchievementsTapped: {},
                        onCustomizeTapped: coordinator.openShop
                    )

                case .settings:
                    SettingsScreen()
                }
            }
            .foregroundColor(.black)
            .padding(isFullBleedScreenVisible ? 0 : 16)
            .padding(.bottom, selectedBottomTab == nil ? 0 : bottomNavigationReservedHeight)

            if let selectedBottomTab {
                VStack {
                    Spacer()
                    TRBottomNavigationBar(
                        selectedTab: selectedBottomTab,
                        onTabSelected: coordinator.selectTab
                    )
                }
            }
        }
        .statusBarHidden(isStandardMenuHeaderScreenVisible)
    }

    private var selectedBottomTab: TRBottomTab? {
        coordinator.selectedBottomTab
    }

    private var currentCoinTotal: Int {
        profileSummaryService.makeSummary().coinTotal
    }

    private var isFullBleedScreenVisible: Bool {
        switch coordinator.state {
        case .levelSelect, .shop, .profile, .levelComplete, .levelFailed:
            return true
        default:
            return false
        }
    }

    private var isStandardMenuHeaderScreenVisible: Bool {
        switch coordinator.state {
        case .levelSelect, .shop, .profile:
            return true
        default:
            return false
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
                coinTotal: currentCoinTotal,
                onLevelSelected: { levelID in
                    coordinator.startGameplay(levelID: levelID)
                },
                onSettingsTapped: coordinator.openSettings,
                onAddCurrencyTapped: coordinator.openShop,
                progressService: progressService
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
