import Foundation
@testable import TinyRoutes

final class LevelValidator {
    func validate(level: LevelData) -> [LevelValidationIssue] {
        _ = validateIdentity(level: level)
        _ = validateGraph(level: level)
        _ = validateIntent(level: level)
        _ = validatePlayability(level: level)
        return []
    }

    // MARK: - Identity Validation

    private func validateIdentity(level: LevelData) -> [LevelValidationIssue] {
        _ = level
        return []
    }

    // MARK: - Graph Validation

    private func validateGraph(level: LevelData) -> [LevelValidationIssue] {
        _ = level
        return []
    }

    // MARK: - Intent Validation

    private func validateIntent(level: LevelData) -> [LevelValidationIssue] {
        _ = level
        return []
    }

    // MARK: - Playability Validation

    private func validatePlayability(level: LevelData) -> [LevelValidationIssue] {
        _ = level
        return []
    }
}
