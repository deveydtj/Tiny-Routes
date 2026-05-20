import XCTest
@testable import TinyRoutes

final class TRLevelPathViewTests: XCTestCase {
    private let layout = TRSerpentineLayout(
        tileSize: TRLevelTile.size,
        horizontalSpacing: 16,
        verticalSpacing: 24
    )

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

    func testHorizontalSegmentsAreCreatedBetweenAdjacentTilesPerRow() {
        let positions = layout.positions(for: makeLevels(8))
        let states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.current) })

        let segments = makeHorizontalSegments(positions: positions, tileStatesByLevelID: states)

        XCTAssertEqual(segments.count, 6)
    }

    func testSegmentUnlockStateUsesBothConnectedTileStates() {
        let positions = layout.positions(for: makeLevels(8))
        var states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.locked) })
        [1, 2, 3, 4].forEach { number in
            states["level_\(String(format: "%03d", number))"] = .completed
        }

        let segments = makeHorizontalSegments(positions: positions, tileStatesByLevelID: states)

        let unlockedCount = segments.filter(\.isUnlocked).count
        XCTAssertEqual(unlockedCount, 3)
    }
}
