import SwiftUI
import XCTest
@testable import TinyRoutes

final class ShopScreenTests: XCTestCase {
    private let service = ShopCatalogService()

    @MainActor
    func testShopScreenCanBeConstructedWithCatalogData() {
        let screen = ShopScreen(
            coinTotal: 1_250,
            onSettingsTapped: {},
            onAddCurrencyTapped: {},
            catalogService: service
        )

        XCTAssertNotNil(screen)
    }

    @MainActor
    func testShopPinnedBalanceBarCanBeConstructed() {
        let bar = TRShopPinnedBalanceBar(
            coinTotal: 1_250,
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )

        XCTAssertNotNil(bar)
    }

    @MainActor
    func testCategoryPillBarCanBeConstructed() {
        let pillBar = TRShopCategoryPillBar(
            categories: service.categories,
            selectedCategoryID: ShopCosmeticCategoryID.routeThemes,
            onCategorySelected: { _ in }
        )

        XCTAssertNotNil(pillBar)
    }

    @MainActor
    func testFeaturedCardCanBeConstructed() throws {
        let offer = try XCTUnwrap(service.featuredOffers.first)
        let card = TRShopFeaturedCard(offer: offer, action: {})

        XCTAssertNotNil(card)
    }

    @MainActor
    func testCosmeticOptionCardCanBeConstructed() throws {
        let option = try XCTUnwrap(service.options(forCategoryID: ShopCosmeticCategoryID.routeThemes).first)
        let card = TRShopCosmeticOptionCard(option: option, action: {})

        XCTAssertNotNil(card)
    }

    @MainActor
    func testCosmeticGridCanBeConstructed() {
        let grid = TRShopCosmeticGrid(
            options: service.options(forCategoryID: ShopCosmeticCategoryID.routeThemes),
            onOptionTapped: { _ in }
        )

        XCTAssertNotNil(grid)
    }
}
