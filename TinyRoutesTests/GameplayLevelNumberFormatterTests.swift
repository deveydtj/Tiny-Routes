import XCTest
@testable import TinyRoutes

final class GameplayLevelNumberFormatterTests: XCTestCase {
    func testLevelIDWithPaddedNumericSuffixDisplaysPlainNumber() {
        XCTAssertEqual(GameplayLevelNumberFormatter.title(for: "level_001"), "Level 1")
        XCTAssertEqual(GameplayLevelNumberFormatter.title(for: "level_012"), "Level 12")
    }

    func testCustomLevelIDFallsBackToID() {
        XCTAssertEqual(GameplayLevelNumberFormatter.title(for: "custom_id"), "Level custom_id")
    }

    func testEmptyLevelIDFallsBackToGenericLevelTitle() {
        XCTAssertEqual(GameplayLevelNumberFormatter.title(for: ""), "Level")
    }
}
