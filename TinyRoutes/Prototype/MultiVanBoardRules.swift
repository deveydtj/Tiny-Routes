import SwiftUI

/// Board facts every board draws from. Pure functions of the engine's graph and vans,
/// so the flat board and the diorama always agree on what is on the board.
enum MultiVanBoardRules {
    static func switchNodes(in graph: RuntimeRouteGraph) -> [RuntimeRouteNode] {
        graph.nodesByID.values.filter { (2...4).contains($0.outgoingEdgeIDs.count) }
            .sorted { $0.id < $1.id }
    }

    static func isDelivered(
        _ house: MultiVanHouse, vans: [MultiVanVanState], graph: RuntimeRouteGraph
    ) -> Bool {
        guard let node = graph.nodesByID[house.nodeID] else { return false }
        // Wrong-house arrivals are also parked; both colour and destination must match.
        return vans.contains { van in
            guard van.status == .parked, van.color == house.color else { return false }
            if let edgeID = van.currentEdgeID {
                return graph.edgesByID[edgeID]?.toNodeID == house.nodeID
            }
            // Also support a van authored directly on its house with no incoming edge.
            return van.position == RoadPoint(x: node.x, y: node.y)
        }
    }

    static func barrierNodes(in graph: RuntimeRouteGraph, houses: [MultiVanHouse]) -> [RuntimeRouteNode] {
        let houseNodeIDs = Set(houses.map(\.nodeID))
        return graph.nodesByID.values
            .filter { $0.outgoingEdgeIDs.isEmpty && !houseNodeIDs.contains($0.id) }
            .sorted { $0.id < $1.id }
    }

    static func barrierHeading(at node: RuntimeRouteNode, in graph: RuntimeRouteGraph) -> Angle {
        MultiVanVanView.heading(for: arrivalTangent(at: node.id, in: graph) ?? RoadVector(x: 0, y: 1))
    }

    /// Direction of travel on arriving at a node, in grid space. Nil when no road arrives.
    static func arrivalTangent(at nodeID: String, in graph: RuntimeRouteGraph) -> RoadVector? {
        // Stable choice if an authored house or dead end has several incoming roads.
        guard let road = graph.edgesByID.values.filter({ $0.toNodeID == nodeID })
            .min(by: { $0.id < $1.id })?.roadPath else { return nil }
        return road.tangent(atDistance: road.totalLength)
    }

    /// Direction a van faces, in grid space: along its road, or along its start's
    /// first exit before it leaves. Zero when neither exists.
    static func vanTangent(for van: MultiVanVanState, startNodeID: String?, in graph: RuntimeRouteGraph) -> RoadVector {
        if let edgeID = van.currentEdgeID, let edge = graph.edgesByID[edgeID] {
            // Parked/crashed vans retain this edge and their last travel distance.
            return edge.roadPath.tangent(atDistance: van.distanceAlongEdge)
        }
        return startNodeID.flatMap { departureTangent(from: $0, in: graph) } ?? RoadVector(x: 0, y: 0)
    }

    /// Direction a waiting van faces at its start: along the node's first exit, as
    /// `MultiVanVanView.heading` draws it. Nil for a node with no exits.
    static func departureTangent(from nodeID: String, in graph: RuntimeRouteGraph) -> RoadVector? {
        guard let edgeID = graph.nodesByID[nodeID]?.outgoingEdgeIDs.first,
              let road = graph.edgesByID[edgeID]?.roadPath else { return nil }
        return road.tangent(atDistance: 0)
    }
}
