import Foundation

/// Wraps StoreKit so IAP logic stays decoupled from the rest of the app.
/// Placeholder — implemented in monetization stories.
final class PurchaseAdapter {
    enum ProductID {
        static let starterPack = "com.tinyroutes.starterpack"
        static let removeAds = "com.tinyroutes.removeads"
        static let smallCoinPack = "com.tinyroutes.coins.small"
        static let largeCoinPack = "com.tinyroutes.coins.large"
    }

    struct Product: Equatable {
        let id: String
        let displayName: String
        let displayPrice: String
    }

    enum PurchaseResult: Equatable {
        case purchased(productID: String)
        case cancelled
        case pending
        case failed(message: String)
    }

    func loadProducts() async throws -> [Product] {
        []
    }

    func purchase(productID: String) async -> PurchaseResult {
        .failed(message: "Purchases coming soon.")
    }

    func restorePurchases() async throws -> [String] {
        []
    }
}
