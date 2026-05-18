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
            var candidateTapNodeIDs: [String] = []
            if let solution = try findSolution(
                for: level,
                switchNodeIDs: switchNodeIDs,
                targetTapCount: tapCount,
                firstTapTimeSeconds: firstTapTimeSeconds,
                tapSpacingSeconds: tapSpacingSeconds,
                candidateTapNodeIDs: &candidateTapNodeIDs
            ) {
                return solution
            }
        }

        return nil
    }

    private func findSolution(
        for level: LevelData,
        switchNodeIDs: [String],
        targetTapCount: Int,
        firstTapTimeSeconds: TimeInterval,
        tapSpacingSeconds: TimeInterval,
        candidateTapNodeIDs: inout [String]
    ) throws -> Solution? {
        if candidateTapNodeIDs.count == targetTapCount {
            return try evaluateCandidate(
                level: level,
                tapNodeIDs: candidateTapNodeIDs,
                firstTapTimeSeconds: firstTapTimeSeconds,
                tapSpacingSeconds: tapSpacingSeconds
            )
        }

        for switchNodeID in switchNodeIDs {
            candidateTapNodeIDs.append(switchNodeID)
            if let solution = try findSolution(
                for: level,
                switchNodeIDs: switchNodeIDs,
                targetTapCount: targetTapCount,
                firstTapTimeSeconds: firstTapTimeSeconds,
                tapSpacingSeconds: tapSpacingSeconds,
                candidateTapNodeIDs: &candidateTapNodeIDs
            ) {
                return solution
            }
            candidateTapNodeIDs.removeLast()
        }

        return nil
    }

    private func evaluateCandidate(
        level: LevelData,
        tapNodeIDs: [String],
        firstTapTimeSeconds: TimeInterval,
        tapSpacingSeconds: TimeInterval
    ) throws -> Solution? {
        let actions = tapNodeIDs.enumerated().map { index, nodeID in
            LevelSolutionAction(
                timeSeconds: firstTapTimeSeconds + (TimeInterval(index) * tapSpacingSeconds),
                tapNodeID: nodeID
            )
        }
        let script = LevelSolutionScript(
            levelID: level.id,
            description: "experimental_solver_candidate_taps_\(actions.count)",
            expectedOutcome: .completed,
            maxTaps: actions.count,
            requiresWithinTimeLimit: true,
            actions: actions
        )
        let result = try harness.run(level: level, script: script)
        if result.outcome == .completed {
            return Solution(actions: actions, result: result)
        }

        return nil
    }
}
