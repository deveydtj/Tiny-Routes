import Foundation

enum CosmeticUnlockResult: Equatable {
    case unlocked
    case alreadyOwned
    case insufficientCoins
}

enum CosmeticSelectionResult: Equatable {
    case selected
    case alreadySelected
    case notOwned
}

enum CosmeticUnlockAndSelectResult: Equatable {
    case unlockedAndSelected
    case selected
    case alreadySelected
    case insufficientCoins
    case notFound
}

/// Manages cosmetic item ownership and selection.
final class CosmeticService {
    private let repository: SaveDataRepository
    private let economyService: EconomyService
    private let catalogService: ShopCatalogService

    init(
        repository: SaveDataRepository = SaveDataRepository(),
        economyService: EconomyService? = nil,
        catalogService: ShopCatalogService = ShopCatalogService()
    ) {
        self.repository = repository
        self.economyService = economyService ?? EconomyService(repository: repository)
        self.catalogService = catalogService
    }

    func isOwned(cosmeticID: String) -> Bool {
        repository.load().ownedCosmeticIDs.contains(cosmeticID)
    }

    func selectedCosmeticID(forCategoryID categoryID: String) -> String? {
        repository.load().selectedCosmeticIDByCategoryID[categoryID]
    }

    func ownedCosmeticIDs() -> Set<String> {
        repository.load().ownedCosmeticIDs
    }

    func selectedCosmeticIDByCategoryID() -> [String: String] {
        repository.load().selectedCosmeticIDByCategoryID
    }

    func options(forCategoryID categoryID: String) -> [ShopCosmeticOption] {
        let profile = repository.load()
        return catalogService.options(
            forCategoryID: categoryID,
            ownedCosmeticIDs: profile.ownedCosmeticIDs,
            selectedCosmeticIDByCategoryID: profile.selectedCosmeticIDByCategoryID
        )
    }

    func gameplayLoadout() -> GameplayCosmeticLoadout {
        let profile = repository.load()
        let routeTheme = resolvedSelectedOption(
            categoryID: ShopCosmeticCategoryID.routeThemes,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.routeThemes] ?? "themeOceanDrive",
            profile: profile
        )
        let deliveryDot = resolvedSelectedOption(
            categoryID: ShopCosmeticCategoryID.deliveryDots,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.deliveryDots] ?? "dotCourierBlue",
            profile: profile
        )
        let trail = resolvedSelectedOption(
            categoryID: ShopCosmeticCategoryID.trails,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.trails] ?? "trailClean",
            profile: profile
        )
        let confetti = resolvedSelectedOption(
            categoryID: ShopCosmeticCategoryID.confetti,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.confetti] ?? "confettiStars",
            profile: profile
        )
        let destination = resolvedSelectedOption(
            categoryID: ShopCosmeticCategoryID.destinations,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.destinations] ?? "destinationFlag",
            profile: profile
        )

        return GameplayCosmeticLoadout(
            routeTheme: routeTheme,
            deliveryDot: deliveryDot,
            trail: trail,
            confetti: confetti,
            destination: destination
        )
    }

    @discardableResult
    func unlockCosmetic(_ option: ShopCosmeticOption) -> CosmeticUnlockResult {
        if isOwned(cosmeticID: option.id) {
            return .alreadyOwned
        }

        if let price = option.price, price > 0 {
            guard economyService.spendCoins(price, reason: .cosmeticUnlock(cosmeticID: option.id)) else {
                return .insufficientCoins
            }
        }

        repository.update { profile in
            profile.ownedCosmeticIDs.insert(option.id)
        }
        return .unlocked
    }

    @discardableResult
    func selectCosmetic(_ option: ShopCosmeticOption) -> CosmeticSelectionResult {
        guard isOwned(cosmeticID: option.id) else {
            return .notOwned
        }

        if selectedCosmeticID(forCategoryID: option.categoryID) == option.id {
            return .alreadySelected
        }

        repository.update { profile in
            profile.selectedCosmeticIDByCategoryID[option.categoryID] = option.id
        }
        return .selected
    }

    @discardableResult
    func unlockAndSelectCosmetic(_ option: ShopCosmeticOption) -> CosmeticUnlockAndSelectResult {
        guard let catalogOption = catalogService.option(withID: option.id),
              catalogOption.categoryID == option.categoryID else {
            return .notFound
        }

        let profile = repository.load()
        let isOwned = profile.ownedCosmeticIDs.contains(catalogOption.id)
        let isSelected = profile.selectedCosmeticIDByCategoryID[catalogOption.categoryID] == catalogOption.id

        if isOwned, isSelected {
            return .alreadySelected
        }

        if isOwned {
            repository.update { profile in
                profile.selectedCosmeticIDByCategoryID[catalogOption.categoryID] = catalogOption.id
            }
            return .selected
        }

        let price = catalogOption.price ?? 0
        guard price <= 0 || profile.coinTotal >= price else {
            return .insufficientCoins
        }

        repository.update { profile in
            if price > 0 {
                profile.coinTotal -= price
                profile.lifetimeCoinsSpent += price
            }
            profile.ownedCosmeticIDs.insert(catalogOption.id)
            profile.selectedCosmeticIDByCategoryID[catalogOption.categoryID] = catalogOption.id
        }

        return .unlockedAndSelected
    }

    func selectedCollectionSelections() -> [ProfileCollectionSelection] {
        let profile = repository.load()

        return [
            collectionSelection(
                id: "favorite-theme",
                label: "Favorite Theme",
                categoryID: ShopCosmeticCategoryID.routeThemes,
                fallbackValue: "Ocean Drive",
                systemImage: "water.waves",
                accent: .theme,
                profile: profile
            ),
            collectionSelection(
                id: "trail",
                label: "Trail",
                categoryID: ShopCosmeticCategoryID.trails,
                fallbackValue: "Classic",
                systemImage: "point.topleft.down.curvedto.point.bottomright.up",
                accent: .trail,
                profile: profile
            ),
            collectionSelection(
                id: "destination",
                label: "Destination",
                categoryID: ShopCosmeticCategoryID.destinations,
                fallbackValue: "Finish Flag",
                systemImage: "house.fill",
                accent: .destination,
                profile: profile
            )
        ]
    }

    private func collectionSelection(
        id: String,
        label: String,
        categoryID: String,
        fallbackValue: String,
        systemImage: String,
        accent: ProfileCollectionAccent,
        profile: PlayerProfile
    ) -> ProfileCollectionSelection {
        let selectedID = profile.selectedCosmeticIDByCategoryID[categoryID]
        let optionTitle = selectedID.flatMap { catalogService.option(withID: $0)?.title } ?? fallbackValue

        return ProfileCollectionSelection(
            id: id,
            label: label,
            value: optionTitle,
            systemImage: systemImage,
            accent: accent,
            isSelected: selectedID != nil
        )
    }

    private func resolvedSelectedOption(
        categoryID: String,
        defaultID: String,
        profile: PlayerProfile
    ) -> ShopCosmeticOption {
        if let selectedID = profile.selectedCosmeticIDByCategoryID[categoryID],
           profile.ownedCosmeticIDs.contains(selectedID),
           let selectedOption = catalogService.option(withID: selectedID),
           selectedOption.categoryID == categoryID {
            return selectedOption
        }

        if profile.ownedCosmeticIDs.contains(defaultID),
           let defaultOption = catalogService.option(withID: defaultID),
           defaultOption.categoryID == categoryID {
            return defaultOption
        }

        if let ownedOption = catalogService.options(forCategoryID: categoryID).first(where: { profile.ownedCosmeticIDs.contains($0.id) }) {
            return ownedOption
        }

        if let categoryOption = catalogService.options(forCategoryID: categoryID).first {
            return categoryOption
        }

        return ShopCosmeticOption(
            id: defaultID,
            categoryID: categoryID,
            title: "Default",
            price: nil,
            isUnlocked: true,
            isSelected: true,
            accent: .classic
        )
    }
}
