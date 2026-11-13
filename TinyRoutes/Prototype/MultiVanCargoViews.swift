import SwiftUI

/// A kraft parcel tied in its owner's colour. The owner's shape is on the label,
/// so the parcel reads without colour, like the vans and houses.
struct MultiVanParcelView: View {
    let color: VanColor
    var side: CGFloat = 16
    var showsSymbol = true

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: side * 0.16)
                .fill(Color(hex: 0x9A6233))
                .offset(y: side * 0.07)
            RoundedRectangle(cornerRadius: side * 0.16)
                .fill(Color(hex: 0xC98A4B))
            // The ribbon carries the owner's colour.
            Rectangle().fill(color.boardColor).frame(width: side * 0.2)
            Rectangle().fill(color.boardColor).frame(height: side * 0.2)
            if showsSymbol {
                Circle()
                    .fill(TRVillagePalette.cream)
                    .overlay { Circle().strokeBorder(color.boardDeep, lineWidth: max(1, side * 0.06)) }
                    .overlay { VanSymbolShape(color: color).fill(color.boardInk).padding(side * 0.14) }
                    .frame(width: side * 0.62, height: side * 0.62)
            }
        }
        .frame(width: side, height: side)
        .clipShape(RoundedRectangle(cornerRadius: side * 0.16).offset(y: side * 0.035).scale(1.08))
    }
}

/// A parcel waiting on the board for its van. Collected, only its pad remains.
struct MultiVanPickupMarker: View {
    let pickup: MultiVanPickup
    var side: CGFloat = 26
    var reduceMotion = false
    @State private var isPulsing = false

    var body: some View {
        ZStack {
            // A cream pad lifts the marker off the asphalt.
            Circle()
                .fill(TRVillagePalette.cream)
                .overlay { Circle().strokeBorder(pickup.color.boardDeep.opacity(isWaiting ? 1 : 0.35), lineWidth: 1.5) }
                .shadow(color: TRVillagePalette.ink.opacity(0.2), radius: 2, y: 1.5)
            if pickup.isMissed {
                // The planned route skips this parcel: the same ring a tip uses.
                Circle()
                    .stroke(TRGameplayStyle.Colors.orangeAccent, style: StrokeStyle(lineWidth: 2.5, dash: [5, 4]))
                    .scaleEffect(reduceMotion || !isPulsing ? 1.22 : 1.38)
            }
            if isWaiting {
                MultiVanParcelView(color: pickup.color, side: side * 0.62)
            } else {
                Image(systemName: "checkmark")
                    .font(.system(size: side * 0.36, weight: .heavy))
                    .foregroundStyle(pickup.color.boardInk.opacity(0.55))
            }
        }
        .frame(width: side, height: side)
        .animation(reduceMotion ? nil : .spring(duration: 0.25), value: pickup.state)
        .onAppear { pulse(pickup.isMissed) }
        .onChange(of: pickup.isMissed) { _, missed in pulse(missed) }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(pickup.accessibilityLabel)
        .accessibilityValue(pickup.accessibilityValue)
    }

    private var isWaiting: Bool { pickup.state == .atPickup }

    private func pulse(_ enabled: Bool) {
        guard enabled, !reduceMotion else {
            isPulsing = false
            return
        }
        withAnimation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true)) { isPulsing = true }
    }
}

/// One parcel as every board draws it: where it waits, whose it is, and whether
/// the planned route skips it. Read from the engine; no board keeps its own copy.
struct MultiVanPickup: Equatable, Identifiable {
    let id: String
    let nodeID: String
    let ownerVanID: String
    let color: VanColor
    let state: MultiVanPackageState
    /// The owner's current route ends at its house without this parcel.
    let isMissed: Bool
    /// Where the marker stands, in grid space: beside its node, clear of the roads.
    let point: RoadPoint

    static func pickups(engine: MultiVanEngine) -> [MultiVanPickup] {
        let routes = engine.previewRoutes
        let graph = engine.runtimeGraph
        return engine.level.packages.compactMap { package in
            guard let index = engine.level.vans.firstIndex(where: { $0.id == package.ownerVanID }) else { return nil }
            let route = index < routes.count ? routes[index] : nil
            return MultiVanPickup(
                id: package.id, nodeID: package.nodeID, ownerVanID: package.ownerVanID,
                color: engine.level.vans[index].color,
                state: engine.packageStates[package.id] ?? .atPickup,
                isMissed: route?.ending == .missingPackage && route?.missingPackageIDs.contains(package.id) == true,
                point: markerPoint(nodeID: package.nodeID, graph: graph)
            )
        }
    }

    /// How far the marker sits from its node along each axis, in grid units.
    static let markerOffset = 0.36

    /// The diagonal beside `nodeID` farthest from every road, so the parcel never
    /// covers asphalt or reads as part of another road. Ties keep a fixed order.
    static func markerPoint(nodeID: String, graph: RuntimeRouteGraph) -> RoadPoint {
        guard let node = graph.nodesByID[nodeID] else { return RoadPoint(x: 0, y: 0) }
        let tuning = MultiVanTuning.default
        let roads = graph.edgesByID.values.sorted { $0.id < $1.id }.map(\.roadPath)
        var best = RoadPoint(x: node.x + markerOffset, y: node.y + markerOffset)
        var bestClearance = -Double.infinity
        for (dx, dy) in [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)] {
            let candidate = RoadPoint(x: node.x + dx * markerOffset, y: node.y + dy * markerOffset)
            // Stay on the board: half a unit of lawn surrounds the grid.
            guard (-0.4...Double(tuning.gridColumns) - 0.6).contains(candidate.x),
                  (-0.4...Double(tuning.gridRows) - 0.6).contains(candidate.y) else { continue }
            var clearance = Double.infinity
            for road in roads where road.totalLength > 0 {
                for distance in stride(from: 0, through: road.totalLength, by: 0.1) {
                    let point = road.point(atDistance: distance)
                    clearance = min(clearance, hypot(point.x - candidate.x, point.y - candidate.y))
                }
            }
            if clearance > bestClearance + 1e-9 {
                bestClearance = clearance
                best = candidate
            }
        }
        return best
    }

    var accessibilityLabel: String {
        "Parcel for the \(color.displayName.lowercased()) \(color.accessibilitySymbolName) van"
    }

    var accessibilityValue: String {
        switch state {
        case .atPickup: isMissed ? "Waiting. The planned route does not pass it" : "Waiting to be collected"
        case .carried: "Collected"
        case .delivered: "Delivered"
        }
    }
}

/// A signal's lamp for one approach. Shape and word carry the state, not colour
/// alone: a square says STOP, a disc says GO.
struct MultiVanSignalLampView: View {
    let kind: MultiVanSignal.Kind
    let isOpen: Bool
    var side: CGFloat = 22

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: side * 0.2)
                .fill(Color(hex: 0x2A2933))
                .overlay { RoundedRectangle(cornerRadius: side * 0.2).strokeBorder(TRVillagePalette.cream, lineWidth: 1.5) }
            Group {
                if isOpen {
                    Circle().fill(Color(hex: 0x4CB862))
                } else {
                    RoundedRectangle(cornerRadius: side * 0.08).fill(Color(hex: 0xEC5B4B))
                }
            }
            .frame(width: side * 0.56, height: side * 0.56)
            Image(systemName: isOpen ? "arrow.up" : (kind == .drawbridge ? "water.waves" : "hand.raised.fill"))
                .font(.system(size: side * 0.3, weight: .black))
                .foregroundStyle(.white)
        }
        .frame(width: side, height: side)
        .shadow(color: TRVillagePalette.ink.opacity(0.25), radius: 2, y: 1.5)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Self.accessibilityLabel(kind: kind))
        .accessibilityValue(Self.accessibilityValue(kind: kind, isOpen: isOpen))
    }

    static func accessibilityLabel(kind: MultiVanSignal.Kind) -> String {
        kind == .drawbridge ? "Drawbridge" : "Traffic light"
    }

    static func accessibilityValue(kind: MultiVanSignal.Kind, isOpen: Bool) -> String {
        switch (kind, isOpen) {
        case (.trafficLight, true): "Go. Vans on this road may enter"
        case (.trafficLight, false): "Stop. Vans on this road wait at the line"
        case (.drawbridge, true): "Bridge down. Vans may cross"
        case (.drawbridge, false): "Bridge up. Vans wait at the line"
        }
    }
}

/// One stop line as every board draws it, read from the engine's signal states.
struct MultiVanSignalApproach: Equatable, Identifiable {
    let signalID: String
    let kind: MultiVanSignal.Kind
    let edgeID: String
    /// Where a held van stops, and the direction it faces there.
    let stopPoint: RoadPoint
    let tangent: RoadVector
    let isOpen: Bool

    var id: String { "\(signalID):\(edgeID)" }

    /// How far a lamp post stands from its stop line, to the right of travel.
    static let postOffset = 0.34

    /// Where the lamp stands, in grid space, on both boards.
    static func postPoint(stopPoint: RoadPoint, tangent: RoadVector) -> RoadPoint {
        RoadPoint(x: stopPoint.x + tangent.y * postOffset, y: stopPoint.y - tangent.x * postOffset)
    }

    var postPoint: RoadPoint { Self.postPoint(stopPoint: stopPoint, tangent: tangent) }

    static func approaches(engine: MultiVanEngine) -> [MultiVanSignalApproach] {
        let states = engine.signalStates
        let graph = engine.runtimeGraph
        return engine.level.signals.flatMap { signal in
            let open = states.first { $0.signalID == signal.id }?.openGroup
            return signal.approaches.compactMap { approach -> MultiVanSignalApproach? in
                guard let road = graph.edgesByID[approach.edgeID]?.roadPath else { return nil }
                return MultiVanSignalApproach(
                    signalID: signal.id, kind: signal.kind, edgeID: approach.edgeID,
                    stopPoint: road.point(atDistance: approach.stopDistance),
                    tangent: road.tangent(atDistance: approach.stopDistance),
                    isOpen: open == approach.group
                )
            }
        }
    }
}
