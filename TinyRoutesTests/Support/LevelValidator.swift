import Foundation
@testable import TinyRoutes

final class LevelValidator {
    func validate(level: LevelData) -> [LevelValidationIssue] {
        var issues: [LevelValidationIssue] = []
        issues += validateIdentity(level: level)
        issues += validateRules(level: level)
        issues += level.validateObjectives().map {
            LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: $0.message
            )
        }
        issues += validateGraph(level: level)
        guard !hasDuplicateGraphIDs(level) else {
            return issues
        }
        issues += validateIntent(level: level)
        issues += validatePlayability(level: level)
        return issues
    }

    private func validateRules(level: LevelData) -> [LevelValidationIssue] {
        guard let rules = level.rules else {
            return []
        }

        var issues: [LevelValidationIssue] = []
        if !rules.switchLookaheadSeconds.isFinite || rules.switchLookaheadSeconds <= 0 {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "rules.switchLookaheadSeconds must be finite and greater than 0"
            ))
        }
        if !rules.switchTapCooldownSeconds.isFinite || rules.switchTapCooldownSeconds < 0 {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "rules.switchTapCooldownSeconds must be finite and greater than or equal to 0"
            ))
        }
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
        let switchOutgoingEdgeIssues = validateSwitchOutgoingEdgeCounts(level: level)

        return duplicateNodeIssues
            + duplicateEdgeIssues
            + requiredNodeIssues
            + edgeReferenceIssues
            + outgoingEdgeConsistencyIssues
            + switchOutgoingEdgeIssues
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

    private func validateSwitchOutgoingEdgeCounts(level: LevelData) -> [LevelValidationIssue] {
        var issues: [LevelValidationIssue] = []
        let edgesByID = Dictionary(grouping: level.graph.edges, by: \.id)
            .compactMapValues(\.first)

        for node in level.graph.nodes {
            let validOutgoingEdgeCount = node.outgoingEdgeIDs.filter { edgeID in
                guard let edge = edgesByID[edgeID] else {
                    return false
                }
                return edge.fromNodeID == node.id
            }.count

            if validOutgoingEdgeCount > SwitchNodeKind.maximumSupportedOutgoingEdgeCount {
                issues.append(LevelValidationIssue(
                    severity: .error,
                    levelID: level.id,
                    message: "Node '\(node.id)' has \(validOutgoingEdgeCount) valid outgoing edges; at most \(SwitchNodeKind.maximumSupportedOutgoingEdgeCount) are supported"
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

        let nodeByID = Dictionary(grouping: level.graph.nodes, by: \.id)
            .compactMapValues(\.first)
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
        let nodeIDs = Set(level.graph.nodes.map(\.id))
        guard nodeIDs.contains(level.startNodeID),
              nodeIDs.contains(level.packageNodeID),
              nodeIDs.contains(level.destinationNodeID) else {
            return []
        }

        var issues: [LevelValidationIssue] = []

        let reachableFromStart = reachableNodeIDs(from: level.startNodeID, edges: level.graph.edges)
        let packageReachableFromStart = reachableFromStart.contains(level.packageNodeID)
        if !packageReachableFromStart {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "packageNodeID '\(level.packageNodeID)' is unreachable from startNodeID '\(level.startNodeID)'"
            ))
        }

        let reachableFromPackage = reachableNodeIDs(from: level.packageNodeID, edges: level.graph.edges)
        let destinationReachableFromPackage = reachableFromPackage.contains(level.destinationNodeID)
        if !destinationReachableFromPackage {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "destinationNodeID '\(level.destinationNodeID)' is unreachable from packageNodeID '\(level.packageNodeID)'"
            ))
        }

        if !(packageReachableFromStart && destinationReachableFromPackage) {
            issues.append(LevelValidationIssue(
                severity: .error,
                levelID: level.id,
                message: "No directed path can satisfy start → package → destination"
            ))
        }

        return issues
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

    private func hasDuplicateGraphIDs(_ level: LevelData) -> Bool {
        !duplicateIDs(in: level.graph.nodes.map(\.id)).isEmpty
            || !duplicateIDs(in: level.graph.edges.map(\.id)).isEmpty
    }

    private func reachableNodeIDs(from startNodeID: String, edges: [RouteEdge]) -> Set<String> {
        let edgesBySourceNodeID = Dictionary(grouping: edges, by: \.fromNodeID)
        var visited: Set<String> = [startNodeID]
        var stack = [startNodeID]

        while let nodeID = stack.popLast() {
            let nextNodeIDs = edgesBySourceNodeID[nodeID]?.map(\.toNodeID) ?? []
            for nextNodeID in nextNodeIDs where visited.insert(nextNodeID).inserted {
                stack.append(nextNodeID)
            }
        }

        return visited
    }
}
