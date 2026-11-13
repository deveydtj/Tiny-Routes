import SceneKit
import XCTest
@testable import TinyRoutes

/// The shop's cosmetics on the Multi-Van boards: what carries over, what is
/// refunded, and that nothing a player plans with changes.
@MainActor
final class MultiVanCosmeticsTests: XCTestCase {
    private let catalog = ShopCatalogService()

    // MARK: - Catalog

    func testEveryCosmeticOnSaleShowsOnTheBoards() {
        XCTAssertEqual(catalog.categories.map(\.title), ["Table Themes", "Confetti"])
        for option in catalog.cosmeticOptions {
            let shows = MultiVanTableTheme(rawValue: option.id) != nil || MultiVanConfettiStyle(rawValue: option.id) != nil
            XCTAssertTrue(shows, "\(option.id) is sold but no board draws it")
            XCTAssertFalse(ShopCatalogService.isRetired(option), option.id)
        }
        // And every look the boards know is in the shop.
        let onSale = Set(catalog.cosmeticOptions.map(\.id))
        XCTAssertEqual(Set(MultiVanTableTheme.allCases.map(\.rawValue) + MultiVanConfettiStyle.allCases.map(\.rawValue)), onSale)
        // A player who finishes the campaign at three stars can afford a set, not everything.
        let total = catalog.cosmeticOptions.compactMap(\.price).reduce(0, +)
        XCTAssertEqual(total, 3_600)
        XCTAssertGreaterThan(total, 19 * 3 * EconomyService.coinsPerStar)
    }

    func testRetiredCosmeticsResolveButCannotBeBought() throws {
        let suite = "MultiVanCosmeticsTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let repository = SaveDataRepository(userDefaults: defaults)
        let service = CosmeticService(repository: repository, catalogService: catalog)
        repository.update { $0.coinTotal = 5_000 }

        let retired = try XCTUnwrap(catalog.option(withID: "dotGolden"))
        XCTAssertTrue(ShopCatalogService.isRetired(retired))
        XCTAssertFalse(catalog.cosmeticOptions.contains(retired))
        XCTAssertEqual(service.unlockAndSelectCosmetic(retired), .notFound)
        XCTAssertEqual(repository.load().coinTotal, 5_000)
        XCTAssertFalse(service.isOwned(cosmeticID: "dotGolden"))
        XCTAssertEqual(ShopCatalogService.retiredCosmeticPrices.count, 9)
        XCTAssertEqual(ShopCatalogService.retiredCosmeticPrices.values.reduce(0, +), 4_200)
    }

    // MARK: - Owned items

    func testOlderSaveKeepsThemesAndConfettiAndIsRefundedForTheRest() throws {
        var saved = PlayerProfile(
            coinTotal: 120,
            lifetimeCoinsSpent: 2_000,
            ownedCosmeticIDs: PlayerProfile.defaultOwnedCosmeticIDs.union([
                "themeForestPath", "confettiGarden", "dotGolden", "trailNeon", "destinationCabin",
            ]),
            selectedCosmeticIDByCategoryID: [
                ShopCosmeticCategoryID.routeThemes: "themeForestPath",
                ShopCosmeticCategoryID.confetti: "confettiGarden",
                ShopCosmeticCategoryID.deliveryDots: "dotGolden",
                ShopCosmeticCategoryID.trails: "trailNeon",
                ShopCosmeticCategoryID.destinations: "destinationCabin",
            ]
        )
        saved.schemaVersion = 4
        let profile = saved.normalized()

        XCTAssertEqual(profile.schemaVersion, 5)
        // Golden 450 + Neon Glow 650 + Cabin 500 come back.
        XCTAssertEqual(profile.coinTotal, 120 + 1_600)
        XCTAssertEqual(profile.lifetimeCoinsSpent, 400)
        XCTAssertTrue(profile.ownedCosmeticIDs.isSuperset(of: ["themeForestPath", "confettiGarden"]))
        XCTAssertTrue(profile.ownedCosmeticIDs.isDisjoint(with: ["dotGolden", "trailNeon", "destinationCabin"]))
        XCTAssertEqual(profile.selectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.routeThemes], "themeForestPath")
        XCTAssertEqual(profile.selectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.confetti], "confettiGarden")
        XCTAssertEqual(profile.selectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.deliveryDots], "dotCourierBlue")
        XCTAssertEqual(MultiVanCosmetics(profile: profile), MultiVanCosmetics(table: .forestPath, confetti: .leaves))
        // Refunded once: loading again pays nothing more.
        XCTAssertEqual(profile.normalized(), profile)
    }

    func testOnlyOwnedSelectionsAreDrawn() {
        var profile = PlayerProfile()
        XCTAssertEqual(MultiVanCosmetics(profile: profile), .standard)
        profile.selectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.routeThemes] = "themeNeonNights"
        XCTAssertEqual(MultiVanCosmetics(profile: profile).table, .standard, "selected but not owned")
        profile.ownedCosmeticIDs.insert("themeNeonNights")
        XCTAssertEqual(MultiVanCosmetics(profile: profile).table, .neonNights)
        // The shop tries one item on over what the player wears.
        let sugar = catalog.option(withID: "confettiCandy")!
        XCTAssertEqual(MultiVanCosmetics(profile: profile).trying(sugar), MultiVanCosmetics(table: .neonNights, confetti: .sugarBurst))
    }

    // MARK: - On the boards

    func testStandardLookIsTheBoardAsItWasAndThemesAreDistinct() {
        XCTAssertEqual(MultiVanTableTheme.standard.soilHex, 0xA26E48)
        XCTAssertEqual(MultiVanTableTheme.standard.deepSoilHex, 0x7B5339)
        XCTAssertEqual(MultiVanTableTheme.standard.skyHexes, [0xBFE1F2, 0xE4F3F6, 0xFBF1E3])
        XCTAssertNil(MultiVanConfettiStyle.standard.winColors)
        XCTAssertEqual(Set(MultiVanTableTheme.allCases.map(\.soilHex)).count, MultiVanTableTheme.allCases.count)
        for style in MultiVanConfettiStyle.allCases where style != .standard {
            XCTAssertEqual(style.winColors?.count, 6, style.rawValue)
        }
    }

    func testThemeRepaintsOnlyTheTablesBaseAndSky() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository(bundle: MultiVanTestBoards.appBundle).loadAllLevels().first)
        let engine = try MultiVanEngine(level: level)
        let scene = MultiVanDioramaScene()
        scene.load(level, graph: engine.runtimeGraph)
        func diffuse(_ name: String) -> AnyObject? {
            scene.scene.rootNode.childNode(withName: name, recursively: true)?.geometry?.firstMaterial?.diffuse.contents as AnyObject?
        }
        let before = (
            soil: try XCTUnwrap(diffuse(MultiVanDioramaScene.soilNodeName)),
            deep: try XCTUnwrap(diffuse(MultiVanDioramaScene.deepSoilNodeName)),
            lawn: try XCTUnwrap(diffuse(MultiVanDioramaScene.lawnNodeName)),
            sky: try XCTUnwrap(scene.scene.background.contents as AnyObject?)
        )
        let pieces = scene.vans.count + scene.houses.count + scene.dials.count

        // The standard look repaints nothing.
        scene.apply(.standard)
        XCTAssertTrue(diffuse(MultiVanDioramaScene.soilNodeName) === before.soil)

        scene.apply(MultiVanCosmetics(table: .sunsetBlvd, confetti: .leaves))
        XCTAssertEqual(scene.cosmetics.table, .sunsetBlvd)
        XCTAssertFalse(diffuse(MultiVanDioramaScene.soilNodeName) === before.soil)
        XCTAssertFalse(diffuse(MultiVanDioramaScene.deepSoilNodeName) === before.deep)
        XCTAssertFalse((scene.scene.background.contents as AnyObject?) === before.sky)
        // The lawn, with its roads, and every piece are exactly as they were.
        XCTAssertTrue(diffuse(MultiVanDioramaScene.lawnNodeName) === before.lawn)
        XCTAssertEqual(scene.vans.count + scene.houses.count + scene.dials.count, pieces)

        // Confetti alone leaves the table as it is.
        let sunsetSoil = diffuse(MultiVanDioramaScene.soilNodeName)
        scene.apply(MultiVanCosmetics(table: .sunsetBlvd, confetti: .sugarBurst))
        XCTAssertTrue(diffuse(MultiVanDioramaScene.soilNodeName) === sunsetSoil)
        XCTAssertEqual(scene.cosmetics.confetti, .sugarBurst)
    }
}
