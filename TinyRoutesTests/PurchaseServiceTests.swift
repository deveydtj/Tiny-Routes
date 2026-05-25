import XCTest
@testable import TinyRoutes

final class PurchaseServiceTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!
    private var repository: SaveDataRepository!
    private var service: PurchaseService!

    override func setUp() {
        super.setUp()
        suiteName = "PurchaseServiceTests.\(name)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        repository = SaveDataRepository(userDefaults: defaults)
        service = PurchaseService(repository: repository)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        service = nil
        repository = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testRemoveAdsEntitlementCanBeSetThroughService() {
        let result = service.fulfillRemoveAds()

        XCTAssertEqual(result, .removeAdsFulfilled)
        XCTAssertTrue(repository.load().isRemoveAdsPurchased)
    }

    func testRemoveAdsFulfillmentIsIdempotent() {
        XCTAssertEqual(service.fulfillRemoveAds(), .removeAdsFulfilled)
        XCTAssertEqual(service.fulfillRemoveAds(), .alreadyFulfilled)
    }

    func testStarterPackAddsCoinsAndUnlocksExpectedCosmetics() {
        let result = service.fulfillStarterPack()
        let profile = repository.load()

        XCTAssertEqual(
            result,
            .starterPackFulfilled(
                coinsAdded: PurchaseService.starterPackCoinAmount,
                unlockedCosmeticIDs: PurchaseService.starterPackCosmeticIDs
            )
        )
        XCTAssertEqual(profile.coinTotal, PurchaseService.starterPackCoinAmount)
        XCTAssertTrue(PurchaseService.starterPackCosmeticIDs.isSubset(of: profile.ownedCosmeticIDs))
    }

    func testStarterPackFulfillmentIsIdempotent() {
        XCTAssertEqual(service.fulfillStarterPack(), .starterPackFulfilled(
            coinsAdded: PurchaseService.starterPackCoinAmount,
            unlockedCosmeticIDs: PurchaseService.starterPackCosmeticIDs
        ))
        XCTAssertEqual(service.fulfillStarterPack(), .alreadyFulfilled)
        XCTAssertEqual(repository.load().coinTotal, PurchaseService.starterPackCoinAmount)
    }

    func testUnsupportedProductIsIgnored() {
        XCTAssertEqual(service.fulfillPurchase(productID: "unknown"), .unsupportedProduct)
    }
}
