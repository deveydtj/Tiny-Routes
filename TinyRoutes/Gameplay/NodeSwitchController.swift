import Foundation

/// Handles player taps that rotate switch-node outgoing direction.
final class NodeSwitchController {
    /// Rotates the active outgoing edge for the specified node when it is a switch node.
    ///
    /// A node is treated as a switch only when it has more than one valid outgoing edge.
    /// - Parameters:
    ///   - nodeID: The tapped node id.
    ///   - runtimeGraph: The mutable runtime graph containing node/edge state.
    /// - Returns: `true` when rotation occurred; otherwise `false`.
    @discardableResult
    func rotateSwitch(nodeID: String, in runtimeGraph: inout RuntimeRouteGraph) -> Bool {
        guard var node = runtimeGraph.nodesByID[nodeID] else {
            return false
        }

        let validOutgoingEdgeIDs = runtimeGraph.validOutgoingEdgeIDs(for: node)

        guard validOutgoingEdgeIDs.count > 1 else {
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
}
