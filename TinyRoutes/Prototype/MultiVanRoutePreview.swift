import Foundation

enum MultiVanPreviewEnding: Equatable {
    case matchingHouse
    case wrongHouse
    case deadEnd
    case loopLimit
}

struct MultiVanPreviewRoute: Equatable {
    let edgeIDs: [String]
    let ending: MultiVanPreviewEnding
}

enum MultiVanRoutePreview {
    static func trace(
        van: MultiVanVan,
        graph: RuntimeRouteGraph,
        houses: [MultiVanHouse],
        edgeLimit: Int = MultiVanTuning.default.previewEdgeLimit
    ) -> MultiVanPreviewRoute {
        var nodeID = van.startNodeID
        var edgeIDs: [String] = []

        while true {
            if let house = houses.first(where: { $0.nodeID == nodeID }) {
                return MultiVanPreviewRoute(
                    edgeIDs: edgeIDs,
                    ending: house.color == van.color ? .matchingHouse : .wrongHouse
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
