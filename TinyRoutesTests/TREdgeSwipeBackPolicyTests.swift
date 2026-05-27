import CoreGraphics
import XCTest
@testable import TinyRoutes

final class TREdgeSwipeBackPolicyTests: XCTestCase {
    func testTriggersForRightSwipeStartingAtLeftEdge() {
        XCTAssertTrue(
            TREdgeSwipeBackPolicy.shouldTriggerBack(
                startLocation: CGPoint(x: 12, y: 120),
                translation: CGSize(width: 80, height: 8),
                predictedEndTranslation: CGSize(width: 100, height: 8)
            )
        )
    }

    func testDoesNotTriggerAwayFromLeftEdge() {
        XCTAssertFalse(
            TREdgeSwipeBackPolicy.shouldTriggerBack(
                startLocation: CGPoint(x: 80, y: 120),
                translation: CGSize(width: 100, height: 4),
                predictedEndTranslation: CGSize(width: 120, height: 4)
            )
        )
    }

    func testDoesNotTriggerForShortDrag() {
        XCTAssertFalse(
            TREdgeSwipeBackPolicy.shouldTriggerBack(
                startLocation: CGPoint(x: 12, y: 120),
                translation: CGSize(width: 20, height: 2),
                predictedEndTranslation: CGSize(width: 30, height: 2)
            )
        )
    }

    func testDoesNotTriggerForVerticalScroll() {
        XCTAssertFalse(
            TREdgeSwipeBackPolicy.shouldTriggerBack(
                startLocation: CGPoint(x: 12, y: 120),
                translation: CGSize(width: 40, height: 120),
                predictedEndTranslation: CGSize(width: 60, height: 160)
            )
        )
    }

    func testDoesNotTriggerForLeftSwipe() {
        XCTAssertFalse(
            TREdgeSwipeBackPolicy.shouldTriggerBack(
                startLocation: CGPoint(x: 12, y: 120),
                translation: CGSize(width: -90, height: 4),
                predictedEndTranslation: CGSize(width: -110, height: 4)
            )
        )
    }
}
