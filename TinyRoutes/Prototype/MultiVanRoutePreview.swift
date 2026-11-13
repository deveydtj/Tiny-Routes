import Foundation

enum MultiVanPreviewEnding: Equatable {
    case matchingHouse
    case wrongHouse
    case deadEnd
    case loopLimit
    /// Reaches its own house, but without a parcel it needs.
    case missingPackage
    /// The van has parked, crashed or got stuck, so there is no route left to draw.
    case offRoad
}

struct MultiVanPreviewRoute: Equatable {
    let edgeIDs: [String]
    let ending: MultiVanPreviewEnding
    /// Parcels this route collects, in the order it reaches them. Imagined: a
    /// traced pickup never takes a parcel off the board.
    let collectedPackageIDs: [String]
    /// Parcels the van would still lack at the end of the route.
    let missingPackageIDs: [String]
    /// Signals the route stops at, in order. The wait is automatic; how long it
    /// lasts is not predicted.
    let signalIDs: [String]

    init(
        edgeIDs: [String], ending: MultiVanPreviewEnding,
        collectedPackageIDs: [String] = [], missingPackageIDs: [String] = [], signalIDs: [String] = []
    ) {
        self.edgeIDs = edgeIDs
        self.ending = ending
        self.collectedPackageIDs = collectedPackageIDs
        self.missingPackageIDs = missingPackageIDs
        self.signalIDs = signalIDs
    }

    /// The route delivers: right house, every parcel aboard. Not a promise that
    /// traffic is safe, or that a live change still to come will be made.
    var isComplete: Bool { ending == .matchingHouse }
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
    /// `packages` are the van's own parcels and `collected` those it already
    /// holds; the trace collects into its own copy and changes nothing else.
    static func trace(
        from nodeID: String,
        color: VanColor,
        after edgeIDs: [String] = [],
        graph: RuntimeRouteGraph,
        houses: [MultiVanHouse],
        packages: [MultiVanPackage] = [],
        collected: Set<String> = [],
        signals: [MultiVanSignal] = [],
        edgeLimit: Int = MultiVanTuning.default.previewEdgeLimit
    ) -> MultiVanPreviewRoute {
        var nodeID = nodeID
        var edgeIDs = edgeIDs
        var collected = collected
        var collectedInOrder: [String] = []
        var signalIDs: [String] = []
        func noteSignal(on edgeID: String) {
            guard let signal = signals.first(where: { $0.approaches.contains { $0.edgeID == edgeID } }),
                  !signalIDs.contains(signal.id) else { return }
            signalIDs.append(signal.id)
        }
        edgeIDs.forEach(noteSignal)
        func route(_ ending: MultiVanPreviewEnding) -> MultiVanPreviewRoute {
            MultiVanPreviewRoute(
                edgeIDs: edgeIDs, ending: ending, collectedPackageIDs: collectedInOrder,
                missingPackageIDs: packages.filter { !collected.contains($0.id) }.map(\.id),
                signalIDs: signalIDs
            )
        }

        while true {
            for package in MultiVanCargoRules.pickups(at: nodeID, owned: packages, collected: collected) {
                collected.insert(package.id)
                collectedInOrder.append(package.id)
            }
            if let house = houses.first(where: { $0.nodeID == nodeID }) {
                guard house.color == color else { return route(.wrongHouse) }
                let isLoaded = MultiVanCargoRules.firstMissing(owned: packages, collected: collected) == nil
                return route(isLoaded ? .matchingHouse : .missingPackage)
            }
            guard let node = graph.nodesByID[nodeID] else { return route(.deadEnd) }
            guard
                  let edgeID = node.activeOutgoingEdgeID,
                  node.outgoingEdgeIDs.contains(edgeID),
                  let edge = graph.edgesByID[edgeID],
                  edge.fromNodeID == nodeID else {
                return route(.deadEnd)
            }
            guard edgeIDs.count < max(0, edgeLimit) else { return route(.loopLimit) }
            edgeIDs.append(edgeID)
            noteSignal(on: edgeID)
            nodeID = edge.toNodeID
        }
    }

    /// One van's route and what it still has to do, in words: for the status
    /// summary, the failure card and VoiceOver.
    static func summary(for van: MultiVanVan, route: MultiVanPreviewRoute, level: MultiVanLevel) -> String {
        let name = "\(van.color.displayName) van"
        let pickups = route.collectedPackageIDs.count
        let collects = pickups == 0 ? "" : pickups == 1 ? "collects its parcel, then " : "collects \(pickups) parcels, then "
        let waits = route.signalIDs.isEmpty ? "" : " It waits at a signal on the way."
        switch route.ending {
        case .matchingHouse:
            return "\(name) \(collects)reaches its house.\(waits)"
        case .missingPackage:
            let count = route.missingPackageIDs.count
            return "\(name) reaches its house without \(count == 1 ? "its parcel" : "\(count) parcels"). Route it past the pickup first."
        case .wrongHouse:
            return "\(name) \(collects)ends at the wrong house."
        case .deadEnd:
            return "\(name) \(collects)ends at a dead end."
        case .loopLimit:
            return "\(name) \(collects)keeps circling: this route is not finished."
        case .offRoad:
            return "\(name) has no route left."
        }
    }
}
