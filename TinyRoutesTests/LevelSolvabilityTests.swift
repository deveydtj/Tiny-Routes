import XCTest
@testable import TinyRoutes

final class LevelSolvabilityTests: XCTestCase {
    private let catalog = TestLevelCatalog()
    private let solutionRepository = LevelSolutionRepository()
    // Uses default production-equivalent parameters: RouteEngine() (dotSpeed 1) and frameStep 1/60.
    private let harness = LevelSimulationHarness()

    // MARK: - Simulation cache

    private struct SimulationEntry {
        let level: LevelData
        let script: LevelSolutionScript
        let result: LevelSolvabilityResult?
        let harnessError: Error?
    }

    /// Static cache so each level is simulated at most once across all test methods in the suite.
    private static var simulationCache: [SimulationEntry]?

    /// Returns cached simulation results, computing them on first call.
    private func simulationEntries() throws -> [SimulationEntry] {
        if let cached = Self.simulationCache {
            return cached
        }
        let pairs = try levelsWithScripts()
        var entries: [SimulationEntry] = []
        for (level, script) in pairs {
            do {
                let result = try harness.run(level: level, script: script)
                entries.append(SimulationEntry(level: level, script: script, result: result, harnessError: nil))
            } catch {
                entries.append(SimulationEntry(level: level, script: script, result: nil, harnessError: error))
            }
        }
        Self.simulationCache = entries
        return entries
    }

    // MARK: - Helpers

    /// Returns all production levels paired with their solution scripts.
    /// Levels whose script file does not exist (`fileNotFound`) are silently skipped.
    /// Any other loading error (e.g. decoding failure) is rethrown immediately.
    private func levelsWithScripts() throws -> [(level: LevelData, script: LevelSolutionScript)] {
        let levels = try catalog.loadAllProductionLevels()
        var result: [(level: LevelData, script: LevelSolutionScript)] = []
        for level in levels {
            do {
                let script = try solutionRepository.loadScript(levelID: level.id)
                result.append((level, script))
            } catch LevelSolutionRepositoryError.fileNotFound(_) {
                // No solution script exists yet for this level — skip it.
            } catch {
                throw error
            }
        }
        return result
    }

    // MARK: - Tests

    func testProductionLevelsWithScriptsAllComplete() throws {
        let entries = try simulationEntries()
        var failures: [String] = []

        for entry in entries {
            if let error = entry.harnessError {
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
            } else if entry.result?.outcome != .completed {
                failures.append(
                    "\(entry.level.id): expected .completed but got \(String(describing: entry.result?.outcome))"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Level solvability failures:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testProductionLevelsWithTimeLimitFlagCompleteWithinTimeLimit() throws {
        let entries = try simulationEntries()
        var failures: [String] = []

        for entry in entries where entry.script.requiresWithinTimeLimit {
            if let error = entry.harnessError {
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
            } else if entry.result?.outcome != .completed {
                failures.append(
                    "\(entry.level.id): expected .completed but got \(String(describing: entry.result?.outcome))"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Levels with requiresWithinTimeLimit did not complete:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testProductionLevelsWithScriptsCompleteWithinDeclaredMaxTaps() throws {
        let entries = try simulationEntries()
        var failures: [String] = []

        for entry in entries {
            if let error = entry.harnessError {
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
                continue
            }
            guard let result = entry.result else { continue }

            guard result.outcome == .completed else {
                failures.append(
                    "\(entry.level.id): did not complete (outcome: \(String(describing: result.outcome))); cannot verify tap count"
                )
                continue
            }

            if result.tapCount > entry.script.maxTaps {
                failures.append(
                    "\(entry.level.id): tap count \(result.tapCount) exceeds script maxTaps \(entry.script.maxTaps)"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Levels exceeded script maxTaps:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testParSolutionScriptsDoNotExceedLevelParTaps() throws {
        let entries = try simulationEntries()
        var failures: [String] = []

        for entry in entries where entry.script.maxTaps <= entry.level.parTaps {
            if let error = entry.harnessError {
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
                continue
            }
            guard let result = entry.result else { continue }

            guard result.outcome == .completed else {
                failures.append(
                    "\(entry.level.id): did not complete (outcome: \(String(describing: result.outcome))); cannot verify par tap count"
                )
                continue
            }

            if result.tapCount > entry.level.parTaps {
                failures.append(
                    "\(entry.level.id): par script tap count \(result.tapCount) exceeds level parTaps \(entry.level.parTaps)"
                )
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Par solution scripts exceeded level parTaps:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testLevel001CompletesWithZeroTaps() throws {
        let entries = try simulationEntries()
        let entry = try XCTUnwrap(
            entries.first(where: { $0.level.id == "level_001" }),
            "level_001 not found in simulation entries"
        )

        if let error = entry.harnessError {
            XCTFail("level_001: harness threw \(error.localizedDescription)")
            return
        }

        let result = try XCTUnwrap(entry.result)
        XCTAssertEqual(
            result.outcome,
            .completed,
            "level_001: expected .completed but got \(String(describing: result.outcome))"
        )
        XCTAssertEqual(result.tapCount, 0, "level_001: expected 0 taps but got \(result.tapCount)")
    }
}
