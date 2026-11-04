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
            if !isGameplayVisible {
                SpriteImage(name: "background")
                    .scaledToFill()
                    .ignoresSafeArea()
            }

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
                        settingsService: settingsService
                    )

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
        case .levelSelect, .gameplay, .shop, .profile, .settings:
            return true
        default:
            return false
        }
    }

    private var isGameplayVisible: Bool {
        if case .gameplay = coordinator.state { return true }
        return false
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
    private func gameplayView(levelID: String) -> some View {
        if let levels = try? loadSortedLevels(),
           let level = levels.first(where: { $0.id == levelID }) {
            LevelPlayScreen(
                level: level,
                nextLevelID: nextLevelID(after: levelID),
                settingsService: settingsService,
                progressService: progressService,
                economyService: economyService,
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
