import Foundation

enum PurchaseFulfillmentResult: Equatable {
    case starterPackFulfilled(coinsAdded: Int, unlockedCosmeticIDs: Set<String>)
    case removeAdsFulfilled
    case alreadyFulfilled
    case unsupportedProduct
}

final class PurchaseService {
    static let starterPackCoinAmount = 1_000
    static let starterPackCosmeticIDs: Set<String> = [
        "themeForestPath",
        "dotGarden",
        "trailBubbles",
        "confettiSpark",
        "destinationBeach"
    ]

    private let repository: SaveDataRepository
    private let catalogService: ShopCatalogService

    init(
        repository: SaveDataRepository = SaveDataRepository(),
        catalogService: ShopCatalogService = ShopCatalogService()
    ) {
        self.repository = repository
        self.catalogService = catalogService
    }

    @discardableResult
    func fulfillPurchase(productID: String) -> PurchaseFulfillmentResult {
        switch productID {
        case PurchaseAdapter.ProductID.starterPack:
            return fulfillStarterPack()
        case PurchaseAdapter.ProductID.removeAds:
            return fulfillRemoveAds()
        default:
            return .unsupportedProduct
        }
    }

    @discardableResult
    func fulfillRemoveAds() -> PurchaseFulfillmentResult {
        let profile = repository.load()
        guard !profile.isRemoveAdsPurchased else {
            return .alreadyFulfilled
        }

        repository.update { profile in
            profile.isRemoveAdsPurchased = true
        }
        return .removeAdsFulfilled
    }

    @discardableResult
    func fulfillStarterPack() -> PurchaseFulfillmentResult {
        let fulfillmentKey = "purchase:\(PurchaseAdapter.ProductID.starterPack)"
        let profile = repository.load()
        guard !profile.claimedLevelRewardKeys.contains(fulfillmentKey) else {
            return .alreadyFulfilled
        }

        let validCosmeticIDs = Self.starterPackCosmeticIDs.filter { catalogService.option(withID: $0) != nil }
        repository.update { profile in
            profile.claimedLevelRewardKeys.insert(fulfillmentKey)
            profile.coinTotal += Self.starterPackCoinAmount
            profile.lifetimeCoinsEarned += Self.starterPackCoinAmount
            profile.ownedCosmeticIDs.formUnion(validCosmeticIDs)
        }

        return .starterPackFulfilled(
            coinsAdded: Self.starterPackCoinAmount,
            unlockedCosmeticIDs: validCosmeticIDs
        )
    }
}
