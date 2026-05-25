import SwiftUI

/// Root view wired to the app coordinator.
@MainActor
struct ContentView: View {
    @StateObject private var coordinator = AppCoordinator()
    @StateObject private var settingsService = UserSettingsService()
    @State private var profileRevision = 0

    private let saveDataRepository: SaveDataRepository
    private let levelRepository: LevelRepository
    private let progressService: ProgressService
    private let economyService: EconomyService
    private let cosmeticService: CosmeticService
    private let profileSummaryService: ProfileSummaryService
    private let bottomNavigationReservedHeight: CGFloat = 96

    init() {
        let repository = SaveDataRepository()
        let levelRepository = LevelRepository()
        let progressService = ProgressService(repository: repository)
        let economyService = EconomyService(repository: repository)
        let cosmeticService = CosmeticService(
            repository: repository,
            economyService: economyService
        )

        self.saveDataRepository = repository
        self.levelRepository = levelRepository
        self.progressService = progressService
        self.economyService = economyService
        self.cosmeticService = cosmeticService
        self.profileSummaryService = ProfileSummaryService(
            repository: repository,
            progressService: progressService,
            economyService: economyService,
            cosmeticService: cosmeticService,
            levelRepository: levelRepository
        )
    }

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
                            startGameplayIfUnlocked(levelID: nextLevelID)
                        },
                        onExitTapped: coordinator.exitGameplayToMenu,
                        onBackToLevelsTapped: coordinator.exitGameplayToLevels,
                        onHomeTapped: coordinator.backToMainMenu,
                        onShareTapped: {},
                        onProfileChanged: handleProfileChanged,
                        nextLevelID: nextLevelID,
                        levelRepository: levelRepository,
                        progressService: progressService,
                        economyService: economyService,
                        saveDataRepository: saveDataRepository
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
                        canAdvanceToNextLevel: nextLevelID.map(progressService.isLevelUnlocked) ?? false,
                        onRestartTapped: coordinator.restartGameplay,
                        onNextLevelTapped: {
                            guard let nextLevelID else { return }
                            startGameplayIfUnlocked(levelID: nextLevelID)
                        },
                        onExitTapped: coordinator.exitGameplayToMenu,
                        onBackToLevelsTapped: coordinator.exitGameplayToLevels,
                        onHomeTapped: coordinator.backToMainMenu,
                        onShareTapped: {},
                        onUseHintTapped: {},
                        onSkipLevelTapped: {
                            guard let nextLevelID else { return }
                            startGameplayIfUnlocked(levelID: nextLevelID)
                        },
                        nextLevelID: nextLevelID,
                        levelRepository: levelRepository,
                        progressService: progressService,
                        economyService: economyService,
                        saveDataRepository: saveDataRepository
                    )

                case .shop:
                    ShopScreen(
                        coinTotal: currentCoinTotal,
                        onSettingsTapped: coordinator.openSettings,
                        onAddCurrencyTapped: coordinator.openShop,
                        cosmeticService: cosmeticService,
                        economyService: economyService,
                        onProfileChanged: handleProfileChanged
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
                    SettingsScreen(
                        settingsService: settingsService,
                        progressService: progressService,
                        playerName: profileSummaryService.makeSummary().playerName,
                        onBackTapped: coordinator.closeSettings,
                        onEditProfileTapped: {},
                        onCustomizeTapped: coordinator.openShop,
                        onRestorePurchasesTapped: {},
                        onRemoveAdsTapped: {},
                        onContactSupportTapped: {},
                        onRateAppTapped: {},
                        onPrivacyPolicyTapped: {},
                        onTermsTapped: {},
                        onProfileChanged: handleProfileChanged
                    )
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
        _ = profileRevision
        return economyService.coinTotal()
    }

    private var isFullBleedScreenVisible: Bool {
        switch coordinator.state {
        case .levelSelect, .shop, .profile, .settings, .levelComplete, .levelFailed:
            return true
        default:
            return false
        }
    }

    private var isStandardMenuHeaderScreenVisible: Bool {
        switch coordinator.state {
        case .levelSelect, .shop, .profile, .settings:
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
                currentStreakDays: saveDataRepository.load().currentStreakDays,
                onLevelSelected: { levelID in
                    startGameplayIfUnlocked(levelID: levelID)
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

    private func startGameplayIfUnlocked(levelID: String) {
        guard progressService.isLevelUnlocked(levelID) else {
            return
        }

        coordinator.startGameplay(levelID: levelID)
    }

    private func handleProfileChanged() {
        profileRevision += 1
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
