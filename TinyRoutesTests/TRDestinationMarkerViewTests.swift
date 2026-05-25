import SwiftUI
import XCTest
@testable import TinyRoutes

final class TRDestinationMarkerViewTests: XCTestCase {
    private let catalogService = ShopCatalogService()

    @MainActor
    func testDestinationMarkerCanBeConstructedForEveryDestinationOption() {
        for option in catalogService.options(forCategoryID: ShopCosmeticCategoryID.destinations) {
            let view = TRDestinationMarkerView(
                option: option,
                shellSize: TRGameplayStyle.Metrics.packageMarkerSize,
                iconSize: TRGameplayStyle.Metrics.markerIconSize
            )

            XCTAssertNotNil(view)
        }
    }

    func testDefaultFlagOptionUsesFinishFlagSprite() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "destinationFlag"))
        let visual = TRDestinationMarkerVisual(option: option)

        XCTAssertTrue(visual.usesFinishFlagSprite)
    }

    func testUnknownDestinationUsesSafeFallbackIcon() {
        XCTAssertEqual(
            TRDestinationMarkerVisual.systemImageName(forOptionID: "unknownDestination"),
            "mappin.circle.fill"
        )
    }
}
