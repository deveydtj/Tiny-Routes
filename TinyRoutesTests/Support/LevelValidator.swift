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
        let nodeIDList = level.graph.nodes.map(\.id)
        let nodeIDs = Set(nodeIDList)

        let duplicateNodeIDs = duplicateIDs(in: nodeIDList)
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

        var requiredNodeIssues: [LevelValidationIssue] = []
        if !nodeIDs.contains(level.startNodeID) {
            requiredNodeIssues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "startNodeID '\(level.startNodeID)' does not exist in the graph"
            ))
        }
        if !nodeIDs.contains(level.packageNodeID) {
            requiredNodeIssues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "packageNodeID '\(level.packageNodeID)' does not exist in the graph"
            ))
        }
        if !nodeIDs.contains(level.destinationNodeID) {
            requiredNodeIssues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "destinationNodeID '\(level.destinationNodeID)' does not exist in the graph"
            ))
        }

        return duplicateNodeIssues + duplicateEdgeIssues + requiredNodeIssues
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
