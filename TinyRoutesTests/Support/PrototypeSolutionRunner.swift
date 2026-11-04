import Foundation
@testable import TinyRoutes

enum PrototypeSolutionRunner {
    /// Every invocation starts from authored settings, using production defaults.
    /// Return the actual engine so tests can inspect deliveries and deterministic state.
    /// `onStep` sees the engine after each tap and each simulation step, as a board would.
    static func run(
        level: MultiVanLevel, script: PrototypeSolutionScript, onStep: (MultiVanEngine) -> Void = { _ in }
    ) throws -> MultiVanEngine {
        for (index, tap) in script.liveTaps.enumerated() {
            guard tap.atTime.isFinite, tap.atTime >= 0 else {
                throw PrototypeSolutionError("\(level.id): liveTaps[\(index)] node \(tap.nodeID), atTime \(tap.atTime): invalid timestamp")
            }
        }
        // Explicit tie-break preserves script order for simultaneous inputs.
        let liveTaps = script.liveTaps.enumerated().sorted {
            $0.element.atTime == $1.element.atTime ? $0.offset < $1.offset : $0.element.atTime < $1.element.atTime
        }
        var nextTap = 0
        let engine: MultiVanEngine
        do {
            engine = try MultiVanEngine(level: level, tuning: .default)
        } catch {
            throw PrototypeSolutionError("\(level.id): could not construct engine: \(error)")
        }
        for (index, nodeID) in script.planTaps.enumerated() {
            let result = engine.tapSwitch(nodeID: nodeID)
            guard result == .accepted else {
                throw PrototypeSolutionError("\(level.id): planTaps[\(index)] node \(nodeID) rejected: \(result)")
            }
            onStep(engine)
        }
        engine.go()
        onStep(engine)
        // Count steps rather than accumulating floating-point frame deltas.
        let stepDuration = engine.tuning.stepDuration
        let maxSteps = Int((120 / stepDuration).rounded(.down))
        for _ in 0..<maxSteps {
            if engine.outcome != nil { break }
            while nextTap < liveTaps.count, liveTaps[nextTap].element.atTime <= engine.runTime {
                let (index, tap) = liveTaps[nextTap]
                let result = engine.tapSwitch(nodeID: tap.nodeID)
                guard result == .accepted else {
                    throw PrototypeSolutionError(
                        "\(level.id): liveTaps[\(index)] node \(tap.nodeID), atTime \(tap.atTime), runTime \(engine.runTime) rejected: \(result)"
                    )
                }
                nextTap += 1
            }
            engine.advance(by: stepDuration)
            onStep(engine)
        }
        guard engine.outcome != nil else {
            throw PrototypeSolutionError("\(level.id): timed out after 120 seconds; \(diagnostics(engine))")
        }
        guard nextTap == liveTaps.count else {
            let (index, tap) = liveTaps[nextTap]
            throw PrototypeSolutionError(
                "\(level.id): liveTaps[\(index)] node \(tap.nodeID), atTime \(tap.atTime) not applied before outcome; \(diagnostics(engine))"
            )
        }
        return engine
    }

    @discardableResult
    static func verify(level: MultiVanLevel, script: PrototypeSolutionScript) throws -> MultiVanEngine {
        let engine = try run(level: level, script: script)
        guard engine.outcome == .win else {
            throw PrototypeSolutionError("\(level.id): expected .win; \(diagnostics(engine))")
        }
        guard engine.changeCount == level.parChanges else {
            throw PrototypeSolutionError(
                "\(level.id): expected changeCount == parChanges (\(level.parChanges)); \(diagnostics(engine))"
            )
        }
        return engine
    }

    private static func diagnostics(_ engine: MultiVanEngine) -> String {
        let vans = engine.vans.map {
            "\($0.id)=\($0.status), edge=\($0.currentEdgeID ?? "none"), position=\($0.position)"
        }.joined(separator: "; ")
        return "outcome=\(String(describing: engine.outcome)), runTime=\(engine.runTime), "
            + "changeCount=\(engine.changeCount), parChanges=\(engine.level.parChanges); vans: [\(vans)]"
    }
}
