import Foundation
@testable import TinyRoutes

final class LevelValidator {
    func validate(level: LevelData) -> [LevelValidationIssue] {
        var issues: [LevelValidationIssue] = []
        issues += validateIdentity(level: level)
        issues += validateGraph(level: level)
        issues += validateIntent(level: level)
        issues += validatePlayability(level: level)
        return issues
    }

    // MARK: - Identity Validation

    private func validateIdentity(level: LevelData) -> [LevelValidationIssue] {
        _ = level
        return []
    }

    // MARK: - Graph Validation

    private func validateGraph(level: LevelData) -> [LevelValidationIssue] {
        let duplicateNodeIDs = duplicateIDs(in: level.graph.nodes.map(\.id))
        let duplicateEdgeIDs = duplicateIDs(in: level.graph.edges.map(\.id))

        let duplicateNodeIssues = duplicateNodeIDs.map {
            LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "Duplicate node ID: \($0)"
            )
        }
        let duplicateEdgeIssues = duplicateEdgeIDs.map {
            LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "Duplicate edge ID: \($0)"
            )
        }

        return duplicateNodeIssues + duplicateEdgeIssues
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

    private func duplicateIDs(in ids: [String]) -> [String] {
        Dictionary(grouping: ids, by: { $0 })
            .filter { $1.count > 1 }
            .map(\.key)
            .sorted()
    }
}
