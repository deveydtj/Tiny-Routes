import Foundation
@testable import TinyRoutes

enum LevelHumanPlayabilityRules {
    static let minimumTapSpacingSeconds: TimeInterval = 0.30
    static let minimumCompletionBufferSeconds: TimeInterval = 0.50

    static func tapSpacingViolations(for script: LevelSolutionScript) -> [String] {
        let actions = script.actions.sorted { $0.timeSeconds < $1.timeSeconds }

        return zip(actions, actions.dropFirst()).enumerated().compactMap { index, pair in
            let (previous, current) = pair
            let spacing = current.timeSeconds - previous.timeSeconds
            guard spacing < minimumTapSpacingSeconds else {
                return nil
            }

            return "\(script.levelID): action[\(index)] at \(formatted(previous.timeSeconds))s and action[\(index + 1)] at \(formatted(current.timeSeconds))s are only \(formatted(spacing))s apart (minimum \(formatted(minimumTapSpacingSeconds))s)"
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
