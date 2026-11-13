import SwiftUI

struct MultiVanBoardView: View {
    let engine: MultiVanEngine
    var onEventsProduced: (() -> Void)? = nil
    var celebration = MultiVanCelebration()
    var reducesExtraAnimations = false
    var personality = MultiVanPersonality()
    var onDeliveryEffectCompleted: (UUID) -> Void = { _ in }
    var crashEffects = MultiVanCrashEffects()
    var switchFeedback = MultiVanSwitchFeedback()
    var onCrashEffectCompleted: (UUID) -> Void = { _ in }
    /// Pieces a tutorial tip is about, ringed under the switches.
    var spotlightNodeIDs: [String] = []
    var onMissedTap: (() -> Void)? = nil
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.multiVanCosmetics) private var cosmetics
    @State private var previewCache: PreviewCache?

    private struct PreviewKey: Equatable {
        let engineID: ObjectIdentifier
        let routes: [MultiVanPreviewRoute]
        let size: CGSize
    }

    /// Sampled preview paths and the key they were built for.
    private struct PreviewCache {
        let key: PreviewKey
        let drawings: [MultiVanPreviewDrawing]
    }

    /// Builds from the key alone, never from values an older body captured.
    private func previewDrawings(for key: PreviewKey) -> [MultiVanPreviewDrawing] {
        MultiVanPreviewDrawing.make(
            routes: key.routes, vans: engine.level.vans, graph: engine.runtimeGraph,
            layout: Self.boardLayout(level: engine.level, size: key.size)
        )
    }

    var body: some View {
        // Read observable values here, outside Canvas. Both layers capture the same
        // snapshot after a synchronous engine tap; neither keeps a local selection.
        let graph = engine.runtimeGraph
        let routes = engine.previewRoutes
        let vans = engine.vans
        let animatesDeliveries = !reduceMotion && !reducesExtraAnimations
        let pickups = MultiVanPickup.pickups(engine: engine)
        let approaches = MultiVanSignalApproach.approaches(engine: engine)

        GeometryReader { geometry in
            let layout = Self.boardLayout(level: engine.level, size: geometry.size)
            let previewKey = PreviewKey(engineID: ObjectIdentifier(engine), routes: routes, size: geometry.size)
            // A cache from another key (first layout passes, before onChange lands) is
            // never drawn: the line would sit where an earlier board size put it.
            let drawings = previewCache.flatMap { $0.key == previewKey ? $0.drawings : nil }
                ?? previewDrawings(for: previewKey)
            ZStack(alignment: .topLeading) {
                if let onMissedTap {
                    Color.clear
                        .contentShape(Rectangle())
                        .onTapGesture(perform: onMissedTap)
                        .accessibilityHidden(true)
                }
                boardCanvas(graph: graph, vans: vans, layout: layout, previewDrawings: drawings, approaches: approaches)
                if let scale = layout.coordinateScale, scale > 0 {
                    ForEach(pickups) { pickup in
                        // Beside the road, so the van and its route line stay readable.
                        if let point = layout.point(for: pickup.point) {
                            MultiVanPickupMarker(
                                pickup: pickup, side: min(30, scale * 0.58),
                                reduceMotion: reduceMotion || reducesExtraAnimations
                            )
                            .position(point)
                            .allowsHitTesting(false)
                        }
                    }
                    ForEach(approaches) { approach in
                        // To the right of travel, off the asphalt.
                        if let point = layout.point(for: approach.postPoint) {
                            MultiVanSignalLampView(kind: approach.kind, isOpen: approach.isOpen, side: min(24, scale * 0.46))
                                .position(point)
                                .allowsHitTesting(false)
                        }
                    }
                    ForEach(MultiVanBoardRules.barrierNodes(in: graph, houses: engine.level.houses), id: \.id) { node in
                        if let point = layout.pointsByNodeID[node.id] {
                            MultiVanBarrierView(width: min(32, scale * 0.65))
                                .rotationEffect(MultiVanBoardRules.barrierHeading(at: node, in: graph))
                                .position(point)
                                .allowsHitTesting(false)
                        }
                    }
                    ForEach(engine.level.houses, id: \.nodeID) { house in
                        if let point = layout.pointsByNodeID[house.nodeID] {
                            MultiVanHouseView(
                                color: house.color,
                                isDelivered: MultiVanBoardRules.isDelivered(house, vans: vans, graph: graph),
                                side: min(40, scale * 0.8)
                            )
                            .keyframeAnimator(
                                initialValue: 1.0,
                                trigger: celebration.houseTokens[house.nodeID]
                            ) { content, scale in
                                content.scaleEffect(animatesDeliveries ? scale : 1)
                            } keyframes: { _ in
                                if celebration.houseTokens[house.nodeID] != nil {
                                    CubicKeyframe(1.16, duration: 0.12)
                                    SpringKeyframe(1, duration: 0.4, spring: .bouncy)
                                } else {
                                    MoveKeyframe(1)
                                }
                            }
                            .position(point)
                            .allowsHitTesting(false)
                        }
                    }
                }
                ForEach(vans, id: \.id) { van in
                    if let point = layout.point(for: van.position),
                       let scale = layout.coordinateScale, scale > 0 {
                        MultiVanVanView(
                            color: van.color, length: min(28, scale * 0.6),
                            status: van.status, reaction: personality.reactions[van.id],
                            reducesExtraAnimations: !animatesDeliveries,
                            isDelivered: engine.level.houses.contains {
                                MultiVanBoardRules.isDelivered($0, vans: [van], graph: graph)
                            },
                            cargo: engine.cargoStatus(forVanID: van.id),
                            turnSignal: engine.phase == .run ? MultiVanVanView.turnSignal(for: van, graph: graph) : nil,
                            signalIsLit: MultiVanVanView.signalIsLit(for: van, graph: graph, speed: engine.tuning.vanSpeed)
                        )
                            .rotationEffect(MultiVanVanView.heading(
                                for: van,
                                startNodeID: engine.level.vans.first { $0.id == van.id }?.startNodeID,
                                graph: graph
                            ))
                            .position(point)
                            .allowsHitTesting(false)
                    }
                }
                if engine.phase == .plan,
                   let failPoint = engine.lastFailPoint,
                   let point = layout.point(for: failPoint) {
                    MultiVanFailureRing(reduceMotion: reduceMotion || reducesExtraAnimations)
                        .position(point)
                        .allowsHitTesting(false)
                        .accessibilityHidden(true)
                }
                ForEach(spotlightNodeIDs, id: \.self) { nodeID in
                    if let point = layout.pointsByNodeID[nodeID] {
                        MultiVanTutorialSpotlight(reduceMotion: reduceMotion || reducesExtraAnimations)
                            .position(point)
                    }
                }
                ForEach(Self.switchPlacements(
                    controls: MultiVanSwitchControl.controls(
                        engine: engine, graph: graph,
                        systemReduceMotion: reduceMotion, reducesExtraAnimations: reducesExtraAnimations
                    ),
                    layout: layout, size: geometry.size
                )) { placement in
                    MultiVanSwitchButton(
                        control: placement.control, engine: engine,
                        onEventsProduced: onEventsProduced,
                        rejectionToken: switchFeedback.rejectionTokens[placement.control.nodeID],
                        animates: animatesDeliveries,
                        hitShape: placement.hitShape,
                        previewOffset: MultiVanSwitchButton.previewOffset(at: placement.point, in: geometry.size)
                    )
                    .position(placement.point)
                }
                if !reduceMotion && !reducesExtraAnimations {
                    if let impact = crashEffects.impact,
                       let point = layout.point(for: impact.point) {
                        MultiVanImpactPuff(impact: impact, onComplete: onCrashEffectCompleted)
                            .id(impact.id)
                            .position(point)
                    }
                    ForEach(celebration.deliveries) { delivery in
                        if let point = layout.pointsByNodeID[delivery.houseNodeID],
                           let scale = layout.coordinateScale, scale > 0 {
                            MultiVanDeliveryPopup(
                                delivery: delivery, side: min(40, scale * 0.8),
                                onComplete: { onDeliveryEffectCompleted(delivery.id) }
                            )
                            .position(point)
                        }
                    }
                }
            }
            .onChange(of: previewKey, initial: true) { _, key in
                // Cache sampled paths across movement frames; only route/layout changes rebuild them.
                previewCache = PreviewCache(key: key, drawings: previewDrawings(for: key))
            }
        }
        .background {
            MultiVanBoardLawn(
                level: engine.level, scenery: MultiVanFlatScenery.scenery(for: engine.level, graph: graph),
                // Only a drawbridge board has water to lay out.
                canals: engine.level.signals.contains { $0.kind == .drawbridge }
                    ? MultiVanDioramaLawn.Features(level: engine.level, graph: graph).canals : [],
                table: cosmetics.table
            )
            .equatable()
        }
    }

    static func boardLayout(level: MultiVanLevel, size: CGSize) -> BoardLayout {
        // Reserve half a hit target even when the grid is scaled below 44pt per unit.
        // Both layers use this MV-12 projection in the full Canvas coordinate space.
        let inset = MultiVanSwitchButton.hitSize / 2
        return MultiVanBoardLayout.make(
            level: level, in: CGRect(origin: .zero, size: size).insetBy(dx: inset, dy: inset)
        )
    }

    /// The switch buttons at their layout points.
    static func switchPlacements(
        controls: [MultiVanSwitchControl], layout: BoardLayout, size: CGSize
    ) -> [MultiVanSwitchPlacement] {
        MultiVanSwitchPlacement.make(
            controls.compactMap { control in layout.pointsByNodeID[control.nodeID].map { (control, $0) } },
            bounds: CGRect(origin: .zero, size: size)
        )
    }

    private func boardCanvas(
        graph: RuntimeRouteGraph, vans: [MultiVanVanState], layout: BoardLayout,
        previewDrawings: [MultiVanPreviewDrawing], approaches: [MultiVanSignalApproach]
    ) -> some View {
        let iceEdgeIDs = Set(engine.level.roadZones.filter { $0.kind == .ice }.flatMap(\.edgeIDs))
        return Canvas { context, _ in
            guard let scale = layout.coordinateScale, scale > 0 else { return }

            // The diorama's road in three passes, each over the whole network so
            // crossings merge: a cream curb, a white edge line, then the asphalt.
            var roads = Path()
            for edge in graph.edgesByID.values {
                roads.addPath(RoadPathRenderer.path(for: edge, layout: layout))
            }
            let pass = { (width: Double) in StrokeStyle(lineWidth: scale * width, lineCap: .round, lineJoin: .round) }
            var shadow = context
            shadow.translateBy(x: 0, y: scale * 0.04)
            shadow.stroke(roads, with: .color(TRVillagePalette.ink.opacity(0.14)), style: pass(MultiVanFlatRoad.curb))
            context.stroke(roads, with: .color(Color(hex: 0xEFE6D2)), style: pass(MultiVanFlatRoad.curb))
            context.stroke(roads, with: .color(.white), style: pass(MultiVanFlatRoad.edgeLine))
            context.stroke(roads, with: .color(Color(hex: 0x626779)), style: pass(MultiVanFlatRoad.asphalt))

            // Ice lies over the asphalt: pale, with a hatch that reads without colour.
            if !iceEdgeIDs.isEmpty {
                var ice = Path()
                for edge in graph.edgesByID.values where iceEdgeIDs.contains(edge.id) {
                    ice.addPath(RoadPathRenderer.path(for: edge, layout: layout))
                }
                context.stroke(ice, with: .color(Color(hex: 0xCFE8F7)), style: pass(MultiVanFlatRoad.asphalt))
                context.stroke(
                    ice, with: .color(.white),
                    style: StrokeStyle(lineWidth: scale * MultiVanFlatRoad.asphalt * 0.7, lineCap: .butt, dash: [2, 7])
                )
            }

            // Each stop line crosses its road where a held van waits.
            for approach in approaches {
                guard let point = layout.point(for: approach.stopPoint) else { continue }
                // Across the road: the tangent turned a quarter. Screen y runs down.
                let half = scale * MultiVanFlatRoad.asphalt / 2
                let across = CGPoint(x: CGFloat(approach.tangent.y) * half, y: CGFloat(approach.tangent.x) * half)
                var line = Path()
                line.move(to: CGPoint(x: point.x - across.x, y: point.y - across.y))
                line.addLine(to: CGPoint(x: point.x + across.x, y: point.y + across.y))
                context.stroke(line, with: .color(.white), style: StrokeStyle(lineWidth: max(2.5, scale * 0.06), lineCap: .butt))
            }

            // Preview order matches authored van order, including delayed departures.
            for (index, drawing) in previewDrawings.enumerated() {
                let van = index < vans.count ? vans[index] : nil
                // Round joins: a miter spikes out where the route turns back sharply.
                let style = StrokeStyle(lineWidth: min(2.5, scale * 0.04), lineCap: .round, lineJoin: .round, dash: [10, 7])
                // Each dash sits in a cream casing, so every colour reads on the asphalt.
                func dashes(_ path: Path, _ style: StrokeStyle) {
                    var casing = style
                    casing.lineWidth += 1.5
                    context.stroke(path, with: .color(TRVillagePalette.cream), style: casing)
                    context.stroke(path, with: .color(drawing.color.boardColor), style: style)
                }
                switch van?.status {
                case .waiting, nil:
                    dashes(drawing.path, style)
                case .driving:
                    // Like a sat-nav: road behind the van is no longer part of its route.
                    if let van, let edgeID = drawing.leadEdgeID, van.currentEdgeID == edgeID,
                       let length = graph.edgesByID[edgeID]?.roadPath.totalLength, length > 0 {
                        var trimmed = style
                        // Phase keeps the dashes fixed to the road while the line shortens.
                        trimmed.dashPhase = CGFloat(van.distanceAlongEdge) * scale
                        dashes(drawing.leadPath.trimmedPath(from: min(1, van.distanceAlongEdge / length), to: 1), trimmed)
                    }
                    // Drawings rebuild a frame after the van changes road; until then
                    // the stale lead road is behind it, so only the rest is drawn.
                    dashes(drawing.trailingPath, style)
                case .parked, .crashed, .stuck, .missingCargo:
                    continue
                }
                if let point = drawing.endpoint, let marker = drawing.marker {
                    let clearance = max(18, scale * 0.32 + 6)
                    // Small two-column stacks keep shared endpoints' glyphs distinct.
                    let dx = marker.column.map { CGFloat($0) * 10 } ?? clearance
                    let dy = -clearance - CGFloat(marker.row) * 26
                    let center = CGPoint(x: point.x + dx, y: point.y + dy)
                    let size = max(12, min(16, scale * 0.2))
                    let disc = Path(ellipseIn: CGRect(x: center.x - size * 0.68, y: center.y - size * 0.68, width: size * 1.36, height: size * 1.36))
                    context.fill(disc.offsetBy(dx: 0, dy: 1.5), with: .color(TRVillagePalette.ink.opacity(0.18)))
                    context.fill(disc, with: .color(TRVillagePalette.cream))
                    context.stroke(disc, with: .color(drawing.color.boardColor), lineWidth: 1.5)
                    context.draw(
                        Text(marker.glyph)
                            .font(.system(size: size * 0.8, weight: .heavy, design: .rounded))
                            .foregroundColor(drawing.color.boardInk),
                        at: center
                    )
                }
            }

        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

/// Road widths in grid units, a touch narrower than the diorama's so the flat
/// board's pieces keep room around them.
enum MultiVanFlatRoad {
    static let curb = 0.42
    static let edgeLine = 0.31
    static let asphalt = 0.28
}

/// The diorama's scenery for each level, placed once and kept: it depends only on
/// the level's roads and pieces, never on switches or vans.
@MainActor
enum MultiVanFlatScenery {
    private static var cache: [String: MultiVanDioramaScenery] = [:]

    static func scenery(for level: MultiVanLevel, graph: RuntimeRouteGraph) -> MultiVanDioramaScenery {
        if let cached = cache[level.id] { return cached }
        let scenery = MultiVanDioramaScenery(level: level, graph: graph)
        cache[level.id] = scenery
        return scenery
    }
}

/// The lawn card: mown grass on an earthy base, with the diorama's trees, bushes,
/// flower beds and pond seen from above. Static artwork, kept apart from the
/// engine's per-frame observation and redrawn only for a new level or size.
private struct MultiVanBoardLawn: View, Equatable {
    let level: MultiVanLevel
    let scenery: MultiVanDioramaScenery
    /// Water under each drawbridge, as the diorama's lawn paints it.
    var canals: [MultiVanDioramaLawn.Features.Canal] = []
    /// The table's base, from the shop.
    var table = MultiVanTableTheme.standard

    private static func drawCanals(
        _ context: GraphicsContext, canals: [MultiVanDioramaLawn.Features.Canal], layout: BoardLayout, scale: CGFloat
    ) {
        typealias Canal = MultiVanDioramaLawn.Features.Canal
        for canal in canals {
            let end = { (sign: Double) in
                layout.point(for: RoadPoint(
                    x: canal.centre.x + canal.across.x * Canal.halfLength * sign,
                    y: canal.centre.y + canal.across.y * Canal.halfLength * sign
                ))
            }
            guard let from = end(-1), let to = end(1) else { continue }
            var water = Path()
            water.move(to: from)
            water.addLine(to: to)
            for (width, hex) in [(Canal.width + 0.08, 0x7DB457), (Canal.width, 0x5A9CC4), (Canal.width * 0.8, 0x8CC3E0)] as [(Double, UInt32)] {
                context.stroke(water, with: .color(Color(hex: hex)), style: StrokeStyle(lineWidth: scale * width, lineCap: .round))
            }
        }
    }

    nonisolated static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.level.id == rhs.level.id && lhs.scenery == rhs.scenery && lhs.table == rhs.table
    }

    var body: some View {
        GeometryReader { geometry in
            let card = RoundedRectangle(cornerRadius: 22, style: .continuous)
            let layout = MultiVanBoardView.boardLayout(level: level, size: geometry.size)
            ZStack {
                // The base shows below the lawn, like the level map's board.
                card.fill(Color(hex: table.deepSoilHex)).offset(y: 8)
                card.fill(Color(hex: table.soilHex)).offset(y: 5)
                Canvas { context, size in
                    context.fill(Path(CGRect(origin: .zero, size: size)), with: .color(Color(hex: 0x8FC766)))
                    if let wash = level.biome.groundWash {
                        // The chapter's ground, as the diorama's lawn washes it.
                        context.fill(Path(CGRect(origin: .zero, size: size)), with: .color(Color(hex: wash.hex, opacity: wash.opacity)))
                    }
                    guard let scale = layout.coordinateScale, scale > 0 else { return }
                    Self.drawStripes(context, size: size, scale: scale)
                    Self.drawSpeckles(context, size: size, scale: scale)
                    Self.drawCanals(context, canals: canals, layout: layout, scale: scale)
                    Self.drawScenery(context, scenery: scenery, layout: layout, scale: scale, size: size)
                }
                .clipShape(card)
                card.strokeBorder(Color(hex: 0xB5DC8E).opacity(0.9), lineWidth: 2)
            }
            .shadow(color: TRVillagePalette.ink.opacity(0.22), radius: 12, y: 8)
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    /// Mowing stripes across the board, half a grid unit each.
    private static func drawStripes(_ context: GraphicsContext, size: CGSize, scale: CGFloat) {
        var light = Path(), dark = Path()
        for (index, y) in stride(from: 0, to: size.height, by: scale / 2).enumerated() {
            let band = CGRect(x: 0, y: y, width: size.width, height: scale / 2)
            if index.isMultiple(of: 2) { dark.addRect(band) } else { light.addRect(band) }
        }
        context.fill(dark, with: .color(Color(hex: 0x285014, opacity: 0.045)))
        context.fill(light, with: .color(.white.opacity(0.06)))
    }

    /// Grass speckles, the same every time for a board this size.
    private static func drawSpeckles(_ context: GraphicsContext, size: CGSize, scale: CGFloat) {
        var random = MultiVanDioramaRandom(seed: 11)
        var tufts = [Path(), Path(), Path()]
        for index in 0..<Int(size.width * size.height / 140) {
            let x = random.next() * size.width, y = random.next() * size.height
            let r = 0.8 + random.next() * 1.3
            tufts[index % 3].addEllipse(in: CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2))
        }
        for (path, hex) in zip(tufts, [0x7FB85A, 0x9FD474, 0xA9DA7F] as [UInt32]) {
            context.fill(path, with: .color(Color(hex: hex, opacity: 0.6)))
        }
    }

    private static func drawScenery(
        _ context: GraphicsContext, scenery: MultiVanDioramaScenery, layout: BoardLayout, scale: CGFloat, size: CGSize
    ) {
        let bounds = CGRect(origin: .zero, size: size)
        let ink = TRVillagePalette.ink
        if let pond = scenery.pond, let centre = layout.point(for: pond.centre) {
            var water = context
            water.translateBy(x: centre.x, y: centre.y)
            // Grid space turns anticlockwise from above; the screen's y runs down.
            water.rotate(by: .radians(-pond.angle))
            let rx = pond.radiusX * scale, ry = pond.radiusY * scale
            water.fill(Path(ellipseIn: CGRect(x: -rx - 2, y: -ry - 2, width: rx * 2 + 4, height: ry * 2 + 4)), with: .color(Color(hex: 0x7DB457)))
            water.fill(Path(ellipseIn: CGRect(x: -rx, y: -ry, width: rx * 2, height: ry * 2)), with: .color(Color(hex: 0x5A9CC4)))
            water.fill(Path(ellipseIn: CGRect(x: -rx * 0.92, y: -ry * 0.94, width: rx * 1.84, height: ry * 1.7)), with: .color(Color(hex: 0x8CC3E0)))
            var ripple = Path()
            ripple.move(to: CGPoint(x: -rx * 0.5, y: -ry * 0.2))
            ripple.addQuadCurve(to: CGPoint(x: rx * 0.35, y: -ry * 0.25), control: CGPoint(x: 0, y: -ry * 0.55))
            water.stroke(ripple, with: .color(.white.opacity(0.7)), style: StrokeStyle(lineWidth: 2, lineCap: .round))
        }
        // Seen from above nothing hides behind a tree, so the board takes about half
        // the diorama's trees and flowers. Flat things first, then the standing ones
        // from the back of the board forward.
        let items = scenery.items.enumerated().compactMap { index, item -> (MultiVanDioramaScenery.Item, CGPoint)? in
            switch item.kind {
            case .tree where index % 5 >= 3, .flowers where index.isMultiple(of: 2): return nil
            default: break
            }
            guard let point = layout.point(for: item.point) else { return nil }
            let reach = max(item.footprint, 0.12) * scale
            guard bounds.insetBy(dx: reach * 0.6, dy: reach * 0.6).contains(point) else { return nil }
            return (item, point)
        }.sorted { lhs, rhs in
            let lhsFlat = lhs.0.height == 0, rhsFlat = rhs.0.height == 0
            return lhsFlat != rhsFlat ? lhsFlat : lhs.1.y < rhs.1.y
        }
        for (item, point) in items {
            switch item.kind {
            case .flowers(let index):
                let color = Color(hex: UInt32(MultiVanDioramaScenery.flowerColors[index]))
                for (dx, dy) in [(-0.07, -0.03), (0.0, 0.05), (0.07, -0.02), (-0.02, -0.06), (0.05, 0.05)] {
                    let p = CGPoint(x: point.x + dx * scale, y: point.y + dy * scale)
                    context.fill(Path(ellipseIn: CGRect(x: p.x - 2.6, y: p.y - 2.6, width: 5.2, height: 5.2)), with: .color(TRVillagePalette.greens[2].opacity(0.5)))
                    context.fill(Path(ellipseIn: CGRect(x: p.x - 1.8, y: p.y - 2.4, width: 3.6, height: 3.6)), with: .color(color))
                }
            case .tree(let tree):
                let r = item.footprint * scale
                let shadow = Path(ellipseIn: CGRect(x: point.x - r * 0.9, y: point.y - r * 0.55, width: r * 2, height: r * 1.9))
                context.fill(shadow, with: .color(ink.opacity(0.2)))
                switch tree {
                case .pine:
                    // Seen from above, a pine is tiers of soft, scalloped boughs.
                    for (tier, shade) in [(0.9, TRVillagePalette.greens[3]), (0.62, TRVillagePalette.greens[2]), (0.34, Color(hex: 0x4CA35A))] {
                        context.fill(Self.star(at: CGPoint(x: point.x, y: point.y - r * 0.3), radius: r * tier, points: 9), with: .color(shade))
                    }
                case .round(let palette):
                    let greens = [(0x6BB361, 0x8CCC6B), (0x4CA35A, 0x6FBF63), (0x8CCC6B, 0xA9DA7F)][palette % 3]
                    let centre = CGPoint(x: point.x, y: point.y - r * 0.3)
                    context.fill(Path(ellipseIn: CGRect(x: centre.x - r, y: centre.y - r, width: r * 2, height: r * 2)), with: .color(Color(hex: UInt32(greens.0))))
                    context.fill(Path(ellipseIn: CGRect(x: centre.x - r * 0.82, y: centre.y - r * 0.9, width: r * 1.5, height: r * 1.5)), with: .color(Color(hex: UInt32(greens.1))))
                    context.fill(Path(ellipseIn: CGRect(x: centre.x - r * 0.55, y: centre.y - r * 0.65, width: r * 0.55, height: r * 0.5)), with: .color(.white.opacity(0.22)))
                }
            case .bush(let palette):
                let r = item.footprint * scale * 0.75
                let green = TRVillagePalette.greens[[0, 1, 2][palette % 3]]
                context.fill(Path(ellipseIn: CGRect(x: point.x - r * 1.3, y: point.y - r * 0.5, width: r * 2.8, height: r * 1.4)), with: .color(ink.opacity(0.16)))
                var clumps = Path()
                for (dx, dy, k) in [(-0.6, 0.0, 0.7), (0.0, -0.3, 0.85), (0.6, 0.05, 0.65)] {
                    let rr = r * k
                    clumps.addEllipse(in: CGRect(x: point.x + dx * r - rr, y: point.y + dy * r - rr - r * 0.3, width: rr * 2, height: rr * 2))
                }
                context.fill(clumps, with: .color(green))
                context.fill(Path(ellipseIn: CGRect(x: point.x - r * 0.35, y: point.y - r * 1.15, width: r * 0.5, height: r * 0.4)), with: .color(.white.opacity(0.22)))
            case .resident:
                continue
            }
        }
    }

    private static func star(at centre: CGPoint, radius: CGFloat, points: Int) -> Path {
        var path = Path()
        for index in 0..<(points * 2) {
            let angle = Double(index) * .pi / Double(points) - .pi / 2
            let r = index.isMultiple(of: 2) ? radius : radius * 0.8
            let point = CGPoint(x: centre.x + cos(angle) * r, y: centre.y + sin(angle) * r)
            if index == 0 { path.move(to: point) } else { path.addLine(to: point) }
        }
        path.closeSubpath()
        return path
    }
}

private struct MultiVanImpactPuff: View {
    let impact: MultiVanCrashEffects.Impact
    let onComplete: (UUID) -> Void

    var body: some View {
        Color.clear
            .frame(width: 64, height: 64)
            .keyframeAnimator(initialValue: 0.0, repeating: false) { content, progress in
                content.overlay {
                    ZStack {
                        Circle()
                            .fill(.white.opacity(0.9))
                            .frame(width: 14, height: 14)
                            .scaleEffect(1 + progress * 1.5)
                            .opacity((1 - progress) * (1 - progress))
                        ForEach(0..<6) { index in
                            let angle = Double(index) * .pi / 3
                            Circle()
                                .fill(Color(red: 0.76, green: 0.71, blue: 0.61))
                                .overlay { Circle().strokeBorder(.white.opacity(0.8), lineWidth: 1) }
                                .frame(width: 7, height: 7)
                                .scaleEffect(1 + progress * 0.6)
                                .offset(x: cos(angle) * (6 + 20 * progress),
                                        y: sin(angle) * (6 + 20 * progress))
                                .opacity(0.85 * (1 - progress))
                        }
                    }
                }
            } keyframes: { _ in
                LinearKeyframe(1, duration: MultiVanCrashEffects.impactDuration)
            }
            .allowsHitTesting(false)
            .accessibilityHidden(true)
            .task(id: impact.id) {
                do { try await Task.sleep(for: .seconds(MultiVanCrashEffects.impactDuration)) }
                catch { return }
                guard !Task.isCancelled else { return }
                onComplete(impact.id)
            }
    }
}

struct MultiVanDeliveryPopup: View {
    let delivery: MultiVanCelebration.Delivery
    let side: CGFloat
    /// False on the diorama, which throws a real parcel.
    var showsParcel = true
    let onComplete: () -> Void

    var body: some View {
        // Each inserted ID owns its animation and cancellable cleanup task.
        Color.clear
            .frame(width: side, height: side)
            .keyframeAnimator(initialValue: 0.0, repeating: false) { content, progress in
                content.overlay {
                    // Solid, so it reads over roads, lawn and the diorama alike
                    // (white on this green is 5:1).
                    Text(delivery.label)
                        .font(.system(.subheadline, design: .rounded, weight: .heavy))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 4)
                        .background(Color(red: 0.11, green: 0.50, blue: 0.27), in: Capsule())
                        .overlay { Capsule().strokeBorder(.white, lineWidth: 1.5) }
                        .shadow(color: .black.opacity(0.25), radius: 3, y: 1)
                        .fixedSize()
                        .offset(y: -side * 0.8 - 14 * progress)
                        .opacity(min(1, (1 - progress) * 2))
                }
                .overlay {
                    // A tiny parcel pops beside the door, below the score label.
                    if showsParcel {
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Color(red: 0.76, green: 0.49, blue: 0.25))
                            .overlay {
                                Rectangle()
                                    .fill(Color(red: 1, green: 0.85, blue: 0.57))
                                    .frame(width: 2)
                            }
                            .frame(width: 10, height: 8)
                            .scaleEffect(sin(progress * .pi))
                            .offset(x: side * 0.5 * (1 - progress), y: side * 0.4)
                    }
                }
            } keyframes: { _ in
                LinearKeyframe(1, duration: 0.55)
            }
            .allowsHitTesting(false)
            .accessibilityHidden(true)
            .task {
                do { try await Task.sleep(for: .milliseconds(550)) }
                catch { return }
                guard !Task.isCancelled else { return }
                onComplete()
            }
    }
}

private struct MultiVanFailureRing: View {
    let reduceMotion: Bool
    @State private var isPulsing = false

    var body: some View {
        Circle()
            .stroke(Color(hex: 0xD9473A).opacity(reduceMotion ? 0.55 : (isPulsing ? 0.28 : 0.72)), lineWidth: 2)
            .frame(width: 30, height: 30)
            .scaleEffect(reduceMotion || !isPulsing ? 1 : 1.28)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true)) {
                    isPulsing = true
                }
            }
            .onChange(of: reduceMotion) { _, reduced in
                if !reduced {
                    withAnimation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true)) {
                        isPulsing = true
                    }
                } else {
                    isPulsing = false
                }
            }
    }
}

/// The village's roof colours, shared with the level map and the diorama.
extension VanColor {
    var boardColor: Color {
        switch self {
        case .red: Color(hex: 0xEC5B4B)
        case .blue: Color(hex: 0x4A86E8)
        case .yellow: Color(hex: 0xF6C234)
        case .green: Color(hex: 0x4CB862)
        }
    }

    /// The colour's shade, under a van's body and round a house's sticker.
    var boardDeep: Color {
        switch self {
        case .red: Color(hex: 0xB8392C)
        case .blue: Color(hex: 0x2C5DB5)
        case .yellow: Color(hex: 0xC8921A)
        case .green: Color(hex: 0x2F8742)
        }
    }

    /// What the symbol is printed in: yellow's shade is too light on cream in
    /// grayscale, so it prints in ochre, as on the diorama.
    var boardInk: Color {
        self == .yellow ? Color(hex: 0x8F6208) : boardDeep
    }
}

#if DEBUG
struct MultiVanBoardView_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            board(levelID: "level_001").previewDisplayName("Level 1 — Go!")
            board(levelID: "level_002").previewDisplayName("Level 2 — Pick a Lane")
            board(levelID: "level_005").previewDisplayName("Level 5 — Two colours")
            board(levelID: "level_008").previewDisplayName("Level 7 — Merge")
            board(levelID: "level_010").previewDisplayName("Level 8 — Loop")
            board(levelID: "level_011").previewDisplayName("Level 9 — Live switch")
        }
        .previewLayout(.fixed(width: 320, height: 440))
    }

    private static func board(levelID: String) -> some View {
        let result = Result { () throws -> MultiVanEngine in
            let bundled = try MultiVanLevelRepository().loadAllLevels()
            let level: MultiVanLevel
            if let authored = bundled.first(where: { $0.id == levelID }) {
                level = authored
            } else {
                // Preview-only fallback to the same authored JSON when resources aren't bundled.
                let url = URL(fileURLWithPath: #filePath)
                    .deletingLastPathComponent().deletingLastPathComponent()
                    .appendingPathComponent("Resources/PrototypeLevels/\(levelID).json")
                level = try JSONDecoder().decode(MultiVanLevel.self, from: Data(contentsOf: url))
            }
            return try MultiVanEngine(level: level)
        }
        return preview(result)
    }

    @ViewBuilder
    private static func preview(_ result: Result<MultiVanEngine, Error>) -> some View {
        switch result {
        case .success(let engine): MultiVanBoardView(engine: engine)
        case .failure(let error): Text("Preview unavailable: \(error.localizedDescription)")
        }
    }
}
#endif
