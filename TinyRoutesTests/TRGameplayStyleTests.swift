import XCTest
@testable import TinyRoutes

final class TRGameplayStyleTests: XCTestCase {
    func testPlayerCoreSizeTracksConfiguredWhiteRimWidth() {
        let expectedCoreSize = TRGameplayStyle.Metrics.playerOuterSize - (TRGameplayStyle.Metrics.playerWhiteRimWidth * 2)

        XCTAssertEqual(TRGameplayStyle.Metrics.playerCoreSize, expectedCoreSize, accuracy: 0.0001)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.playerCoreSize, 0)
    }

    func testPlayerScaleIsAboutTwentyFivePercentSmallerThanPreviousSize() {
        let previousPlayerScale: CGFloat = 0.75
        let expectedPlayerScale = previousPlayerScale * 0.75

        XCTAssertEqual(TRGameplayStyle.Metrics.playerScale, expectedPlayerScale, accuracy: 0.0001)
    }
}
