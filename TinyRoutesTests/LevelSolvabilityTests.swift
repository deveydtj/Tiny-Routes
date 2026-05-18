import XCTest
@testable import TinyRoutes

final class LevelSolvabilityTests: XCTestCase {
    private let catalog = TestLevelCatalog()
    private let solutionRepository = LevelSolutionRepository()
    // Uses default production-equivalent parameters: RouteEngine() (dotSpeed 1) and frameStep 1/60.
    private let harness = LevelSimulationHarness()

    // MARK: - Helpers

    /// Returns all production levels paired with their solution scripts.
    /// Levels without a solution script (`fileNotFound`) are silently skipped.
    /// Any other loading error (e.g. decoding failure) is rethrown immediately.
    private func levelsWithScripts() throws -> [(level: LevelData, script: LevelSolutionScript)] {
        let levels = try catalog.loadAllProductionLevels()
        var result: [(level: LevelData, script: LevelSolutionScript)] = []
        for level in levels {
            do {
                let script = try solutionRepository.loadScript(levelID: level.id)
                result.append((level, script))
            } catch LevelSolutionRepositoryError.fileNotFound {
                // No solution script exists yet for this level — skip it.
            } catch {
                throw error
            }
        }
        return result
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
            let result: LevelSolvabilityResult
            do {
                result = try harness.run(level: level, script: script)
            } catch {
                failures.append("\(level.id): harness threw \(error.localizedDescription)")
                continue
            }

            guard result.outcome == .completed else {
                failures.append(
                    "\(level.id): did not complete (outcome: \(String(describing: result.outcome))); cannot verify time limit"
                )
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
            let result: LevelSolvabilityResult
            do {
                result = try harness.run(level: level, script: script)
            } catch {
                failures.append("\(level.id): harness threw \(error.localizedDescription)")
                continue
            }

            guard result.outcome == .completed else {
                failures.append(
                    "\(level.id): did not complete (outcome: \(String(describing: result.outcome))); cannot verify tap count"
                )
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
            let result: LevelSolvabilityResult
            do {
                result = try harness.run(level: level, script: script)
            } catch {
                failures.append("\(level.id): harness threw \(error.localizedDescription)")
                continue
            }

            guard result.outcome == .completed else {
                failures.append(
                    "\(level.id): did not complete (outcome: \(String(describing: result.outcome))); cannot verify par tap count"
                )
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
            try catalog.loadAllProductionLevels().first(where: { $0.id == "level_001" }),
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
