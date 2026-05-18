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
        var issues: [LevelValidationIssue] = []

        if level.id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "Level id must not be empty"
            ))
        }

        if level.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "Level name must not be empty"
            ))
        }

        if level.timeLimitSeconds <= 0 {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "timeLimitSeconds must be greater than 0"
            ))
        }

        if level.parTaps < 0 {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "parTaps must be greater than or equal to 0"
            ))
        }

        return issues
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

        let edgeReferenceIssues = validateEdgeReferences(level: level, nodeIDs: nodeIDs)
        let outgoingEdgeConsistencyIssues = validateOutgoingEdgeConsistency(level: level)

        return duplicateNodeIssues
            + duplicateEdgeIssues
            + requiredNodeIssues
            + edgeReferenceIssues
            + outgoingEdgeConsistencyIssues
    }

    private func validateEdgeReferences(level: LevelData, nodeIDs: Set<String>) -> [LevelValidationIssue] {
        var issues: [LevelValidationIssue] = []
        for edge in level.graph.edges {
            if !nodeIDs.contains(edge.fromNodeID) {
                issues.append(LevelValidationIssue(
                    severity: .error,
                    levelID: level.id,
                    message: "Edge '\(edge.id)' references unknown fromNodeID '\(edge.fromNodeID)'"
                ))
            }
            if !nodeIDs.contains(edge.toNodeID) {
                issues.append(LevelValidationIssue(
                    severity: .error,
                    levelID: level.id,
                    message: "Edge '\(edge.id)' references unknown toNodeID '\(edge.toNodeID)'"
                ))
            }
        }
        return issues
    }

    private func validateOutgoingEdgeConsistency(level: LevelData) -> [LevelValidationIssue] {
        var issues: [LevelValidationIssue] = []
        let edgeIDs = Set(level.graph.edges.map(\.id))

        for node in level.graph.nodes {
            let duplicateOutgoingEdgeIDs = duplicateIDs(in: node.outgoingEdgeIDs)
            issues += duplicateOutgoingEdgeIDs.map {
                LevelValidationIssue(
                    severity: .error,
                    levelID: level.id,
                    message: "Node '\(node.id)' has duplicate outgoingEdgeIDs: \($0)"
                )
            }

            for listedEdgeID in node.outgoingEdgeIDs {
                guard edgeIDs.contains(listedEdgeID) else {
                    issues.append(LevelValidationIssue(
                        severity: .error,
                        levelID: level.id,
                        message: "Node '\(node.id)' lists unknown outgoing edge ID '\(listedEdgeID)'"
                    ))
                    continue
                }

                if !level.graph.edges.contains(where: { $0.id == listedEdgeID && $0.fromNodeID == node.id }) {
                    let actualSourceNodeID = level.graph.edges.first(where: { $0.id == listedEdgeID })?.fromNodeID ?? "unknown"
                    issues.append(LevelValidationIssue(
                        severity: .error,
                        levelID: level.id,
                        message: "Node '\(node.id)' lists edge '\(listedEdgeID)' but that edge starts from '\(actualSourceNodeID)'"
                    ))
                }
            }
        }

        let nodeByID = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { ($0.id, $0) })
        for edge in level.graph.edges {
            guard let sourceNode = nodeByID[edge.fromNodeID] else {
                continue
            }
            if !sourceNode.outgoingEdgeIDs.contains(edge.id) {
                issues.append(LevelValidationIssue(
                    severity: .error,
                    levelID: level.id,
                    message: "Node '\(sourceNode.id)' is missing outgoing edge '\(edge.id)' in outgoingEdgeIDs"
                ))
            }
        }

        return issues
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
