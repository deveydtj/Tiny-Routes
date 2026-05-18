import XCTest
@testable import TinyRoutes

final class ExperimentalLevelSolverTests: XCTestCase {
    private let decoder = JSONDecoder()

    func testFindSolutionReturnsCompletionForSimpleFixtureLevel() throws {
        let level = try decodeSolverFixture(named: "simple_single_switch")
        let solver = ExperimentalLevelSolver()

        let solution = try solver.findSolution(for: level)

        let unwrapped = try XCTUnwrap(solution)
        XCTAssertEqual(unwrapped.result.outcome, .completed)
        XCTAssertEqual(unwrapped.actions.count, 1)
        XCTAssertEqual(unwrapped.actions.first?.tapNodeID, "switch")
    }

    private func decodeSolverFixture(named fixtureName: String) throws -> LevelData {
        let fixtureURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures")
            .appendingPathComponent("SolverLevels")
            .appendingPathComponent("\(fixtureName).json")
        let data = try Data(contentsOf: fixtureURL)
        return try decoder.decode(LevelData.self, from: data)
    }
}
