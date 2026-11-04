import Foundation
import XCTest
@testable import TinyRoutes

final class LevelSolvabilityTests: XCTestCase {
    private let catalog = TestLevelCatalog()
    private let solutionRepository = LevelSolutionRepository()
    // Uses default production-equivalent parameters: RouteEngine() (dotSpeed 1) and frameStep 1/60.
    private let harness = LevelSimulationHarness()

    // The bundled single-dot corpus was retired; this hook still validates
    // externally generated levels for the level generator tooling.

    func testRequestedGeneratedLevelsCompleteFromEnvironmentDirectories() throws {
        let environment = ProcessInfo.processInfo.environment
        guard let rawLevelIDs = environment["TINY_ROUTES_VALIDATION_LEVEL_IDS"],
              !rawLevelIDs.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw XCTSkip("No generated level IDs requested for external Swift validation.")
        }
        guard let levelsPath = environment["TINY_ROUTES_LEVELS_DIR"],
              let solutionsPath = environment["TINY_ROUTES_SOLUTIONS_DIR"] else {
            XCTFail("TINY_ROUTES_LEVELS_DIR and TINY_ROUTES_SOLUTIONS_DIR are required when TINY_ROUTES_VALIDATION_LEVEL_IDS is set.")
            return
        }

        let levelIDs = rawLevelIDs
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let levelsDirectory = URL(fileURLWithPath: levelsPath, isDirectory: true)
        let solutionsDirectory = URL(fileURLWithPath: solutionsPath, isDirectory: true)
        var failures: [String] = []

        for levelID in levelIDs {
            let level = try catalog.loadLevel(levelID: levelID, from: levelsDirectory)
            let script = try solutionRepository.loadScript(levelID: levelID, from: solutionsDirectory)
            let result = Result { try harness.run(level: level, script: script) }

            switch result {
            case .failure(let error):
                failures.append(
                    describeFailure(
                        level: level,
                        script: script,
                        error: error,
                        context: "External generated level harness threw."
                    )
                )
            case .success(let solvability) where solvability.outcome != .completed:
                failures.append(
                    describeFailure(
                        level: level,
                        script: script,
                        result: solvability,
                        context: "External generated level expected .completed."
                    )
                )
            case .success:
                break
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "External generated level solvability failures:\n\(failures.joined(separator: "\n"))"
        )
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
