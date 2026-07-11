import Foundation
@testable import TinyRoutes

struct LevelSimulationLimits: Equatable {
    var maxStepCount: Int
    var maxSimulatedTimeSeconds: TimeInterval?
    var maxNoProgressStepCount: Int

    static let productionSolvability = LevelSimulationLimits(
        maxStepCount: 20_000,
        maxSimulatedTimeSeconds: nil,
        maxNoProgressStepCount: 120
    )

    static let fastTest = LevelSimulationLimits(
        maxStepCount: 500,
        maxSimulatedTimeSeconds: 10,
        maxNoProgressStepCount: 30
    )

    func sanitized() -> LevelSimulationLimits {
        LevelSimulationLimits(
            maxStepCount: max(maxStepCount, 1),
            maxSimulatedTimeSeconds: maxSimulatedTimeSeconds.flatMap { value in
                value.isFinite && value > 0 ? value : nil
            },
            maxNoProgressStepCount: max(maxNoProgressStepCount, 1)
        )
    }
}

struct LevelSimulationDiagnostics: Equatable {
    let levelID: String
    let elapsedTime: TimeInterval
    let timeRemaining: TimeInterval?
    let stepCount: Int
    let noProgressStepCount: Int
    let tapCount: Int
    let currentNodeID: String?
    let currentEdgeID: String?
    let progressAlongEdge: Double?
    let transitionNodeID: String?
    let transitionToEdgeID: String?
    let transitionProgress: Double?
    let didCollectPackage: Bool
    let outcome: LevelOutcome?
    let lastAction: ExecutedLevelSolutionAction?
    let phase: String
}

enum LevelSimulationHarnessError: Error, LocalizedError, Equatable {
    case exceededMaxStepCount(LevelSimulationDiagnostics)
    case exceededMaxSimulatedTime(LevelSimulationDiagnostics)
    case exceededNoProgressStepCount(LevelSimulationDiagnostics)
    case routeEngineExceededInternalSafetyLimit(LevelSimulationDiagnostics)
    case invalidActionTime(levelID: String, nodeID: String, timeSeconds: TimeInterval)
    case invalidActionNodeID(levelID: String, timeSeconds: TimeInterval)

    var errorDescription: String? {
        switch self {
        case let .exceededMaxStepCount(diagnostics):
            return "Level simulation exceeded max step count. \(diagnostics.engineerDescription)"
        case let .exceededMaxSimulatedTime(diagnostics):
            return "Level simulation exceeded max simulated time. \(diagnostics.engineerDescription)"
        case let .exceededNoProgressStepCount(diagnostics):
            return "Level simulation made no progress for too many consecutive steps. \(diagnostics.engineerDescription)"
        case let .routeEngineExceededInternalSafetyLimit(diagnostics):
            return "RouteEngine exceeded its internal update safety limit. \(diagnostics.engineerDescription)"
        case let .invalidActionTime(levelID, nodeID, timeSeconds):
            return "Invalid action time for level '\(levelID)' at node '\(nodeID)': \(timeSeconds). Action times must be finite and non-negative."
        case let .invalidActionNodeID(levelID, timeSeconds):
            return "Invalid action node ID for level '\(levelID)' at \(timeSeconds)s. Tap node IDs must be non-empty."
        }
    }
}

final class LevelSimulationHarness {
    private let engineFactory: () -> RouteEngine
    private let frameStep: TimeInterval
    private let limits: LevelSimulationLimits
    private let epsilon: TimeInterval = 0.000_000_1

    init(
        engineFactory: @escaping () -> RouteEngine = { RouteEngine() },
        frameStep: TimeInterval = 1.0 / 60.0,
        limits: LevelSimulationLimits = .productionSolvability
    ) {
        self.engineFactory = engineFactory
        self.frameStep = frameStep > 0 && frameStep.isFinite ? frameStep : 1.0 / 60.0
        self.limits = limits.sanitized()
    }

    func run(level: LevelData, script: LevelSolutionScript) throws -> LevelSolvabilityResult {
        let actions = try validateActions(levelID: level.id, script: script)
        let engine = engineFactory()
        try engine.buildGraph(from: level)
        _ = engine.startDotMovement()

        let effectiveMaxSimulatedTime = limits.maxSimulatedTimeSeconds
            ?? (TimeInterval(max(level.timeLimitSeconds, 0)) + frameStep + 1.0)
        var runState = SimulationRunState()
        var executedActions: [ExecutedLevelSolutionAction] = []

        for action in actions {
            try advance(
                engine: engine,
                levelID: level.id,
                runState: &runState,
                effectiveMaxSimulatedTime: effectiveMaxSimulatedTime,
                targetElapsedTime: action.timeSeconds,
                phase: "advancing_to_action",
                lastAction: runState.lastAction,
                until: {
                    guard engine.levelOutcome == nil else {
                        return true
                    }
                    return (engine.elapsedTime ?? 0) >= action.timeSeconds - epsilon
                }
            )
            guard engine.levelOutcome == nil else {
                break
            }

            let didRotate = engine.rotateSwitchNode(nodeID: action.tapNodeID).didRotate
            let executedAction = ExecutedLevelSolutionAction(
                requestedTime: action.timeSeconds,
                nodeID: action.tapNodeID,
                didRotate: didRotate,
                actualTapCountAfterAction: engine.tapCount
            )
            executedActions.append(executedAction)
            runState.lastAction = executedAction
        }

        try advance(
            engine: engine,
            levelID: level.id,
            runState: &runState,
            effectiveMaxSimulatedTime: effectiveMaxSimulatedTime,
            targetElapsedTime: nil,
            phase: "draining_after_final_action",
            lastAction: runState.lastAction,
            until: {
                engine.levelOutcome != nil
            }
        )

        return LevelSolvabilityResult(
            levelID: level.id,
            outcome: engine.levelOutcome,
            elapsedTime: engine.elapsedTime ?? 0,
            timeRemaining: engine.timeRemaining,
            tapCount: engine.tapCount,
            finalNodeID: engine.deliveryDot?.currentNodeID,
            currentEdgeID: engine.deliveryDot?.currentEdgeID,
            progressAlongEdge: engine.deliveryDot?.progressAlongEdge,
            didCollectPackage: engine.deliveryDot?.hasCollectedPackage ?? false,
            executedActions: executedActions,
            stepCount: runState.stepCount,
            noProgressStepCount: runState.noProgressStepCount
        )
    }

    private func validateActions(levelID: String, script: LevelSolutionScript) throws -> [LevelSolutionAction] {
        for action in script.actions {
            guard action.timeSeconds.isFinite,
                  action.timeSeconds >= 0 else {
                throw LevelSimulationHarnessError.invalidActionTime(
                    levelID: levelID,
                    nodeID: action.tapNodeID,
                    timeSeconds: action.timeSeconds
                )
            }
            guard !action.tapNodeID.isEmpty else {
                throw LevelSimulationHarnessError.invalidActionNodeID(
                    levelID: levelID,
                    timeSeconds: action.timeSeconds
                )
            }
        }

        return script.actions.sorted { $0.timeSeconds < $1.timeSeconds }
    }

    private func advance(
        engine: RouteEngine,
        levelID: String,
        runState: inout SimulationRunState,
        effectiveMaxSimulatedTime: TimeInterval,
        targetElapsedTime: TimeInterval?,
        phase: String,
        lastAction: ExecutedLevelSolutionAction?,
        until shouldStop: () -> Bool
    ) throws {
        while !shouldStop() {
            guard engine.levelOutcome == nil else {
                return
            }

            let elapsedTime = engine.elapsedTime ?? 0
            if elapsedTime > effectiveMaxSimulatedTime + epsilon {
                throw LevelSimulationHarnessError.exceededMaxSimulatedTime(
                    diagnostics(
                        levelID: levelID,
                        engine: engine,
                        runState: runState,
                        phase: phase,
                        lastAction: lastAction
                    )
                )
            }

            guard runState.stepCount < limits.maxStepCount else {
                throw LevelSimulationHarnessError.exceededMaxStepCount(
                    diagnostics(
                        levelID: levelID,
                        engine: engine,
                        runState: runState,
                        phase: phase,
                        lastAction: lastAction
                    )
                )
            }

            var deltaTime = frameStep
            if let targetElapsedTime {
                let remainingToTarget = targetElapsedTime - elapsedTime
                guard remainingToTarget > epsilon else {
                    return
                }
                deltaTime = min(deltaTime, remainingToTarget)
            }

            if let timeRemaining = engine.timeRemaining,
               timeRemaining > 0 {
                deltaTime = min(deltaTime, timeRemaining)
            }

            let remainingAllowedTime = effectiveMaxSimulatedTime - elapsedTime
            guard remainingAllowedTime > epsilon else {
                throw LevelSimulationHarnessError.exceededMaxSimulatedTime(
                    diagnostics(
                        levelID: levelID,
                        engine: engine,
                        runState: runState,
                        phase: phase,
                        lastAction: lastAction
                    )
                )
            }
            deltaTime = min(deltaTime, remainingAllowedTime)

            guard deltaTime > 0,
                  deltaTime.isFinite else {
                throw LevelSimulationHarnessError.exceededNoProgressStepCount(
                    diagnostics(
                        levelID: levelID,
                        engine: engine,
                        runState: runState,
                        phase: phase,
                        lastAction: lastAction
                    )
                )
            }

            let before = EngineProgressSnapshot(engine: engine)
            engine.updateDot(deltaTime: deltaTime)
            runState.stepCount += 1
            let after = EngineProgressSnapshot(engine: engine)

            if engine.didHitUpdateSafetyStepLimit {
                throw LevelSimulationHarnessError.routeEngineExceededInternalSafetyLimit(
                    diagnostics(
                        levelID: levelID,
                        engine: engine,
                        runState: runState,
                        phase: phase,
                        lastAction: lastAction
                    )
                )
            }

            if before == after {
                runState.noProgressStepCount += 1
            } else {
                runState.noProgressStepCount = 0
            }

            if runState.noProgressStepCount > limits.maxNoProgressStepCount {
                throw LevelSimulationHarnessError.exceededNoProgressStepCount(
                    diagnostics(
                        levelID: levelID,
                        engine: engine,
                        runState: runState,
                        phase: phase,
                        lastAction: lastAction
                    )
                )
            }
        }
    }

    private func diagnostics(
        levelID: String,
        engine: RouteEngine,
        runState: SimulationRunState,
        phase: String,
        lastAction: ExecutedLevelSolutionAction?
    ) -> LevelSimulationDiagnostics {
        let dot = engine.deliveryDot
        return LevelSimulationDiagnostics(
            levelID: levelID,
            elapsedTime: engine.elapsedTime ?? 0,
            timeRemaining: engine.timeRemaining,
            stepCount: runState.stepCount,
            noProgressStepCount: runState.noProgressStepCount,
            tapCount: engine.tapCount,
            currentNodeID: dot?.currentNodeID,
            currentEdgeID: dot?.currentEdgeID,
            progressAlongEdge: dot?.progressAlongEdge,
            transitionNodeID: dot?.transition?.nodeID,
            transitionToEdgeID: dot?.transition?.toEdgeID,
            transitionProgress: dot?.transition?.progressAlongTransition,
            didCollectPackage: dot?.hasCollectedPackage ?? false,
            outcome: engine.levelOutcome,
            lastAction: lastAction,
            phase: phase
        )
    }
}

private struct SimulationRunState {
    var stepCount = 0
    var noProgressStepCount = 0
    var lastAction: ExecutedLevelSolutionAction?
}

private struct EngineProgressSnapshot: Equatable {
    let outcome: LevelOutcome?
    let elapsedTime: TimeInterval?
    let timeRemaining: TimeInterval?
    let currentNodeID: String?
    let currentEdgeID: String?
    let progressAlongEdge: Double?
    let transitionNodeID: String?
    let transitionToEdgeID: String?
    let transitionProgress: Double?
    let didCollectPackage: Bool
    let tapCount: Int

    init(engine: RouteEngine) {
        let dot = engine.deliveryDot
        outcome = engine.levelOutcome
        elapsedTime = engine.elapsedTime
        timeRemaining = engine.timeRemaining
        currentNodeID = dot?.currentNodeID
        currentEdgeID = dot?.currentEdgeID
        progressAlongEdge = dot?.progressAlongEdge
        transitionNodeID = dot?.transition?.nodeID
        transitionToEdgeID = dot?.transition?.toEdgeID
        transitionProgress = dot?.transition?.progressAlongTransition
        didCollectPackage = dot?.hasCollectedPackage ?? false
        tapCount = engine.tapCount
    }
}

private extension LevelSimulationDiagnostics {
    var engineerDescription: String {
        [
            "levelID=\(levelID)",
            "phase=\(phase)",
            "elapsed=\(format(elapsedTime))s",
            "remaining=\(timeRemaining.map { "\(format($0))s" } ?? "nil")",
            "stepCount=\(stepCount)",
            "noProgressStepCount=\(noProgressStepCount)",
            "tapCount=\(tapCount)",
            "node=\(currentNodeID ?? "nil")",
            "edge=\(currentEdgeID ?? "nil")",
            "progress=\(progressAlongEdge.map(format) ?? "nil")",
            "transitionNode=\(transitionNodeID ?? "nil")",
            "transitionEdge=\(transitionToEdgeID ?? "nil")",
            "transitionProgress=\(transitionProgress.map(format) ?? "nil")",
            "didCollectPackage=\(didCollectPackage)",
            "outcome=\(String(describing: outcome))",
            "lastAction=\(lastAction.map(describeAction) ?? "nil")"
        ].joined(separator: ", ")
    }

    private func describeAction(_ action: ExecutedLevelSolutionAction) -> String {
        "time=\(format(action.requestedTime))s node=\(action.nodeID) didRotate=\(action.didRotate) tapCount=\(action.actualTapCountAfterAction)"
    }

    private func format(_ value: TimeInterval) -> String {
        String(format: "%.4f", value)
    }
}
