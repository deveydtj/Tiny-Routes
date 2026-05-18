import Foundation
@testable import TinyRoutes

/// EXPERIMENTAL SPIKE:
/// Brute-force solver for small fixture levels only.
/// This is intentionally isolated from production-level solvability validation.
struct ExperimentalLevelSolver {
    struct SearchConfiguration {
        var maximumTapCount: Int = 4
        var firstTapTimeSeconds: TimeInterval = 0.50
        var tapSpacingSeconds: TimeInterval = 0.50
    }

    struct Solution {
        let actions: [LevelSolutionAction]
        let result: LevelSolvabilityResult
    }

    private let harness: LevelSimulationHarness

    init(harness: LevelSimulationHarness = LevelSimulationHarness()) {
        self.harness = harness
    }

    func findSolution(
        for level: LevelData,
        configuration: SearchConfiguration = SearchConfiguration()
    ) throws -> Solution? {
        let switchNodeIDs = level.graph.nodes
            .filter { $0.outgoingEdgeIDs.count > 1 }
            .map(\.id)
            .sorted()
        let maximumTapCount = max(configuration.maximumTapCount, 0)
        let firstTapTimeSeconds = max(configuration.firstTapTimeSeconds, 0)
        let tapSpacingSeconds = max(configuration.tapSpacingSeconds, 0.01)

        for tapCount in 0...maximumTapCount {
            let tapNodeSequences = sequences(nodeIDs: switchNodeIDs, count: tapCount)
            for tapNodeSequence in tapNodeSequences {
                let actions = tapNodeSequence.enumerated().map { index, nodeID in
                    LevelSolutionAction(
                        timeSeconds: firstTapTimeSeconds + (TimeInterval(index) * tapSpacingSeconds),
                        tapNodeID: nodeID
                    )
                }
                let script = LevelSolutionScript(
                    levelID: level.id,
                    description: "experimental_solver_candidate_taps_\(tapCount)",
                    expectedOutcome: .completed,
                    maxTaps: maximumTapCount,
                    requiresWithinTimeLimit: true,
                    actions: actions
                )
                let result = try harness.run(level: level, script: script)
                if result.outcome == .completed {
                    return Solution(actions: actions, result: result)
                }
            }
        }

        return nil
    }

    private func sequences(nodeIDs: [String], count: Int) -> [[String]] {
        guard count > 0 else {
            return [[]]
        }
        guard !nodeIDs.isEmpty else {
            return []
        }

        var result = [[String]]([[]])
        for _ in 0..<count {
            result = result.flatMap { prefix in
                nodeIDs.map { nodeID in
                    var sequence = prefix
                    sequence.append(nodeID)
                    return sequence
                }
            }
        }
        return result
    }
}
