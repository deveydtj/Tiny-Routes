import Foundation

/// What a level must satisfy before an engine will run it, and the stricter
/// policy authored boards are held to.
enum MultiVanLevelRules {
    /// Structural checks: without these the engine could not keep its promises.
    static func check(_ level: MultiVanLevel, graph: RuntimeRouteGraph) throws {
        var vanIDs = Set<String>()
        for van in level.vans where !vanIDs.insert(van.id).inserted {
            throw MultiVanLevelError.duplicateVan(van.id)
        }
        // Road rules carried by the shared graph model are not Multi-Van rules.
        for edge in level.graph.edges where edge.availability != .always || edge.availabilityRule != nil {
            throw MultiVanLevelError.unsupportedEdgeRule(edgeID: edge.id)
        }

        var packageIDs = Set<String>()
        for package in level.packages {
            guard !package.id.isEmpty else { throw MultiVanLevelError.emptyPackageID }
            guard packageIDs.insert(package.id).inserted else {
                throw MultiVanLevelError.duplicatePackage(package.id)
            }
            guard vanIDs.contains(package.ownerVanID) else {
                throw MultiVanLevelError.packageOwnerMissing(packageID: package.id, vanID: package.ownerVanID)
            }
            guard graph.nodesByID[package.nodeID] != nil else {
                throw MultiVanLevelError.packageNodeMissing(packageID: package.id, nodeID: package.nodeID)
            }
        }
        for van in level.vans {
            let count = level.packages(ownedBy: van.id).count
            if count > MultiVanCargoRules.maxPackagesPerVan {
                throw MultiVanLevelError.tooManyPackages(vanID: van.id, count: count)
            }
        }

        let iceEdgeIDs = Set(level.roadZones.filter { $0.kind == .ice }.flatMap(\.edgeIDs))
        var zoneIDs = Set<String>()
        for zone in level.roadZones {
            guard !zone.id.isEmpty, zoneIDs.insert(zone.id).inserted else {
                throw MultiVanLevelError.invalidRoadZone(zoneID: zone.id, reason: "its ID is empty or used twice")
            }
            guard !zone.edgeIDs.isEmpty else {
                throw MultiVanLevelError.invalidRoadZone(zoneID: zone.id, reason: "it covers no roads")
            }
            for edgeID in zone.edgeIDs where graph.edgesByID[edgeID] == nil {
                throw MultiVanLevelError.invalidRoadZone(zoneID: zone.id, reason: "road \(edgeID) does not exist")
            }
        }

        var signalIDs = Set<String>()
        var approachEdgeIDs = Set<String>()
        for signal in level.signals {
            func refuse(_ reason: String) -> MultiVanLevelError { .invalidSignal(signalID: signal.id, reason: reason) }
            guard !signal.id.isEmpty, signalIDs.insert(signal.id).inserted else {
                throw refuse("its ID is empty or used twice")
            }
            guard !signal.approaches.isEmpty else { throw refuse("it has no approaches") }
            guard !signal.phases.isEmpty, signal.phases.allSatisfy({ $0.ticks > 0 }) else {
                throw refuse("every phase needs a positive length in ticks")
            }
            guard signal.area.radius.isFinite, signal.area.radius > 0,
                  signal.area.x.isFinite, signal.area.y.isFinite else {
                throw refuse("its area needs a centre and a positive radius")
            }
            let groups = Set(signal.approaches.map(\.group))
            for phase in signal.phases {
                if let group = phase.group, !groups.contains(group) {
                    throw refuse("a phase opens group \(group), which no approach belongs to")
                }
            }
            for group in groups where !signal.phases.contains(where: { $0.group == group }) {
                throw refuse("group \(group) is never let in")
            }
            for approach in signal.approaches {
                guard approachEdgeIDs.insert(approach.edgeID).inserted else {
                    throw refuse("road \(approach.edgeID) already has a stop line")
                }
                guard let road = graph.edgesByID[approach.edgeID]?.roadPath else {
                    throw refuse("road \(approach.edgeID) does not exist")
                }
                guard approach.stopDistance.isFinite, approach.stopDistance > 0,
                      approach.stopDistance < road.totalLength else {
                    throw refuse("the stop line on \(approach.edgeID) must sit along the road")
                }
                // A van cannot stop on ice.
                guard !iceEdgeIDs.contains(approach.edgeID) else {
                    throw refuse("road \(approach.edgeID) is icy and cannot hold a stop line")
                }
                // Past its line a van must enter the area, or it would never clear it.
                let entersArea = stride(from: approach.stopDistance, through: road.totalLength, by: 0.05)
                    .map { road.point(atDistance: $0) }
                    .contains { hypot($0.x - signal.area.x, $0.y - signal.area.y) <= signal.area.radius }
                guard entersArea else {
                    throw refuse("road \(approach.edgeID) never enters the signal's area after its stop line")
                }
            }
        }
    }

    /// Authoring policy for shipped boards, as messages naming the level and the
    /// piece. Stricter than `check`: a board can run and still be badly laid out.
    static func authoringIssues(in level: MultiVanLevel) -> [String] {
        var issues: [String] = []
        func reject(_ message: String) { issues.append("\(level.id): \(message)") }
        let graph: RuntimeRouteGraph
        do {
            graph = try RuntimeRouteGraph.make(from: level.graph) { $0.availabilityRule }
            try check(level, graph: graph)
        } catch {
            reject(error.localizedDescription)
            return issues
        }

        let houseNodeIDs = Set(level.houses.map(\.nodeID))
        let startNodeIDs = Set(level.vans.map(\.startNodeID))
        var pickupNodeIDs = Set<String>()
        for package in level.packages {
            guard let node = graph.nodesByID[package.nodeID] else { continue }
            if !pickupNodeIDs.insert(package.nodeID).inserted {
                reject("package \(package.id) shares node \(package.nodeID) with another pickup")
            }
            if houseNodeIDs.contains(package.nodeID) { reject("package \(package.id) sits on a house") }
            if startNodeIDs.contains(package.nodeID) { reject("package \(package.id) sits on a van's start") }
            if node.outgoingEdgeIDs.count > 1 { reject("package \(package.id) sits on a switch") }
        }
        // Each van must be able to drive start → every pickup → its house, never
        // through a house on the way. Switch settings are not fixed here: this
        // only proves the roads exist, not that one plan works for every van.
        for van in level.vans {
            let owned = level.packages(ownedBy: van.id)
            guard !owned.isEmpty,
                  let house = level.houses.first(where: { $0.color == van.color }) else { continue }
            if !canTour(from: van.startNodeID, through: Set(owned.map(\.nodeID)), to: house.nodeID,
                        graph: graph, houseNodeIDs: houseNodeIDs) {
                reject("van \(van.id) cannot reach its pickups and then its house")
            }
        }

        if level.packages.isEmpty == false || !level.signals.isEmpty || !level.roadZones.isEmpty,
           level.hint?.trimmingCharacters(in: .whitespaces).isEmpty ?? true {
            reject("a board with pickups, signals or road zones needs a hint")
        }
        let switchNodeIDs = Set(MultiVanBoardRules.switchNodes(in: graph).map(\.id))
        for id in level.hintFocusNodeIDs where !switchNodeIDs.contains(id) {
            reject("hint focuses \(id), which is not a switch")
        }

        for signal in level.signals {
            for approach in signal.approaches {
                guard let edge = graph.edgesByID[approach.edgeID] else { continue }
                // A van held at the line must not sit on a switch's lock.
                for nodeID in [edge.fromNodeID, edge.toNodeID] where switchNodeIDs.contains(nodeID) {
                    guard let node = graph.nodesByID[nodeID] else { continue }
                    let line = edge.roadPath.point(atDistance: approach.stopDistance)
                    if hypot(line.x - node.x, line.y - node.y) <= MultiVanTuning.default.liveSwitchLockRadius {
                        reject("signal \(signal.id): the stop line on \(approach.edgeID) is too close to switch \(nodeID)")
                    }
                }
            }
        }
        for zone in level.roadZones where zone.kind == .ice {
            for edgeID in zone.edgeIDs {
                guard let edge = graph.edgesByID[edgeID] else { continue }
                if !level.liveSwitchNodeIDs.contains(edge.toNodeID) {
                    reject("icy road \(edgeID) does not lead to a live switch, so the ice changes nothing")
                }
            }
        }
        return issues
    }

    /// Whether some path leaves `start`, visits every node of `stops` and ends at
    /// `goal`, without entering any house before the end.
    private static func canTour(
        from start: String, through stops: Set<String>, to goal: String,
        graph: RuntimeRouteGraph, houseNodeIDs: Set<String>
    ) -> Bool {
        struct Visit: Hashable {
            let nodeID: String
            let collected: Set<String>
        }
        var frontier = [Visit(nodeID: start, collected: stops.intersection([start]))]
        var seen = Set(frontier)
        while let visit = frontier.popLast() {
            if visit.nodeID == goal {
                if visit.collected == stops { return true }
                continue
            }
            if houseNodeIDs.contains(visit.nodeID) { continue }
            for edgeID in graph.nodesByID[visit.nodeID]?.outgoingEdgeIDs ?? [] {
                guard let next = graph.edgesByID[edgeID]?.toNodeID else { continue }
                let collected = stops.contains(next) ? visit.collected.union([next]) : visit.collected
                let nextVisit = Visit(nodeID: next, collected: collected)
                if seen.insert(nextVisit).inserted { frontier.append(nextVisit) }
            }
        }
        return false
    }
}
