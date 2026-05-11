import Foundation

/// Represents a route-map intersection with a stable position and outgoing links.
struct RouteNode: Identifiable, Codable {
    let id: String
    var x: Double
    var y: Double
    var outgoingEdgeIDs: [String]
}

enum RouteNodeValidationError: Error, LocalizedError {
    case outgoingEdgesMismatch(nodeID: String, expectedEdgeIDs: [String], actualEdgeIDs: [String])

    var errorDescription: String? {
        switch self {
        case let .outgoingEdgesMismatch(nodeID, expectedEdgeIDs, actualEdgeIDs):
            return "RouteNode \(nodeID) has inconsistent outgoingEdgeIDs. Expected \(expectedEdgeIDs), got \(actualEdgeIDs)."
        }
    }
}

extension RouteNode {
    /// Validates that `outgoingEdgeIDs` matches the edges that actually originate from this node.
    /// Use in tests or debug-time checks to keep duplicated graph connectivity in sync.
    func validateOutgoingEdges(against edges: [RouteEdge]) throws {
        let expectedEdgeIDs = Set(
            edges
                .filter { $0.fromNodeID == id }
                .map(\.id)
        )
        let actualEdgeIDs = Set(outgoingEdgeIDs)

        guard expectedEdgeIDs == actualEdgeIDs else {
            throw RouteNodeValidationError.outgoingEdgesMismatch(
                nodeID: id,
                expectedEdgeIDs: Array(expectedEdgeIDs).sorted(),
                actualEdgeIDs: Array(actualEdgeIDs).sorted()
            )
        }
    }
}
