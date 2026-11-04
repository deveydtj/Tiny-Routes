import Foundation

enum MultiVanPreviewEnding: Equatable {
    case matchingHouse
    case wrongHouse
    case deadEnd
    case loopLimit
    /// The van has parked, crashed or got stuck, so there is no route left to draw.
    case offRoad
}

struct MultiVanPreviewRoute: Equatable {
    let edgeIDs: [String]
    let ending: MultiVanPreviewEnding
}

/// Which ✓ / ✗ a preview route ends with, and where it sits when routes end together.
/// Boards turn `column` and `row` into their own offsets around the end of the line.
struct MultiVanPreviewMarker: Equatable {
    /// Where the line stops: the last road's end, or the van's start if it has no road.
    let nodeID: String
    let ending: MultiVanPreviewEnding
    /// Order among the routes ending at `nodeID`; nil when this route ends there alone.
    let stackSlot: Int?

    var glyph: String { ending == .matchingHouse ? "✓" : "✗" }
    /// Shared ends stack in two columns, -1 left and 1 right; nil keeps the marker unpaired.
    var column: Int? { stackSlot.map { $0.isMultiple(of: 2) ? -1 : 1 } }
    var row: Int { (stackSlot ?? 0) / 2 }

    /// One entry per route in authored van order; nil for a van with no line left to mark.
    static func make(
        routes: [MultiVanPreviewRoute], vans: [MultiVanVan], graph: RuntimeRouteGraph
    ) -> [Self?] {
        let terminalIDs = zip(vans, routes).map { van, route in
            route.edgeIDs.last.flatMap { graph.edgesByID[$0]?.toNodeID } ?? van.startNodeID
        }
        return terminalIDs.indices.map { index in
            guard routes[index].ending != .offRoad else { return nil }
            // Vans with no line left don't share an endpoint glyph stack.
            let peers = terminalIDs.indices.filter {
                terminalIDs[$0] == terminalIDs[index] && routes[$0].ending != .offRoad
            }
            return Self(nodeID: terminalIDs[index], ending: routes[index].ending,
                        stackSlot: peers.count > 1 ? peers.firstIndex(of: index) : nil)
        }
    }
}

/// Side-by-side lanes for routes that share a road, so every line stays visible.
enum MultiVanPreviewLanes {
    /// Per route, its lane on each road it uses: 0 alone, else spread evenly about 0
    /// (−0.5 and 0.5 for two) in authored van order. Positive lanes sit to the right
    /// of the direction of travel. Boards scale lanes to their own widths.
    static func make(routes: [MultiVanPreviewRoute]) -> [[String: Double]] {
        var users: [String: [Int]] = [:]
        for (index, route) in routes.enumerated() {
            // A looping route occupies one lane, however often it visits the edge.
            for edgeID in Set(route.edgeIDs) {
                users[edgeID, default: []].append(index)
            }
        }
        var lanes = Array(repeating: [String: Double](), count: routes.count)
        for (edgeID, indices) in users {
            // Indices were appended in authored van order, never dictionary order.
            for (lane, index) in indices.enumerated() {
                lanes[index][edgeID] = Double(lane) - Double(indices.count - 1) / 2
            }
        }
        return lanes
    }
}

enum MultiVanRoutePreview {
    static func trace(
        van: MultiVanVan,
        graph: RuntimeRouteGraph,
        houses: [MultiVanHouse],
        edgeLimit: Int = MultiVanTuning.default.previewEdgeLimit
    ) -> MultiVanPreviewRoute {
        trace(from: van.startNodeID, color: van.color, graph: graph, houses: houses, edgeLimit: edgeLimit)
    }

    /// Traces from `nodeID`; `edgeIDs` seeds the route with roads already committed to.
    static func trace(
        from nodeID: String,
        color: VanColor,
        after edgeIDs: [String] = [],
        graph: RuntimeRouteGraph,
        houses: [MultiVanHouse],
        edgeLimit: Int = MultiVanTuning.default.previewEdgeLimit
    ) -> MultiVanPreviewRoute {
        var nodeID = nodeID
        var edgeIDs = edgeIDs

        while true {
            if let house = houses.first(where: { $0.nodeID == nodeID }) {
                return MultiVanPreviewRoute(
                    edgeIDs: edgeIDs,
                    ending: house.color == color ? .matchingHouse : .wrongHouse
                )
            }
            guard let node = graph.nodesByID[nodeID] else {
                return MultiVanPreviewRoute(edgeIDs: edgeIDs, ending: .deadEnd)
            }
            guard
                  let edgeID = node.activeOutgoingEdgeID,
                  node.outgoingEdgeIDs.contains(edgeID),
                  let edge = graph.edgesByID[edgeID],
                  edge.fromNodeID == nodeID else {
                return MultiVanPreviewRoute(edgeIDs: edgeIDs, ending: .deadEnd)
            }
            guard edgeIDs.count < max(0, edgeLimit) else {
                return MultiVanPreviewRoute(edgeIDs: edgeIDs, ending: .loopLimit)
            }
            edgeIDs.append(edgeID)
            nodeID = edge.toNodeID
        }
    }
}
