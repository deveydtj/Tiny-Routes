import Foundation

/// A runtime snapshot of a route-map node, including the currently active outgoing edge for switch nodes.
struct RuntimeRouteNode {
    let id: String
    let x: Double
    let y: Double
    let outgoingEdgeIDs: [String]
    /// The edge ID the dot will follow when leaving this node.
    /// `nil` for leaf nodes (no outgoing edges); set to the first outgoing edge for all other nodes.
    var activeOutgoingEdgeID: String?
}

/// A runtime snapshot of a directed connection between two route-map nodes.
struct RuntimeRouteEdge {
    let id: String
    let fromNodeID: String
    let toNodeID: String
    let roadPath: RoadPath
}

/// The live, mutable graph used during a running level.
/// Nodes and edges are keyed by their IDs for O(1) lookup.
struct RuntimeRouteGraph {
    var nodesByID: [String: RuntimeRouteNode]
    let edgesByID: [String: RuntimeRouteEdge]

    func validOutgoingEdgeIDs(for node: RuntimeRouteNode) -> [String] {
        node.outgoingEdgeIDs.filter { edgeID in
            guard let edge = edgesByID[edgeID] else {
                return false
            }
            return edge.fromNodeID == node.id
        }
    }

    func switchKind(for node: RuntimeRouteNode) -> SwitchNodeKind {
        SwitchNodeKind(validOutgoingEdgeCount: validOutgoingEdgeIDs(for: node).count)
    }
}

enum SwitchNodeKind: Equatable {
    case terminal
    case passThrough
    case twoWaySwitch
    case threeWaySwitch
    case fourWayIntersectionSwitch
    case invalidTooManyOutgoingEdges(validOutgoingEdgeCount: Int)

    static let maximumSupportedOutgoingEdgeCount = 4

    init(validOutgoingEdgeCount: Int) {
        switch validOutgoingEdgeCount {
        case 0:
            self = .terminal
        case 1:
            self = .passThrough
        case 2:
            self = .twoWaySwitch
        case 3:
            self = .threeWaySwitch
        case 4:
            self = .fourWayIntersectionSwitch
        default:
            self = .invalidTooManyOutgoingEdges(validOutgoingEdgeCount: validOutgoingEdgeCount)
        }
    }

    var isSwitchable: Bool {
        switch self {
        case .twoWaySwitch, .threeWaySwitch, .fourWayIntersectionSwitch:
            return true
        case .terminal, .passThrough, .invalidTooManyOutgoingEdges:
            return false
        }
    }
}
