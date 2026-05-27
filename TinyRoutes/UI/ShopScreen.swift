import SwiftUI

struct ShopScreen: View {
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void
    let onProfileChanged: () -> Void

    private let catalogService: ShopCatalogService
    private let cosmeticService: CosmeticService
    private let economyService: EconomyService
    private let dailyBonusService: DailyBonusService

    @State private var selectedCategoryID = ShopCosmeticCategoryID.routeThemes
    @State private var activePlaceholder: ShopAlert?

    init(
        coinTotal: Int,
        onSettingsTapped: @escaping () -> Void,
        onAddCurrencyTapped: @escaping () -> Void,
        catalogService: ShopCatalogService = ShopCatalogService(),
        cosmeticService: CosmeticService? = nil,
        economyService: EconomyService? = nil,
        dailyBonusService: DailyBonusService? = nil,
        onProfileChanged: @escaping () -> Void = {}
    ) {
        self.coinTotal = coinTotal
        self.onSettingsTapped = onSettingsTapped
        self.onAddCurrencyTapped = onAddCurrencyTapped
        self.catalogService = catalogService
        let repository = SaveDataRepository()
        let resolvedEconomyService = economyService ?? EconomyService(repository: repository)
        self.economyService = resolvedEconomyService
        self.dailyBonusService = dailyBonusService ?? DailyBonusService(
            repository: repository,
            economyService: resolvedEconomyService
        )
        self.cosmeticService = cosmeticService ?? CosmeticService(
            repository: repository,
            economyService: resolvedEconomyService,
            catalogService: catalogService
        )
        self.onProfileChanged = onProfileChanged
    }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 16) {
                TRMenuTitleLogo(
                    pageTitle: "Shop",
                    subtitleOverride: "Customize your journey"
                )
                .padding(.top, 10)

                featuredSection

                customizeSection

                goodiesSection
                    .padding(.bottom, 18)
            }
            .frame(maxWidth: 760)
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 20)
            .padding(.top, 4)
            .padding(.bottom, 26)
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            TRShopPinnedBalanceBar(
                coinTotal: coinTotal,
                onSettingsTapped: onSettingsTapped,
                onAddCurrencyTapped: onAddCurrencyTapped
            )
        }
        .background {
            LinearGradient(
                colors: [
                    Color.white.opacity(0.24),
                    Color(red: 0.69, green: 0.89, blue: 0.80).opacity(0.12)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        }
        .alert(item: $activePlaceholder) { placeholder in
            Alert(
                title: Text(placeholder.title),
                message: Text(placeholder.message),
                dismissButton: .default(Text("OK"))
            )
        }
    }

    private var featuredSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            TRShopSectionHeader(title: "Featured")

            ViewThatFits(in: .horizontal) {
                HStack(spacing: 14) {
                    featuredCards
                }
                .frame(minWidth: 620)

                VStack(spacing: 14) {
                    featuredCards
                }
            }
        }
    }

    private var featuredCards: some View {
        ForEach(catalogService.featuredOffers) { offer in
            TRShopFeaturedCard(offer: offer) {
                onFeaturedOfferTapped(offer)
            }
        }
    }

    private var customizeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            TRShopSectionHeader(title: "Customize")

            TRShopCategoryPillBar(
                categories: catalogService.categories,
                selectedCategoryID: selectedCategoryID,
                onCategorySelected: { selectedCategoryID = $0 }
            )

            if let selectedOption = selectedOptionForPreview {
                ViewThatFits(in: .horizontal) {
                    HStack(alignment: .top, spacing: 14) {
                        TRShopRouteThemePreviewCard(selectedOption: selectedOption)
                            .frame(width: 286)

                        TRShopCosmeticGrid(
                            options: selectedCategoryOptions,
                            onOptionTapped: onCosmeticOptionTapped
                        )
                        .frame(maxWidth: .infinity)
                    }
                    .frame(minWidth: 620)

                    VStack(spacing: 14) {
                        TRShopRouteThemePreviewCard(selectedOption: selectedOption)

                        TRShopCosmeticGrid(
                            options: selectedCategoryOptions,
                            onOptionTapped: onCosmeticOptionTapped
                        )
                    }
                }
            }
        }
    }

    private var goodiesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            TRShopSectionHeader(title: "More Goodies")

            TRShopGoodiesStrip(
                actions: catalogService.goodieActions,
                onActionTapped: onGoodieTapped
            )
        }
    }

    private var selectedCategoryOptions: [ShopCosmeticOption] {
        cosmeticService.options(forCategoryID: selectedCategoryID)
    }

    private var selectedOptionForPreview: ShopCosmeticOption? {
        selectedCategoryOptions.first { $0.isSelected }
            ?? selectedCategoryOptions.first
            ?? cosmeticService.options(forCategoryID: ShopCosmeticCategoryID.routeThemes).first { $0.isSelected }
    }

    private func onFeaturedOfferTapped(_ offer: ShopFeaturedOffer) {
        // Entitlement flags should change only after real StoreKit purchase or restore succeeds.
        activePlaceholder = .featuredOffer(offer)
    }

    private func onCosmeticOptionTapped(_ option: ShopCosmeticOption) {
        switch cosmeticService.unlockAndSelectCosmetic(option) {
        case .unlockedAndSelected:
            onProfileChanged()
            activePlaceholder = .unlockedAndSelected(option)
        case .selected:
            onProfileChanged()
            activePlaceholder = .selectedCosmetic(option)
        case .alreadySelected:
            activePlaceholder = .alreadySelected(option)
        case .insufficientCoins:
            activePlaceholder = .insufficientCoins(option)
        case .notFound:
            activePlaceholder = .notFound(option)
        }
    }

    private func onGoodieTapped(_ action: ShopGoodieAction) {
        if action.id == "dailyBonus" {
            switch dailyBonusService.claimDailyBonus() {
            case let .claimed(amount, _):
                onProfileChanged()
                activePlaceholder = .dailyBonusClaimed(amount: amount)
            case .alreadyClaimed:
                activePlaceholder = .dailyBonusAlreadyClaimed
            }
        } else {
            activePlaceholder = .goodie(action)
        }
    }
}

private enum ShopAlert: Identifiable {
    case featuredOffer(ShopFeaturedOffer)
    case unlockedAndSelected(ShopCosmeticOption)
    case selectedCosmetic(ShopCosmeticOption)
    case insufficientCoins(ShopCosmeticOption)
    case alreadyOwned(ShopCosmeticOption)
    case alreadySelected(ShopCosmeticOption)
    case notOwned(ShopCosmeticOption)
    case notFound(ShopCosmeticOption)
    case dailyBonusClaimed(amount: Int)
    case dailyBonusAlreadyClaimed
    case goodie(ShopGoodieAction)

    var id: String {
        "\(title)-\(message)"
    }

    var title: String {
        switch self {
        case let .featuredOffer(offer):
            return offer.title
        case let .unlockedAndSelected(option):
            return option.title
        case let .selectedCosmetic(option):
            return option.title
        case let .insufficientCoins(option):
            return option.title
        case let .alreadyOwned(option):
            return option.title
        case let .alreadySelected(option):
            return option.title
        case let .notOwned(option):
            return option.title
        case let .notFound(option):
            return option.title
        case .dailyBonusClaimed:
            return "Daily Bonus"
        case .dailyBonusAlreadyClaimed:
            return "Daily Bonus"
        case let .goodie(action):
            return action.title
        }
    }

    var message: String {
        switch self {
        case .featuredOffer:
            return "Purchases coming soon."
        case .unlockedAndSelected:
            return "Unlocked and equipped."
        case .selectedCosmetic:
            return "Now equipped."
        case .insufficientCoins:
            return "Not enough coins to unlock this cosmetic."
        case .alreadyOwned:
            return "This cosmetic is already owned."
        case .alreadySelected:
            return "Already equipped."
        case .notOwned:
            return "Unlock this cosmetic before selecting it."
        case .notFound:
            return "This cosmetic is no longer available."
        case let .dailyBonusClaimed(amount):
            return "\(amount) coins added."
        case .dailyBonusAlreadyClaimed:
            return "Daily bonus already claimed today."
        case let .goodie(action):
            switch action.id {
            case "coins":
                return "Coin packs coming soon."
            case "gems":
                return "Gems coming soon."
            case "dailyDeals":
                return "Daily deals coming soon."
            default:
                return "This shop action is coming soon."
            }
        }
    }
}

#Preview("Shop Screen") {
    ZStack {
        SpriteImage(name: "background")
            .scaledToFill()
            .ignoresSafeArea()

        ShopScreen(
            coinTotal: 1_250,
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )
    }
}
