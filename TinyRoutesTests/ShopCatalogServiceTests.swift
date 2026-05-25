import XCTest
@testable import TinyRoutes

final class ShopCatalogServiceTests: XCTestCase {
    private let service = ShopCatalogService()

    func testFeaturedOffersReturnInExpectedOrder() {
        XCTAssertEqual(service.featuredOffers.map(\.title), ["Starter Pack", "Remove Ads"])
    }

    func testCategoriesReturnInExpectedOrder() {
        XCTAssertEqual(
            service.categories.map(\.title),
            ["Route Themes", "Delivery Dots", "Trails", "Confetti", "Destinations"]
        )
    }

    func testEveryCosmeticOptionReferencesKnownCategoryID() {
        let categoryIDs = Set(service.categories.map(\.id))

        for option in service.cosmeticOptions {
            XCTAssertTrue(categoryIDs.contains(option.categoryID), "\(option.title) references an unknown category")
        }
    }

    func testRouteThemeCatalogHasExactlyOneSelectedOption() {
        let selectedRouteThemes = service
            .options(forCategoryID: ShopCosmeticCategoryID.routeThemes)
            .filter(\.isSelected)

        XCTAssertEqual(selectedRouteThemes.map(\.title), ["Ocean Drive"])
    }

    func testLockedCoinPricedCosmeticsHavePositivePrices() {
        for option in service.cosmeticOptions where !option.isUnlocked {
            guard let price = option.price else {
                XCTFail("\(option.title) is locked but has no coin price")
                continue
            }

            XCTAssertGreaterThan(price, 0, "\(option.title) should have a positive coin price")
        }
    }

    func testEveryCategoryHasPlaceholderOptions() {
        for category in service.categories {
            XCTAssertGreaterThanOrEqual(
                service.options(forCategoryID: category.id).count,
                4,
                "\(category.title) should not render as an empty shop category"
            )
        }
    }

    func testProfileAwareOptionsReflectOwnership() throws {
        let options = service.options(
            forCategoryID: ShopCosmeticCategoryID.routeThemes,
            ownedCosmeticIDs: ["themeOceanDrive", "themeForestPath"],
            selectedCosmeticIDByCategoryID: [
                ShopCosmeticCategoryID.routeThemes: "themeForestPath"
            ]
        )
        let forestPath = try XCTUnwrap(options.first { $0.id == "themeForestPath" })
        let neonNights = try XCTUnwrap(options.first { $0.id == "themeNeonNights" })

        XCTAssertTrue(forestPath.isUnlocked)
        XCTAssertTrue(forestPath.isSelected)
        XCTAssertFalse(neonNights.isUnlocked)
        XCTAssertEqual(options.filter(\.isSelected).map(\.id), ["themeForestPath"])
    }

    func testEveryDefaultSelectedCosmeticExistsInCatalog() {
        let catalogIDs = Set(service.cosmeticOptions.map(\.id))

        for cosmeticID in PlayerProfile.defaultSelectedCosmeticIDByCategoryID.values {
            XCTAssertTrue(catalogIDs.contains(cosmeticID), "\(cosmeticID) should exist in the catalog")
        }
    }

    func testEveryDefaultOwnedCosmeticExistsInCatalog() {
        let catalogIDs = Set(service.cosmeticOptions.map(\.id))

        for cosmeticID in PlayerProfile.defaultOwnedCosmeticIDs {
            XCTAssertTrue(catalogIDs.contains(cosmeticID), "\(cosmeticID) should exist in the catalog")
        }
    }

    func testEveryGameplayCategoryHasExactlyOneDefaultSelectedOption() {
        let gameplayCategoryIDs = [
            ShopCosmeticCategoryID.routeThemes,
            ShopCosmeticCategoryID.deliveryDots,
            ShopCosmeticCategoryID.trails,
            ShopCosmeticCategoryID.confetti,
            ShopCosmeticCategoryID.destinations
        ]

        for categoryID in gameplayCategoryIDs {
            let defaultSelectedIDs = PlayerProfile.defaultSelectedCosmeticIDByCategoryID.filter { $0.key == categoryID }
            let selectedCatalogOptions = service.options(forCategoryID: categoryID).filter(\.isSelected)

            XCTAssertEqual(defaultSelectedIDs.count, 1, "\(categoryID) should have one default selected ID")
            XCTAssertEqual(selectedCatalogOptions.count, 1, "\(categoryID) should have one selected catalog option")
            XCTAssertEqual(selectedCatalogOptions.first?.id, defaultSelectedIDs[categoryID])
        }
    }

    func testEveryCosmeticCategoryHasAtLeastOneFreeDefaultOwnedOption() {
        for category in service.categories {
            let defaultOwnedOptions = service.options(forCategoryID: category.id).filter { option in
                PlayerProfile.defaultOwnedCosmeticIDs.contains(option.id) && option.price == nil
            }

            XCTAssertFalse(defaultOwnedOptions.isEmpty, "\(category.title) should have a free default owned option")
        }
    }
}
