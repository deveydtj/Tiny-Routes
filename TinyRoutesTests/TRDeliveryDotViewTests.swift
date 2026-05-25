import SwiftUI
import XCTest
@testable import TinyRoutes

final class TRDeliveryDotViewTests: XCTestCase {
    private let catalogService = ShopCatalogService()

    @MainActor
    func testDeliveryDotViewCanBeConstructedForEveryDotOption() {
        for option in catalogService.options(forCategoryID: ShopCosmeticCategoryID.deliveryDots) {
            let view = TRDeliveryDotView(
                option: option,
                isMoving: false,
                outerSize: TRGameplayStyle.Metrics.playerOuterSize,
                coreSize: TRGameplayStyle.Metrics.playerCoreSize,
                scale: TRGameplayStyle.Metrics.playerScale
            )

            XCTAssertNotNil(view)
        }
    }

    @MainActor
    func testDeliveryDotViewCanRenderMovingAndIdleStates() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "dotCourierBlue"))
        let idleView = TRDeliveryDotView(
            option: option,
            isMoving: false,
            outerSize: 52,
            coreSize: 40,
            scale: 0.75
        )
        let movingView = TRDeliveryDotView(
            option: option,
            isMoving: true,
            outerSize: 52,
            coreSize: 40,
            scale: 0.75
        )

        XCTAssertNotNil(idleView)
        XCTAssertNotNil(movingView)
    }

    @MainActor
    func testUnknownDotOptionFallsBackSafely() {
        let option = ShopCosmeticOption(
            id: "unknownDot",
            categoryID: "unknown",
            title: "Unknown",
            price: nil,
            isUnlocked: true,
            isSelected: false,
            accent: .classic
        )
        let view = TRDeliveryDotView(
            option: option,
            isMoving: true,
            outerSize: 52,
            coreSize: 40,
            scale: 0.75
        )

        XCTAssertNotNil(view)
        XCTAssertFalse(TRDeliveryDotVisual.colors(for: option).isEmpty)
    }
}
