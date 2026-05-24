import SwiftUI

struct ShopScreen: View {
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    private let catalogService: ShopCatalogService

    @State private var selectedCategoryID = ShopCosmeticCategoryID.routeThemes
    @State private var activePlaceholder: ShopPlaceholderAlert?

    init(
        coinTotal: Int,
        onSettingsTapped: @escaping () -> Void,
        onAddCurrencyTapped: @escaping () -> Void,
        catalogService: ShopCatalogService = ShopCatalogService()
    ) {
        self.coinTotal = coinTotal
        self.onSettingsTapped = onSettingsTapped
        self.onAddCurrencyTapped = onAddCurrencyTapped
        self.catalogService = catalogService
    }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 16) {
                TRMenuHeader(
                    pageTitle: "Shop",
                    subtitleOverride: "Customize your journey",
                    coinTotal: coinTotal,
                    onSettingsTapped: onSettingsTapped,
                    onAddCurrencyTapped: onAddCurrencyTapped
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
        catalogService.options(forCategoryID: selectedCategoryID)
    }

    private var selectedOptionForPreview: ShopCosmeticOption? {
        selectedCategoryOptions.first { $0.isSelected }
            ?? selectedCategoryOptions.first
            ?? catalogService.options(forCategoryID: ShopCosmeticCategoryID.routeThemes).first { $0.isSelected }
    }

    private func onFeaturedOfferTapped(_ offer: ShopFeaturedOffer) {
        // TODO: route Starter Pack and Remove Ads purchases through PurchaseAdapter.
        // TODO: route Remove Ads entitlement through AdsAdapter once monetization is active.
        activePlaceholder = .featuredOffer(offer)
    }

    private func onCosmeticOptionTapped(_ option: ShopCosmeticOption) {
        if option.isSelected {
            activePlaceholder = .alreadySelected(option)
        } else if option.isUnlocked {
            // TODO: connect cosmetic selection to CosmeticService.
            activePlaceholder = .selectCosmetic(option)
        } else {
            // TODO: spend coins through EconomyService and persist ownership with SaveDataRepository.
            activePlaceholder = .unlockCosmetic(option)
        }
    }

    private func onGoodieTapped(_ action: ShopGoodieAction) {
        activePlaceholder = .goodie(action)
    }
}

private enum ShopPlaceholderAlert: Identifiable {
    case featuredOffer(ShopFeaturedOffer)
    case unlockCosmetic(ShopCosmeticOption)
    case selectCosmetic(ShopCosmeticOption)
    case alreadySelected(ShopCosmeticOption)
    case goodie(ShopGoodieAction)

    var id: String {
        "\(title)-\(message)"
    }

    var title: String {
        switch self {
        case let .featuredOffer(offer):
            return offer.title
        case let .unlockCosmetic(option):
            return option.title
        case let .selectCosmetic(option):
            return option.title
        case let .alreadySelected(option):
            return option.title
        case let .goodie(action):
            return action.title
        }
    }

    var message: String {
        switch self {
        case .featuredOffer:
            return "Purchases coming soon."
        case .unlockCosmetic:
            return "Unlock coming soon."
        case .selectCosmetic:
            return "Cosmetic selection coming soon."
        case .alreadySelected:
            return "This cosmetic is already selected."
        case let .goodie(action):
            if action.id == "dailyBonus" {
                return "Daily bonus coming soon."
            }
            return "This shop action is coming soon."
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
