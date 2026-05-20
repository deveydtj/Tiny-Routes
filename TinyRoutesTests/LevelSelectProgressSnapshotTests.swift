import XCTest
@testable import TinyRoutes

final class LevelSelectProgressSnapshotTests: XCTestCase {
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

    private func makeProgressService() -> ProgressService {
        let suiteName = "LevelSelectProgressSnapshotTests-\(UUID().uuidString)"
        let userDefaults = UserDefaults(suiteName: suiteName)!
        userDefaults.removePersistentDomain(forName: suiteName)
        return ProgressService(userDefaults: userDefaults, bestStarsByLevelIDKey: "bestStarsByLevelID")
    }

    func testNoProgressShowsCurrentThenLocked() {
        let levels = makeLevels(4)
        let progressService = makeProgressService()
        let snapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)

        XCTAssertEqual(snapshot.firstIncompleteIndex, 0)
        XCTAssertEqual(snapshot.tileState(at: 0, levelID: levels[0].id), .current)
        XCTAssertEqual(snapshot.tileState(at: 1, levelID: levels[1].id), .locked)
        XCTAssertEqual(snapshot.tileState(at: 2, levelID: levels[2].id), .locked)
        XCTAssertEqual(snapshot.tileState(at: 3, levelID: levels[3].id), .locked)
    }

    func testAllCompleteShowsAllCompleted() {
        let levels = makeLevels(4)
        let progressService = makeProgressService()
        levels.forEach { level in
            progressService.saveBestStars(3, for: level.id)
        }
        let snapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)

        XCTAssertEqual(snapshot.firstIncompleteIndex, levels.count)
        for (index, level) in levels.enumerated() {
            XCTAssertEqual(snapshot.tileState(at: index, levelID: level.id), .completed)
        }
    }

    func testNonContiguousCompletionsKeepCompletedTilesCompleted() {
        let levels = makeLevels(4)
        let progressService = makeProgressService()
        progressService.saveBestStars(3, for: levels[0].id)
        progressService.saveBestStars(2, for: levels[2].id)

        let snapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)

        XCTAssertEqual(snapshot.firstIncompleteIndex, 1)
        XCTAssertEqual(snapshot.tileState(at: 0, levelID: levels[0].id), .completed)
        XCTAssertEqual(snapshot.tileState(at: 1, levelID: levels[1].id), .current)
        XCTAssertEqual(snapshot.tileState(at: 2, levelID: levels[2].id), .completed)
        XCTAssertEqual(snapshot.tileState(at: 3, levelID: levels[3].id), .locked)
    }
}
