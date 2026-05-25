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
}
