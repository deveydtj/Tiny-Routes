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
}
