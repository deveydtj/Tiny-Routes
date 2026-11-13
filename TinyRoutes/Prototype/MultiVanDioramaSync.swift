import Foundation

/// What the diorama shows on one frame, read from the engine on the main actor in
/// the board's `body`. Renderer-free: `MultiVanDioramaScene.sync` pushes it into
/// SceneKit, and tests hold it against what the flat board draws.
struct MultiVanDioramaFrame {
    struct Van: Equatable {
        enum Signal: Equatable {
            case left, right
            /// A van stopped at a dead end flashes both sides.
            case hazard
        }

        let id: String
        let color: VanColor
        let point: RoadPoint
        /// Direction of travel in grid space, as the flat board turns the van.
        let heading: RoadVector
        let status: MultiVanVanState.Status
        let currentEdgeID: String?
        let distanceAlongEdge: Double
        let signal: Signal?
        let signalIsLit: Bool
        /// Rumbles in place, as the flat board's van sways: waiting or parked, with motion on.
        let idles: Bool
        /// Holds every parcel it needs: a parcel rides on the roof.
        var carriesCargo = false
    }

    struct Dial: Equatable {
        let nodeID: String
        let activeAngle: Double
        let tint: MultiVanSwitchDialView.Tint
        /// Breathes like the flat board's live ring: live and free, mid-run, with motion on.
        let pulses: Bool
    }

    let graph: RuntimeRouteGraph
    let vans: [Van]
    let routes: [MultiVanPreviewRoute]
    /// The switch buttons' contents, in the order both boards list them.
    let controls: [MultiVanSwitchControl]
    let dials: [Dial]
    let deliveredHouseNodeIDs: Set<String>
    /// Every parcel and where it is, as the flat board's markers show them.
    let pickups: [MultiVanPickup]
    /// Every stop line and whether it lets vans in, as the flat board's lamps show.
    let signalApproaches: [MultiVanSignalApproach]
    /// Where the last run went wrong, ringed while the player plans the next.
    let failPoint: RoadPoint?
    /// False under Reduce Motion or "Reduce Animations": pieces snap instead of moving.
    let animates: Bool

    init(engine: MultiVanEngine, systemReduceMotion: Bool, reducesExtraAnimations: Bool) {
        let graph = engine.runtimeGraph
        let states = engine.vans
        let animates = !systemReduceMotion && !reducesExtraAnimations
        let isRunning = engine.phase == .run
        self.graph = graph
        self.animates = animates
        routes = engine.previewRoutes
        vans = states.map { state in
            let authored = engine.level.vans.first { $0.id == state.id }
            let turn = isRunning ? MultiVanVanView.turnSignal(for: state, graph: graph) : nil
            let signal: Van.Signal? = state.status == .stuck ? .hazard : turn.map { $0 == .left ? .left : .right }
            return Van(
                id: state.id, color: state.color, point: state.position,
                heading: MultiVanBoardRules.vanTangent(for: state, startNodeID: authored?.startNodeID, in: graph),
                status: state.status, currentEdgeID: state.currentEdgeID, distanceAlongEdge: state.distanceAlongEdge,
                signal: signal,
                // Like the flat board, only the system setting holds a signal steady.
                signalIsLit: systemReduceMotion || signal == .hazard
                    || MultiVanVanView.signalIsLit(for: state, graph: graph, speed: engine.tuning.vanSpeed),
                idles: MultiVanPersonality.isIdle(status: state.status, reduceMotion: !animates),
                carriesCargo: engine.cargoStatus(forVanID: state.id) == .carrying
            )
        }
        pickups = MultiVanPickup.pickups(engine: engine)
        signalApproaches = MultiVanSignalApproach.approaches(engine: engine)
        controls = MultiVanSwitchControl.controls(
            engine: engine, graph: graph,
            systemReduceMotion: systemReduceMotion, reducesExtraAnimations: reducesExtraAnimations
        )
        dials = controls.map {
            Dial(nodeID: $0.nodeID, activeAngle: $0.activeAngle, tint: $0.appearance.dialTint, pulses: $0.appearance.pulses)
        }
        deliveredHouseNodeIDs = Set(engine.level.houses.filter {
            MultiVanBoardRules.isDelivered($0, vans: states, graph: graph)
        }.map(\.nodeID))
        failPoint = engine.phase == .plan ? engine.lastFailPoint : nil
    }
}

/// The feedback the diorama plays, read from the same models the flat board reads.
/// Each token plays once, on the first sync that sees it; whatever a board finds
/// on its first sync already happened, so it stays quiet.
struct MultiVanDioramaCues: Equatable {
    struct Delivery: Equatable {
        let token: UUID
        let houseNodeID: String
        /// The van home at that house, which throws the parcel.
        let vanID: String?
        let color: VanColor
    }

    struct Impact: Equatable {
        let token: UUID
        let point: RoadPoint
    }

    /// One per house that has squashed since Go, as the flat board's house bounces.
    var deliveries: [Delivery] = []
    /// Vans pulling away, once each has started to drive.
    var departures: [String: UUID] = [:]
    /// Vans hopping as they arrive home.
    var arrivals: [String: UUID] = [:]
    var impact: Impact?
    var confetti: UUID?
    var rejections: [String: UUID] = [:]

    init() {}

    init(
        engine: MultiVanEngine, celebration: MultiVanCelebration, personality: MultiVanPersonality,
        crashEffects: MultiVanCrashEffects, switchFeedback: MultiVanSwitchFeedback
    ) {
        let graph = engine.runtimeGraph
        let vans = engine.vans
        deliveries = engine.level.houses.compactMap { house in
            guard let token = celebration.houseTokens[house.nodeID] else { return nil }
            let van = vans.first { $0.color == house.color && MultiVanBoardRules.isDelivered(house, vans: [$0], graph: graph) }
            return Delivery(token: token, houseNodeID: house.nodeID, vanID: van?.id, color: house.color)
        }
        for van in vans {
            // Tokens are only handed out with motion on; a departure waits for the van to move.
            let reaction = MultiVanPersonality.activeReaction(personality.reactions[van.id], status: van.status, reduceMotion: false)
            switch reaction?.kind {
            case .departure: departures[van.id] = reaction?.token
            case .delivery: arrivals[van.id] = reaction?.token
            // A crashed van's spin comes with its crashed pose.
            case .crash, nil: break
            }
        }
        impact = crashEffects.impact.map { Impact(token: $0.id, point: $0.point) }
        confetti = celebration.confettiID
        rejections = switchFeedback.rejectionTokens
    }

    /// Every token, for telling new cues from ones already played.
    var tokens: Set<UUID> {
        var tokens = Set(deliveries.map(\.token))
        tokens.formUnion(departures.values)
        tokens.formUnion(arrivals.values)
        tokens.formUnion(rejections.values)
        if let impact { tokens.insert(impact.token) }
        if let confetti { tokens.insert(confetti) }
        return tokens
    }
}

/// One van's preview route as a line of dots along its roads, ending in its ✓ / ✗.
/// Dots are fixed to the roads, so trimming behind a driving van only hides them.
struct MultiVanDioramaTrail: Equatable {
    struct Dot: Equatable {
        /// On the lawn, shifted into the route's lane.
        let point: RoadPoint
        /// Along the route from the start of its first road.
        let distance: Double
    }

    /// Grid units, wide enough to leave a gap between the dots.
    static let spacing = 0.16
    /// No dots under the van itself.
    static let clearance = 0.27
    /// About one dot across, so lines sharing a road sit side by side.
    static let laneWidth = 0.11

    let color: VanColor
    let leadEdgeID: String?
    let leadLength: Double
    let dots: [Dot]
    /// Where the line ends, in its lane; nil when there is no line.
    let endpoint: RoadPoint?
    let marker: MultiVanPreviewMarker?

    /// One trail per route, in authored van order, as `MultiVanPreviewDrawing.make` lays them out.
    static func make(routes: [MultiVanPreviewRoute], vans: [MultiVanVan], graph: RuntimeRouteGraph) -> [Self] {
        let lanes = MultiVanPreviewLanes.make(routes: routes)
        let markers = MultiVanPreviewMarker.make(routes: routes, vans: vans, graph: graph)
        return zip(vans, routes).enumerated().map { index, pair in
            let (van, route) = pair
            var dots: [Dot] = []
            var drawnEdgeIDs = Set<String>()
            var start = 0.0
            var leadLength = 0.0
            var endpoint = route.ending == .offRoad ? nil : graph.nodesByID[van.startNodeID].map { RoadPoint(x: $0.x, y: $0.y) }
            for (position, edgeID) in route.edgeIDs.enumerated() {
                guard let road = graph.edgesByID[edgeID]?.roadPath else { continue }
                let length = road.totalLength
                let offset = (lanes[index][edgeID] ?? 0) * laneWidth
                if position == 0 { leadLength = length }
                // A loop revisits roads; the lead keeps its own dots so trimming it
                // leaves the later pass drawn.
                if position == 0 || drawnEdgeIDs.insert(edgeID).inserted {
                    // Each road starts its own dots, so a rebuilt route keeps them in place.
                    // Strided, not summed, so rounding never adds a dot on the road's end.
                    for distance in stride(from: spacing / 2, to: length, by: spacing) {
                        dots.append(Dot(point: lanePoint(on: road, at: distance, offset: offset), distance: start + distance))
                    }
                }
                endpoint = lanePoint(on: road, at: length, offset: offset)
                start += length
            }
            return Self(
                color: van.color, leadEdgeID: route.edgeIDs.first, leadLength: leadLength,
                dots: dots, endpoint: endpoint, marker: markers[index]
            )
        }
    }

    /// The first dot still ahead of `van`, or nil when its line is gone (parked,
    /// crashed or stuck), like the flat board's dashes.
    func firstVisibleDot(for van: MultiVanDioramaFrame.Van?) -> Int? {
        let covered: Double
        switch van?.status {
        case .waiting, nil: covered = 0
        case .driving:
            // A route rebuilt for a later road no longer starts under the van.
            covered = van?.currentEdgeID == leadEdgeID ? van?.distanceAlongEdge ?? 0 : leadLength
        case .parked, .crashed, .stuck, .missingCargo: return nil
        }
        let limit = covered + Self.clearance
        return dots.firstIndex { $0.distance >= limit } ?? dots.count
    }

    /// `distance` along `road`, moved `offset` grid units to the right of travel.
    static func lanePoint(on road: RoadPath, at distance: Double, offset: Double) -> RoadPoint {
        let point = road.point(atDistance: distance)
        let tangent = road.tangent(atDistance: distance)
        let length = hypot(tangent.x, tangent.y)
        guard offset != 0, length.isFinite, length > 1e-9 else { return point }
        return RoadPoint(x: point.x + tangent.y / length * offset, y: point.y - tangent.x / length * offset)
    }
}
