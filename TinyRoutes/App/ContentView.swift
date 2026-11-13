import SwiftUI

/// Root view wired to the app coordinator.
@MainActor
struct ContentView: View {
    @StateObject private var coordinator = AppCoordinator()
    @StateObject private var settingsService = UserSettingsService()
    @State private var profileRevision = 0

    private let saveDataRepository: SaveDataRepository
    private let levelRepository: MultiVanLevelRepository
    private let progressService: ProgressService
    private let economyService: EconomyService
    private let cosmeticService: CosmeticService
    private let dailyBonusService: DailyBonusService
    private let profileSummaryService: ProfileSummaryService
    private let bottomNavigationReservedHeight: CGFloat = 96

    init() {
        let repository = SaveDataRepository()
        let levelRepository = MultiVanLevelRepository()
        let progressService = ProgressService(repository: repository)
        let economyService = EconomyService(repository: repository)
        let cosmeticService = CosmeticService(
            repository: repository,
            economyService: economyService
        )
        let dailyBonusService = DailyBonusService(
            repository: repository,
            economyService: economyService
        )

        self.saveDataRepository = repository
        self.levelRepository = levelRepository
        self.progressService = progressService
        self.economyService = economyService
        self.cosmeticService = cosmeticService
        self.dailyBonusService = dailyBonusService
        self.profileSummaryService = ProfileSummaryService(
            repository: repository,
            progressService: progressService,
            economyService: economyService,
            cosmeticService: cosmeticService
        )
    }

    var body: some View {
        ZStack {
            // A level paints its own backdrop. The menu art fills past the safe
            // area, which sizes this stack to the whole screen and would put a
            // level's Levels button under the clock.
            if coordinator.state == .levelSelect || coordinator.state == .mainMenu {
                // The village's sky, reaching down behind the tab bar.
                TRVillageSky()
            } else if coordinator.state == .shop || coordinator.state == .profile || coordinator.state == .settings
                        || coordinator.state == .experiments {
                // The same sky with clouds, and hills behind the tab bar.
                TRCozySkyBackground()
            } else if !isGameplayVisible {
                // Hung over a clear screen-sized layer, so the art's overflow
                // doesn't stretch this stack past the bottom and push the tab bar
                // off screen.
                Color.clear
                    .overlay { SpriteImage(name: "background").scaledToFill() }
                    .clipped()
                    .ignoresSafeArea()
            }

            Group {
                switch coordinator.state {
                case .boot:
                    ProgressView("Loading Tiny Routes…")
                        .task {
                            if let levels = try? loadSortedLevels() {
                                progressService.unlockLevelsFollowingCompleted(in: levels.map(\.id))
                            }
                            coordinator.launch()
                        }

                case .mainMenu:
                    HomeScreen(onPlayTapped: coordinator.openLevelSelect)

                case .levelSelect:
                    levelSelectView

                case let .gameplay(levelID):
                    gameplayView(levelID: levelID)

                case .shop:
                    ShopScreen(
                        coinTotal: currentCoinTotal,
                        onSettingsTapped: coordinator.openSettings,
                        onAddCurrencyTapped: coordinator.openShop,
                        cosmeticService: cosmeticService,
                        economyService: economyService,
                        dailyBonusService: dailyBonusService,
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
                        onProfileChanged: handleProfileChanged,
                        onExperimentsTapped: experimentsAction
                    )

                case .experiments:
                    MultiVanExperimentsScreen(
                        levels: (try? levelRepository.loadExperimentLevels()) ?? [],
                        onSelect: coordinator.startExperiment,
                        onBack: coordinator.openSettings
                    )

                case let .experiment(levelID):
                    experimentView(levelID: levelID)
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
        case .mainMenu, .levelSelect, .gameplay, .shop, .profile, .settings, .experiments, .experiment:
            return true
        default:
            return false
        }
    }

    private var isGameplayVisible: Bool {
        switch coordinator.state {
        case .gameplay, .experiment: return true
        default: return false
        }
    }

    /// Internal builds list the boards on trial from Settings; release builds have no way in.
    private var experimentsAction: (() -> Void)? {
        #if DEBUG || MULTIVAN_INTERNAL
        coordinator.openExperiments
        #else
        nil
        #endif
    }

    @ViewBuilder
    private func experimentView(levelID: String) -> some View {
        let levels = (try? levelRepository.loadExperimentLevels()) ?? []
        if let index = levels.firstIndex(where: { $0.id == levelID }) {
            MultiVanExperimentPlayScreen(
                level: levels[index],
                settingsService: settingsService,
                onNext: index + 1 < levels.count ? { coordinator.startExperiment(levelID: levels[index + 1].id) } : nil,
                onBack: coordinator.openExperiments
            )
            .id(levelID)
        } else {
            unavailableLevelsView(message: "This experiment could not be loaded.")
        }
    }

    private var isStandardMenuHeaderScreenVisible: Bool {
        switch coordinator.state {
        case .mainMenu, .levelSelect, .shop, .profile, .settings:
            return true
        default:
            return false
        }
    }

    @ViewBuilder
    private func gameplayView(levelID: String) -> some View {
        if let levels = try? loadSortedLevels(),
           let level = levels.first(where: { $0.id == levelID }) {
            LevelPlayScreen(
                level: level,
                nextLevelID: nextLevelID(after: levelID),
                settingsService: settingsService,
                progressService: progressService,
                economyService: economyService,
                cosmetics: MultiVanCosmetics(profile: saveDataRepository.load()),
                onNextLevel: startGameplayIfUnlocked,
                onBackToLevels: coordinator.exitGameplayToLevels,
                onProfileChanged: handleProfileChanged
            )
            // A fresh identity per level gives each one a fresh engine.
            .id(levelID)
        } else {
            unavailableLevelsView(message: "This level could not be loaded.")
        }
    }

    @ViewBuilder
    private var levelSelectView: some View {
        switch levelSelectState {
        case let .loaded(levels):
            LevelSelectScreen(
                levels: levels,
                coinTotal: currentCoinTotal,
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

    private func loadSortedLevels() throws -> [MultiVanLevel] {
        try levelRepository.loadAllLevels()
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

private enum LevelSelectState {
    case loaded([MultiVanLevel])
    case empty
    case failed(String)
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
