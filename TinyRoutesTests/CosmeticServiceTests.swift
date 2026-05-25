import XCTest
@testable import TinyRoutes

final class CosmeticServiceTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!
    private var repository: SaveDataRepository!
    private var economyService: EconomyService!
    private var cosmeticService: CosmeticService!
    private let catalogService = ShopCatalogService()

    override func setUp() {
        super.setUp()
        suiteName = "CosmeticServiceTests.\(name)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        repository = SaveDataRepository(userDefaults: defaults)
        economyService = EconomyService(repository: repository)
        cosmeticService = CosmeticService(
            repository: repository,
            economyService: economyService,
            catalogService: catalogService
        )
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        cosmeticService = nil
        economyService = nil
        repository = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testDefaultCosmeticsAreOwnedAndSelected() {
        XCTAssertTrue(cosmeticService.isOwned(cosmeticID: "themeOceanDrive"))
        XCTAssertTrue(cosmeticService.isOwned(cosmeticID: "dotCourierBlue"))
        XCTAssertEqual(
            cosmeticService.selectedCosmeticID(forCategoryID: ShopCosmeticCategoryID.routeThemes),
            "themeOceanDrive"
        )
        XCTAssertEqual(
            cosmeticService.selectedCosmeticID(forCategoryID: ShopCosmeticCategoryID.trails),
            "trailClean"
        )
    }

    func testUnlockCosmeticSpendsCoinsAndAddsOwnership() throws {
        let option = try paidOption(id: "themeForestPath")
        economyService.addCoins(500, reason: .debug)

        let result = cosmeticService.unlockCosmetic(option)

        XCTAssertEqual(result, .unlocked)
        XCTAssertTrue(cosmeticService.isOwned(cosmeticID: option.id))
        XCTAssertEqual(economyService.coinTotal(), 0)
    }

    func testUnlockCosmeticFailsWhenCoinsAreInsufficient() throws {
        let option = try paidOption(id: "themeForestPath")

        let result = cosmeticService.unlockCosmetic(option)

        XCTAssertEqual(result, .insufficientCoins)
        XCTAssertFalse(cosmeticService.isOwned(cosmeticID: option.id))
    }

    func testUnlockAlreadyOwnedCosmeticDoesNotDoubleSpend() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "themeOceanDrive"))
        economyService.addCoins(500, reason: .debug)

        let result = cosmeticService.unlockCosmetic(option)

        XCTAssertEqual(result, .alreadyOwned)
        XCTAssertEqual(economyService.coinTotal(), 500)
    }

    func testSelectOwnedCosmeticUpdatesSelectedCategory() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "themeClassic"))

        let result = cosmeticService.selectCosmetic(option)

        XCTAssertEqual(result, .selected)
        XCTAssertEqual(
            cosmeticService.selectedCosmeticID(forCategoryID: ShopCosmeticCategoryID.routeThemes),
            "themeClassic"
        )
    }

    func testSelectUnownedCosmeticFails() throws {
        let option = try paidOption(id: "themeForestPath")

        let result = cosmeticService.selectCosmetic(option)

        XCTAssertEqual(result, .notOwned)
        XCTAssertNotEqual(
            cosmeticService.selectedCosmeticID(forCategoryID: ShopCosmeticCategoryID.routeThemes),
            "themeForestPath"
        )
    }

    func testProfileAwareOptionsReflectSavedOwnershipAndSelection() throws {
        let option = try paidOption(id: "themeForestPath")
        economyService.addCoins(500, reason: .debug)
        cosmeticService.unlockCosmetic(option)
        cosmeticService.selectCosmetic(option)

        let options = cosmeticService.options(forCategoryID: ShopCosmeticCategoryID.routeThemes)
        let unlockedOption = try XCTUnwrap(options.first { $0.id == "themeForestPath" })
        let selectedOptions = options.filter(\.isSelected)

        XCTAssertTrue(unlockedOption.isUnlocked)
        XCTAssertTrue(unlockedOption.isSelected)
        XCTAssertEqual(selectedOptions.map(\.id), ["themeForestPath"])
    }

    private func paidOption(id: String) throws -> ShopCosmeticOption {
        try XCTUnwrap(catalogService.option(withID: id))
    }
}
