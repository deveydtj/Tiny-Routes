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
    case duplicateOutgoingEdgeIDs(nodeID: String, duplicateEdgeIDs: [String])
    case duplicateGraphEdgeIDs(nodeID: String, duplicateEdgeIDs: [String])

    var errorDescription: String? {
        switch self {
        case let .outgoingEdgesMismatch(nodeID, expectedEdgeIDs, actualEdgeIDs):
            return "RouteNode \(nodeID) has inconsistent outgoingEdgeIDs. Expected \(expectedEdgeIDs), got \(actualEdgeIDs)."
        case let .duplicateOutgoingEdgeIDs(nodeID, duplicateEdgeIDs):
            return "RouteNode \(nodeID) has duplicate outgoingEdgeIDs: \(duplicateEdgeIDs)."
        case let .duplicateGraphEdgeIDs(nodeID, duplicateEdgeIDs):
            return "RouteNode \(nodeID) has duplicate edge IDs in graph edges: \(duplicateEdgeIDs)."
        }
    }
}

extension RouteNode {
    /// Validates that `outgoingEdgeIDs` matches the edges that actually originate from this node.
    /// Use in tests or debug-time checks to keep duplicated graph connectivity in sync.
    func validateOutgoingEdges(against edges: [RouteEdge]) throws {
        let expectedEdgeIDList = edges
            .filter { $0.fromNodeID == id }
            .map(\.id)
        let expectedEdgeIDs = Set(expectedEdgeIDList)
        let actualEdgeIDs = Set(outgoingEdgeIDs)

        let duplicateExpectedEdgeIDs = duplicates(in: expectedEdgeIDList)
        guard duplicateExpectedEdgeIDs.isEmpty else {
            throw RouteNodeValidationError.duplicateGraphEdgeIDs(
                nodeID: id,
                duplicateEdgeIDs: duplicateExpectedEdgeIDs
            )
        }

        let duplicateOutgoingEdgeIDs = duplicates(in: outgoingEdgeIDs)
        guard duplicateOutgoingEdgeIDs.isEmpty else {
            throw RouteNodeValidationError.duplicateOutgoingEdgeIDs(
                nodeID: id,
                duplicateEdgeIDs: duplicateOutgoingEdgeIDs
            )
        }

        guard expectedEdgeIDs == actualEdgeIDs else {
            throw RouteNodeValidationError.outgoingEdgesMismatch(
                nodeID: id,
                expectedEdgeIDs: Array(expectedEdgeIDs).sorted(),
                actualEdgeIDs: Array(actualEdgeIDs).sorted()
            )
        }
    }

    private func duplicates(in values: [String]) -> [String] {
        var seen = Set<String>()
        var duplicates = Set<String>()

        for value in values where !seen.insert(value).inserted {
            duplicates.insert(value)
        }

        return Array(duplicates).sorted()
    }
}
