import Foundation

/// Handles player taps that rotate switch-node outgoing direction.
final class NodeSwitchController {
    /// Rotates the active outgoing edge for the specified node when it is a switch node.
    ///
    /// A node is treated as a switch only when it has more than one outgoing edge
    /// usable in the current package state. For nodes with zero or one usable edge,
    /// this method normalizes `activeOutgoingEdgeID` to the sole usable edge (or `nil`)
    /// and returns `false`.
    /// - Parameters:
    ///   - nodeID: The tapped node id.
    ///   - runtimeGraph: The mutable runtime graph containing node/edge state.
    ///   - hasCollectedPackage: The package state used to filter conditional roads.
    /// - Returns: `true` when rotation occurred; `false` otherwise, including normalization-only updates.
    @discardableResult
    func rotateSwitch(
        nodeID: String,
        in runtimeGraph: inout RuntimeRouteGraph,
        hasCollectedPackage: Bool = false
    ) -> Bool {
        guard var node = runtimeGraph.nodesByID[nodeID] else {
            return false
        }

        let validOutgoingEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
            for: node,
            hasCollectedPackage: hasCollectedPackage
        )
        let switchKind = runtimeGraph.switchKind(
            for: node,
            hasCollectedPackage: hasCollectedPackage
        )

        guard switchKind.isSwitchable else {
            let normalizedActiveEdgeID = validOutgoingEdgeIDs.first
            if node.activeOutgoingEdgeID != normalizedActiveEdgeID {
                node.activeOutgoingEdgeID = normalizedActiveEdgeID
                runtimeGraph.nodesByID[nodeID] = node
            }
            return false
        }

        let nextIndex: Int
        if let currentActiveEdgeID = node.activeOutgoingEdgeID,
           let currentIndex = validOutgoingEdgeIDs.firstIndex(of: currentActiveEdgeID) {
            nextIndex = (currentIndex + 1) % validOutgoingEdgeIDs.count
        } else {
            nextIndex = 0
        }

        node.activeOutgoingEdgeID = validOutgoingEdgeIDs[nextIndex]
        runtimeGraph.nodesByID[nodeID] = node
        return true
    }

    @discardableResult
    func rotateSwitch(
        nodeID: String,
        in runtimeGraph: inout RuntimeRouteGraph,
        completedObjectiveIDs: Set<String>,
        activeObjectiveIndex: Int?
    ) -> Bool {
        guard var node = runtimeGraph.nodesByID[nodeID] else { return false }

        let usableEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
            for: node,
            completedObjectiveIDs: completedObjectiveIDs,
            activeObjectiveIndex: activeObjectiveIndex
        )
        let switchKind = runtimeGraph.switchKind(
            for: node,
            completedObjectiveIDs: completedObjectiveIDs,
            activeObjectiveIndex: activeObjectiveIndex
        )

        guard switchKind.isSwitchable else {
            let normalizedActiveEdgeID = usableEdgeIDs.first
            if node.activeOutgoingEdgeID != normalizedActiveEdgeID {
                node.activeOutgoingEdgeID = normalizedActiveEdgeID
                runtimeGraph.nodesByID[nodeID] = node
            }
            return false
        }

        let nextIndex: Int
        if let currentActiveEdgeID = node.activeOutgoingEdgeID,
           let currentIndex = usableEdgeIDs.firstIndex(of: currentActiveEdgeID) {
            nextIndex = (currentIndex + 1) % usableEdgeIDs.count
        } else {
            nextIndex = 0
        }

        node.activeOutgoingEdgeID = usableEdgeIDs[nextIndex]
        runtimeGraph.nodesByID[nodeID] = node
        return true
    }
}
