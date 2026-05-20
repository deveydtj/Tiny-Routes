import XCTest
@testable import TinyRoutes

final class LevelSelectLayoutTests: XCTestCase {

    // MARK: - Helpers

    private let layout = TRSerpentineLayout(
        tileSize: CGSize(width: 92, height: 104),
        horizontalSpacing: 16,
        verticalSpacing: 24
    )

    /// Creates a minimal `LevelData` stub with a given 1-based level number.
    private func makeLevel(_ number: Int) -> LevelData {
        LevelData(
            id: "level_\(String(format: "%03d", number))",
            name: "Level \(number)",
            graph: RouteGraph(),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: 60,
            parTaps: 6
        )
    }

    private func makeLevels(_ count: Int) -> [LevelData] {
        (1...count).map { makeLevel($0) }
    }

    // MARK: - First row (row 0, left → right)

    func testLevel1IsAtRow0Column0() {
        let positions = layout.positions(for: makeLevels(8))
        let pos = positions.first { $0.levelNumber == 1 }!
        XCTAssertEqual(pos.row, 0)
        XCTAssertEqual(pos.column, 0)
    }

    func testLevel4IsAtRow0Column3() {
        let positions = layout.positions(for: makeLevels(8))
        let pos = positions.first { $0.levelNumber == 4 }!
        XCTAssertEqual(pos.row, 0)
        XCTAssertEqual(pos.column, 3)
    }

    // MARK: - Second row (row 1, right → left)

    func testLevel5IsAtRow1Column3() {
        let positions = layout.positions(for: makeLevels(8))
        let pos = positions.first { $0.levelNumber == 5 }!
        XCTAssertEqual(pos.row, 1)
        XCTAssertEqual(pos.column, 3)
    }

    func testLevel8IsAtRow1Column0() {
        let positions = layout.positions(for: makeLevels(8))
        let pos = positions.first { $0.levelNumber == 8 }!
        XCTAssertEqual(pos.row, 1)
        XCTAssertEqual(pos.column, 0)
    }

    // MARK: - Third row (row 2, left → right)

    func testLevel9IsAtRow2Column0() {
        let positions = layout.positions(for: makeLevels(12))
        let pos = positions.first { $0.levelNumber == 9 }!
        XCTAssertEqual(pos.row, 2)
        XCTAssertEqual(pos.column, 0)
    }

    // MARK: - Row 0 order: columns must be 0, 1, 2, 3

    func testRow0ColumnsIncreaseLeftToRight() {
        let positions = layout.positions(for: makeLevels(8))
        let row0 = positions.filter { $0.row == 0 }.sorted { $0.levelNumber < $1.levelNumber }
        XCTAssertEqual(row0.map(\.column), [0, 1, 2, 3])
    }

    // MARK: - Row 1 order: columns must be 3, 2, 1, 0

    func testRow1ColumnsDecreaseRightToLeft() {
        let positions = layout.positions(for: makeLevels(8))
        let row1 = positions.filter { $0.row == 1 }.sorted { $0.levelNumber < $1.levelNumber }
        XCTAssertEqual(row1.map(\.column), [3, 2, 1, 0])
    }

    // MARK: - Level IDs are preserved

    func testLevelIDsArePreserved() {
        let levels = makeLevels(4)
        let positions = layout.positions(for: levels)
        let ids = positions.sorted { $0.levelNumber < $1.levelNumber }.map(\.levelID)
        XCTAssertEqual(ids, ["level_001", "level_002", "level_003", "level_004"])
    }

    // MARK: - Works for 12, 16, and 24 levels

    func testLayoutFor12Levels() {
        let positions = layout.positions(for: makeLevels(12))
        XCTAssertEqual(positions.count, 12)
        // Row 2 is left-to-right: level 9 at col 0, level 12 at col 3
        let level9 = positions.first { $0.levelNumber == 9 }!
        let level12 = positions.first { $0.levelNumber == 12 }!
        XCTAssertEqual(level9.column, 0)
        XCTAssertEqual(level12.column, 3)
    }

    func testLayoutFor16Levels() {
        let positions = layout.positions(for: makeLevels(16))
        XCTAssertEqual(positions.count, 16)
        // Row 3 is right-to-left: level 13 at col 3, level 16 at col 0
        let level13 = positions.first { $0.levelNumber == 13 }!
        let level16 = positions.first { $0.levelNumber == 16 }!
        XCTAssertEqual(level13.column, 3)
        XCTAssertEqual(level16.column, 0)
    }

    func testLayoutFor24Levels() {
        let positions = layout.positions(for: makeLevels(24))
        XCTAssertEqual(positions.count, 24)
        // Row 5 is right-to-left: level 21 at col 3, level 24 at col 0
        let level21 = positions.first { $0.levelNumber == 21 }!
        let level24 = positions.first { $0.levelNumber == 24 }!
        XCTAssertEqual(level21.column, 3)
        XCTAssertEqual(level24.column, 0)
    }

    // MARK: - Center points are unique and ordered correctly

    func testCenterPointsAreDistinct() {
        struct CGPointKey: Hashable {
            let x: CGFloat
            let y: CGFloat
        }
        let positions = layout.positions(for: makeLevels(8))
        let centers = Set(positions.map { CGPointKey(x: $0.center.x, y: $0.center.y) })
        XCTAssertEqual(centers.count, 8, "All center points should be unique")
    }

    func testCenterXMatchesColumn() {
        let positions = layout.positions(for: makeLevels(4))
        for pos in positions {
            let expectedX = CGFloat(pos.column) * (layout.tileSize.width + layout.horizontalSpacing) + layout.tileSize.width / 2
            XCTAssertEqual(pos.center.x, expectedX, accuracy: 0.001)
        }
    }

    func testCenterYMatchesRow() {
        let positions = layout.positions(for: makeLevels(8))
        for pos in positions {
            let expectedY = CGFloat(pos.row) * (layout.tileSize.height + layout.verticalSpacing) + layout.tileSize.height / 2
            XCTAssertEqual(pos.center.y, expectedY, accuracy: 0.001)
        }
    }
}
