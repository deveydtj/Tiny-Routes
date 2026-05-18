import Foundation
@testable import TinyRoutes

enum LevelHumanPlayabilityRules {
    static let minimumTapSpacingSeconds: TimeInterval = 0.30
    static let minimumCompletionBufferSeconds: TimeInterval = 0.50

    static func tapSpacingViolations(for script: LevelSolutionScript) -> [String] {
        let indexedActions = script.actions.enumerated().sorted { $0.element.timeSeconds < $1.element.timeSeconds }

        return zip(indexedActions, indexedActions.dropFirst()).compactMap { pair in
            let (previous, current) = pair
            let previousIndex = previous.offset
            let currentIndex = current.offset
            let previousAction = previous.element
            let currentAction = current.element
            let spacing = currentAction.timeSeconds - previousAction.timeSeconds
            guard spacing < minimumTapSpacingSeconds else {
                return nil
            }

            return "\(script.levelID): action[\(previousIndex)] at \(formatted(previousAction.timeSeconds))s and action[\(currentIndex)] at \(formatted(currentAction.timeSeconds))s are only \(formatted(spacing))s apart (minimum \(formatted(minimumTapSpacingSeconds))s)"
        }
    }

    static func completionBufferViolation(level: LevelData, result: LevelSolvabilityResult) -> String? {
        guard result.outcome == .completed else {
            return nil
        }

        let timeRemaining = result.timeRemaining ?? max(TimeInterval(level.timeLimitSeconds) - result.elapsedTime, 0)
        guard timeRemaining < minimumCompletionBufferSeconds else {
            return nil
        }

        return "\(level.id): completed with only \(formatted(timeRemaining))s remaining before the \(level.timeLimitSeconds)s time limit (minimum buffer \(formatted(minimumCompletionBufferSeconds))s)"
    }

    private static func formatted(_ value: TimeInterval) -> String {
        String(format: "%.2f", value)
    }
}
