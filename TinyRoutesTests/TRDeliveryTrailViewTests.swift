import SwiftUI
import XCTest
@testable import TinyRoutes

final class TRDeliveryTrailViewTests: XCTestCase {
    private let catalogService = ShopCatalogService()

    @MainActor
    func testTrailViewCanBeConstructedForEveryTrailOption() {
        for option in catalogService.options(forCategoryID: ShopCosmeticCategoryID.trails) {
            let view = TRDeliveryTrailView(
                option: option,
                dotPoint: CGPoint(x: 100, y: 100),
                isMoving: true
            )

            XCTAssertNotNil(view)
        }
    }

    @MainActor
    func testTrailViewCanBeConstructedForIdleState() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "trailClean"))
        let view = TRDeliveryTrailView(
            option: option,
            dotPoint: CGPoint(x: 40, y: 40),
            isMoving: false
        )

        XCTAssertNotNil(view)
    }

    @MainActor
    func testTrailViewCanBeConstructedForMovingState() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "trailNeon"))
        let roadPath = Path { path in
            path.move(to: CGPoint(x: 0, y: 20))
            path.addLine(to: CGPoint(x: 120, y: 20))
        }
        let view = TRDeliveryTrailView(
            option: option,
            dotPoint: CGPoint(x: 80, y: 20),
            isMoving: true,
            roadPath: roadPath
        )

        XCTAssertNotNil(view)
    }
}
