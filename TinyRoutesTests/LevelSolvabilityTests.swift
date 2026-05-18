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
        let outcome: Result<LevelSolvabilityResult, Error>
    }

    /// Serializes all reads and writes of `simulationCache` so parallel test execution is safe.
    private static let cacheLock = NSLock()
    /// Static cache so each level is simulated at most once across all test methods in the suite.
    private static var simulationCache: [SimulationEntry]?

    override class func tearDown() {
        cacheLock.lock()
        simulationCache = nil
        cacheLock.unlock()
        super.tearDown()
    }

    /// Returns cached simulation results, computing them on first call.
    /// The lock is held for the full initialization so only one thread populates the cache.
    private func simulationEntries() throws -> [SimulationEntry] {
        Self.cacheLock.lock()
        defer { Self.cacheLock.unlock() }
        if let cached = Self.simulationCache {
            return cached
        }
        let pairs = try levelsWithScripts()
        let entries = pairs.map { level, script in
            SimulationEntry(
                level: level,
                script: script,
                outcome: Result { try harness.run(level: level, script: script) }
            )
        }
        Self.simulationCache = entries
        return entries
    }

    // MARK: - Helpers

    /// Returns all production levels paired with their solution scripts.
    /// Levels whose script file does not exist (`fileNotFound`) are silently skipped.
    /// Levels whose script is marked `isPlaceholder` are silently skipped until Task 019 provides real solutions.
    /// Any other loading error (e.g. decoding failure) is rethrown immediately.
    private func levelsWithScripts() throws -> [(level: LevelData, script: LevelSolutionScript)] {
        let levels = try catalog.loadAllProductionLevels()
        var result: [(level: LevelData, script: LevelSolutionScript)] = []
        for level in levels {
            do {
                let script = try solutionRepository.loadScript(levelID: level.id)
                guard !script.isPlaceholder else {
                    // Placeholder script — skip until real solution is available (Task 019).
                    continue
                }
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
            switch entry.outcome {
            case .failure(let error):
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
            case .success(let result) where result.outcome != .completed:
                failures.append(
                    "\(entry.level.id): expected .completed but got \(String(describing: result.outcome))"
                )
            case .success:
                break
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
            switch entry.outcome {
            case .failure(let error):
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
            case .success(let result) where result.outcome != .completed:
                failures.append(
                    "\(entry.level.id): expected .completed but got \(String(describing: result.outcome))"
                )
            case .success:
                break
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
            switch entry.outcome {
            case .failure(let error):
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
            case .success(let result):
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
            switch entry.outcome {
            case .failure(let error):
                failures.append("\(entry.level.id): harness threw \(error.localizedDescription)")
            case .success(let result):
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

        switch entry.outcome {
        case .failure(let error):
            XCTFail("level_001: harness threw \(error.localizedDescription)")
        case .success(let result):
            XCTAssertEqual(
                result.outcome,
                .completed,
                "level_001: expected .completed but got \(String(describing: result.outcome))"
            )
            XCTAssertEqual(result.tapCount, 0, "level_001: expected 0 taps but got \(result.tapCount)")
        }
    }
}
