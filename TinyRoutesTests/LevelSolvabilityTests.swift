import XCTest
@testable import TinyRoutes

final class LevelSolvabilityTests: XCTestCase {
    private let catalog = TestLevelCatalog()
    private let solutionRepository = LevelSolutionRepository()
    private let harness = LevelSimulationHarness(
        engineFactory: { RouteEngine(dotSpeed: 100) },
        frameStep: 0.1
    )

    // MARK: - Helpers

    private func levelsWithScripts() throws -> [(level: LevelData, script: LevelSolutionScript)] {
        let levels = try catalog.loadAllProductionLevels()
        return levels.compactMap { level in
            guard let script = try? solutionRepository.loadScript(levelID: level.id) else {
                return nil
            }
            return (level, script)
        }
    }

    // MARK: - Tests

    func testEveryProductionLevelCanBeCompletedByItsSolutionScript() throws {
        let pairs = try levelsWithScripts()
        var failures: [String] = []

        for (level, script) in pairs {
            let result: LevelSolvabilityResult
            do {
                result = try harness.run(level: level, script: script)
            } catch {
                failures.append("\(level.id): harness threw \(error.localizedDescription)")
                continue
            }

            if result.outcome != .completed {
                failures.append(
                    "\(level.id): expected .completed but got \(String(describing: result.outcome))"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Level solvability failures:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testEveryProductionLevelCompletesWithinTimeLimit() throws {
        let pairs = try levelsWithScripts()
        var failures: [String] = []

        for (level, script) in pairs where script.requiresWithinTimeLimit {
            guard let result = try? harness.run(level: level, script: script),
                  result.outcome == .completed else {
                continue
            }

            let timeLimit = TimeInterval(level.timeLimitSeconds)
            if result.elapsedTime > timeLimit {
                failures.append(
                    "\(level.id): elapsed \(result.elapsedTime)s exceeds time limit \(level.timeLimitSeconds)s"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Levels completed outside time limit:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testEveryProductionLevelCompletesWithinDeclaredMaxTaps() throws {
        let pairs = try levelsWithScripts()
        var failures: [String] = []

        for (level, script) in pairs {
            guard let result = try? harness.run(level: level, script: script),
                  result.outcome == .completed else {
                continue
            }

            if result.tapCount > script.maxTaps {
                failures.append(
                    "\(level.id): tap count \(result.tapCount) exceeds script maxTaps \(script.maxTaps)"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Levels exceeded script maxTaps:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testParSolutionScriptsDoNotExceedLevelParTaps() throws {
        let pairs = try levelsWithScripts()
        var failures: [String] = []

        for (level, script) in pairs where script.maxTaps <= level.parTaps {
            guard let result = try? harness.run(level: level, script: script),
                  result.outcome == .completed else {
                continue
            }

            if result.tapCount > level.parTaps {
                failures.append(
                    "\(level.id): par script tap count \(result.tapCount) exceeds level parTaps \(level.parTaps)"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Par solution scripts exceeded level parTaps:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testLevel001CompletesWithZeroTaps() throws {
        let level = try XCTUnwrap(
            catalog.loadAllProductionLevels().first(where: { $0.id == "level_001" }),
            "level_001 not found in production levels"
        )
        let script = try solutionRepository.loadScript(levelID: "level_001")
        let result = try harness.run(level: level, script: script)

        XCTAssertEqual(
            result.outcome,
            .completed,
            "level_001: expected .completed but got \(String(describing: result.outcome))"
        )
        XCTAssertEqual(result.tapCount, 0, "level_001: expected 0 taps but got \(result.tapCount)")
        XCTAssertLessThanOrEqual(
            result.elapsedTime,
            TimeInterval(level.timeLimitSeconds),
            "level_001: elapsed \(result.elapsedTime)s exceeds time limit \(level.timeLimitSeconds)s"
        )
    }
}
