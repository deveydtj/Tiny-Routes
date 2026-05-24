import Foundation
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
    /// Simulations run outside the cache lock so one bad run cannot block every reader.
    private func simulationEntries() throws -> [SimulationEntry] {
        Self.cacheLock.lock()
        if let cached = Self.simulationCache {
            Self.cacheLock.unlock()
            return cached
        }
        Self.cacheLock.unlock()

        let pairs = try levelsWithScripts()
        let entries = pairs.map { level, script in
            SimulationEntry(
                level: level,
                script: script,
                outcome: Result { try harness.run(level: level, script: script) }
            )
        }

        Self.cacheLock.lock()
        if let cached = Self.simulationCache {
            Self.cacheLock.unlock()
            return cached
        }
        Self.simulationCache = entries
        Self.cacheLock.unlock()
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
                    // Placeholder script - skip until a real solution is available.
                    continue
                }
                result.append((level, script))
            } catch LevelSolutionRepositoryError.fileNotFound(_) {
                // No solution script exists yet for this level - skip it.
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
                failures.append(
                    describeFailure(
                        level: entry.level,
                        script: entry.script,
                        error: error,
                        context: "Harness threw before completion."
                    )
                )
            case .success(let result) where result.outcome != .completed:
                failures.append(
                    describeFailure(
                        level: entry.level,
                        script: entry.script,
                        result: result,
                        context: "Expected .completed."
                    )
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
                failures.append(
                    describeFailure(
                        level: entry.level,
                        script: entry.script,
                        error: error,
                        context: "Harness threw before verifying time-limit completion."
                    )
                )
            case .success(let result) where result.outcome != .completed:
                failures.append(
                    describeFailure(
                        level: entry.level,
                        script: entry.script,
                        result: result,
                        context: "Expected .completed within the level time limit."
                    )
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
                failures.append(
                    describeFailure(
                        level: entry.level,
                        script: entry.script,
                        error: error,
                        context: "Harness threw before verifying tap count."
                    )
                )
            case .success(let result):
                guard result.outcome == .completed else {
                    failures.append(
                        describeFailure(
                            level: entry.level,
                            script: entry.script,
                            result: result,
                            context: "Did not complete; cannot verify script maxTaps."
                        )
                    )
                    continue
                }
                if result.tapCount > entry.script.maxTaps {
                    failures.append(
                        describeFailure(
                            level: entry.level,
                            script: entry.script,
                            result: result,
                            context: "Tap count \(result.tapCount) exceeds script maxTaps \(entry.script.maxTaps)."
                        )
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
                failures.append(
                    describeFailure(
                        level: entry.level,
                        script: entry.script,
                        error: error,
                        context: "Harness threw before verifying par taps."
                    )
                )
            case .success(let result):
                guard result.outcome == .completed else {
                    failures.append(
                        describeFailure(
                            level: entry.level,
                            script: entry.script,
                            result: result,
                            context: "Did not complete; cannot verify par tap count."
                        )
                    )
                    continue
                }
                if result.tapCount > entry.level.parTaps {
                    failures.append(
                        describeFailure(
                            level: entry.level,
                            script: entry.script,
                            result: result,
                            context: "Par script tap count \(result.tapCount) exceeds level parTaps \(entry.level.parTaps)."
                        )
                    )
                }
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Par solution scripts exceeded level parTaps:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testProductionLevelSolutionScriptsMeetMinimumTapSpacing() throws {
        let pairs = try levelsWithScripts()
        let failures = pairs
            .flatMap { _, script in
                LevelHumanPlayabilityRules.tapSpacingViolations(for: script)
            }

        XCTAssertTrue(
            failures.isEmpty,
            "Level solution scripts require taps that are too close together:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testProductionCompletedSolutionsLeaveMinimumCompletionBuffer() throws {
        let entries = try simulationEntries()
        var failures: [String] = []

        for entry in entries {
            switch entry.outcome {
            case .failure(let error):
                failures.append(
                    describeFailure(
                        level: entry.level,
                        script: entry.script,
                        error: error,
                        context: "Harness threw before verifying completion buffer."
                    )
                )
            case .success(let result):
                guard result.outcome == .completed else {
                    failures.append(
                        describeFailure(
                            level: entry.level,
                            script: entry.script,
                            result: result,
                            context: "Did not complete; cannot verify completion buffer."
                        )
                    )
                    continue
                }
                if let violation = LevelHumanPlayabilityRules.completionBufferViolation(
                    level: entry.level,
                    result: result
                ) {
                    failures.append(
                        describeFailure(
                            level: entry.level,
                            script: entry.script,
                            result: result,
                            context: violation
                        )
                    )
                }
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Completed solutions must leave a minimum time buffer:\n\(failures.joined(separator: "\n"))"
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
            XCTFail(
                describeFailure(
                    level: entry.level,
                    script: entry.script,
                    error: error,
                    context: "level_001 harness threw."
                )
            )
        case .success(let result):
            XCTAssertEqual(
                result.outcome,
                .completed,
                describeFailure(
                    level: entry.level,
                    script: entry.script,
                    result: result,
                    context: "level_001 expected .completed."
                )
            )
            XCTAssertEqual(result.tapCount, 0, "level_001: expected 0 taps but got \(result.tapCount)")
        }
    }

    private func describeFailure(
        level: LevelData,
        script: LevelSolutionScript,
        result: LevelSolvabilityResult? = nil,
        error: Error? = nil,
        context: String
    ) -> String {
        let actualOutcome = result.map { String(describing: $0.outcome) } ?? "nil"
        let lastAction = result?.executedActions.last.map(describeAction) ?? "nil"
        let details = [
            "level id: \(level.id)",
            "script id: \(script.levelID)",
            "expected outcome: \(script.expectedOutcome.rawValue)",
            "actual outcome: \(actualOutcome)",
            "level time limit: \(level.timeLimitSeconds)s",
            "elapsed time: \(result.map { format($0.elapsedTime) } ?? "nil")",
            "time remaining: \(result?.timeRemaining.map(format) ?? "nil")",
            "tap count: \(result.map { "\($0.tapCount)" } ?? "nil")",
            "script maxTaps: \(script.maxTaps)",
            "step count: \(result.map { "\($0.stepCount)" } ?? "nil")",
            "no-progress step count: \(result.map { "\($0.noProgressStepCount)" } ?? "nil")",
            "final node: \(result?.finalNodeID ?? "nil")",
            "current edge: \(result?.currentEdgeID ?? "nil")",
            "progress along edge: \(result?.progressAlongEdge.map(format) ?? "nil")",
            "package collected: \(result.map { "\($0.didCollectPackage)" } ?? "nil")",
            "last executed action: \(lastAction)",
            "harness error: \(error?.localizedDescription ?? "nil")"
        ]

        return """
        \(context)
          \(details.joined(separator: "\n  "))
        """
    }

    private func describeAction(_ action: ExecutedLevelSolutionAction) -> String {
        "time=\(format(action.requestedTime))s node=\(action.nodeID) didRotate=\(action.didRotate) tapCount=\(action.actualTapCountAfterAction)"
    }

    private func format(_ value: TimeInterval) -> String {
        String(format: "%.4f", value)
    }
}
