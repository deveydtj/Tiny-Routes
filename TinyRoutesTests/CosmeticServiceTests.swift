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

    func testDefaultSaveDataResolvesDefaultGameplayLoadout() {
        let loadout = cosmeticService.gameplayLoadout()

        XCTAssertEqual(loadout.routeThemeID, "themeOceanDrive")
        XCTAssertEqual(loadout.deliveryDotID, "dotCourierBlue")
        XCTAssertEqual(loadout.trailID, "trailClean")
        XCTAssertEqual(loadout.confettiID, "confettiStars")
        XCTAssertEqual(loadout.destinationID, "destinationFlag")
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

    func testUnlockAndSelectChangesGameplayLoadoutRouteTheme() throws {
        let option = try paidOption(id: "themeForestPath")
        economyService.addCoins(500, reason: .debug)

        let result = cosmeticService.unlockAndSelectCosmetic(option)
        let loadout = cosmeticService.gameplayLoadout()

        XCTAssertEqual(result, .unlockedAndSelected)
        XCTAssertEqual(loadout.routeThemeID, "themeForestPath")
        XCTAssertEqual(loadout.routeTheme, option)
        XCTAssertEqual(economyService.coinTotal(), 0)
    }

    func testInvalidSelectedCosmeticIDFallsBackToDefaultGameplayLoadout() {
        repository.save(PlayerProfile(
            selectedCosmeticIDByCategoryID: [
                ShopCosmeticCategoryID.routeThemes: "missing-theme"
            ]
        ))

        let loadout = cosmeticService.gameplayLoadout()

        XCTAssertEqual(loadout.routeThemeID, "themeOceanDrive")
    }

    func testUnownedSelectedCosmeticIDFallsBackToDefaultGameplayLoadout() {
        repository.save(PlayerProfile(
            selectedCosmeticIDByCategoryID: [
                ShopCosmeticCategoryID.routeThemes: "themeForestPath"
            ]
        ))

        let loadout = cosmeticService.gameplayLoadout()

        XCTAssertEqual(loadout.routeThemeID, "themeOceanDrive")
    }

    func testUnlockAndAutoSelectSpendsCoinsAndSelectsPurchasedItem() throws {
        let option = try paidOption(id: "dotGolden")
        economyService.addCoins(450, reason: .debug)

        let result = cosmeticService.unlockAndSelectCosmetic(option)

        XCTAssertEqual(result, .unlockedAndSelected)
        XCTAssertTrue(cosmeticService.isOwned(cosmeticID: "dotGolden"))
        XCTAssertEqual(cosmeticService.selectedCosmeticID(forCategoryID: ShopCosmeticCategoryID.deliveryDots), "dotGolden")
        XCTAssertEqual(economyService.coinTotal(), 0)
    }

    func testUnlockAndAutoSelectWithInsufficientCoinsDoesNotUnlockOrSelect() throws {
        let option = try paidOption(id: "dotGolden")
        economyService.addCoins(100, reason: .debug)

        let result = cosmeticService.unlockAndSelectCosmetic(option)

        XCTAssertEqual(result, .insufficientCoins)
        XCTAssertFalse(cosmeticService.isOwned(cosmeticID: "dotGolden"))
        XCTAssertEqual(cosmeticService.selectedCosmeticID(forCategoryID: ShopCosmeticCategoryID.deliveryDots), "dotCourierBlue")
        XCTAssertEqual(economyService.coinTotal(), 100)
    }

    func testSelectingOwnedItemDoesNotSpendCoins() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "themeClassic"))
        economyService.addCoins(200, reason: .debug)

        let result = cosmeticService.unlockAndSelectCosmetic(option)

        XCTAssertEqual(result, .selected)
        XCTAssertEqual(cosmeticService.selectedCosmeticID(forCategoryID: ShopCosmeticCategoryID.routeThemes), "themeClassic")
        XCTAssertEqual(economyService.coinTotal(), 200)
    }

    func testTappingAlreadySelectedItemDoesNotMutateProfile() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "themeOceanDrive"))
        let profileBefore = repository.load()

        let result = cosmeticService.unlockAndSelectCosmetic(option)

        XCTAssertEqual(result, .alreadySelected)
        XCTAssertEqual(repository.load(), profileBefore)
    }

    private func paidOption(id: String) throws -> ShopCosmeticOption {
        try XCTUnwrap(catalogService.option(withID: id))
    }
}
