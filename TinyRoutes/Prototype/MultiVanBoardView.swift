import SwiftUI

struct MultiVanBoardView: View {
    let engine: MultiVanEngine
    var onSwitchTapped: ((String, MultiVanTapResult) -> Void)? = nil
    var onEventsProduced: (() -> Void)? = nil
    var celebration = MultiVanCelebration()
    var reducesExtraAnimations = false
    var personality = MultiVanPersonality()
    var onDeliveryEffectCompleted: (UUID) -> Void = { _ in }
    var crashEffects = MultiVanCrashEffects()
    var switchFeedback = MultiVanSwitchFeedback()
    var onCrashEffectCompleted: (UUID) -> Void = { _ in }
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var previewDrawings: [MultiVanPreviewDrawing] = []
    static let switchHitSize: CGFloat = 44

    private struct PreviewKey: Equatable {
        let engineID: ObjectIdentifier
        let routes: [MultiVanPreviewRoute]
        let size: CGSize
    }

    var body: some View {
        // Read observable values here, outside Canvas. Both layers capture the same
        // snapshot after a synchronous engine tap; neither keeps a local selection.
        let graph = engine.runtimeGraph
        let routes = engine.previewRoutes
        let vans = engine.vans
        let animatesDeliveries = !reduceMotion && !reducesExtraAnimations

        GeometryReader { geometry in
            let layout = Self.boardLayout(level: engine.level, size: geometry.size)
            ZStack(alignment: .topLeading) {
                boardCanvas(graph: graph, layout: layout)
                if let scale = layout.coordinateScale, scale > 0 {
                    ForEach(Self.barrierNodes(in: graph, houses: engine.level.houses), id: \.id) { node in
                        if let point = layout.pointsByNodeID[node.id] {
                            MultiVanBarrierView(width: min(32, scale * 0.65))
                                .rotationEffect(Self.barrierHeading(at: node, in: graph))
                                .position(point)
                                .allowsHitTesting(false)
                        }
                    }
                    ForEach(engine.level.houses, id: \.nodeID) { house in
                        if let point = layout.pointsByNodeID[house.nodeID] {
                            MultiVanHouseView(
                                color: house.color,
                                isDelivered: Self.isDelivered(house, vans: vans, graph: graph),
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
                                Self.isDelivered($0, vans: [van], graph: graph)
                            }
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
                ForEach(Self.switchNodes(in: graph), id: \.id) { node in
                    if let point = layout.pointsByNodeID[node.id],
                       let edgeID = node.activeOutgoingEdgeID,
                       let edge = graph.edgesByID[edgeID] {
                        let angle = SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: graph)
                        let appearance = MultiVanSwitchAppearance(
                            engine: engine, nodeID: node.id,
                            systemReduceMotion: reduceMotion, reducesExtraAnimations: reducesExtraAnimations
                        )
                        Button {
                            let result = engine.tapSwitch(nodeID: node.id)
                            onSwitchTapped?(node.id, result)
                            onEventsProduced?()
                        } label: {
                            SwitchNodeView(
                                activeDirectionAngle: angle,
                                spriteSize: Self.switchHitSize,
                                ringSize: 32,
                                optionCount: node.outgoingEdgeIDs.count,
                                optionAngles: node.outgoingEdgeIDs.compactMap { graph.edgesByID[$0] }.map {
                                    SwitchArrowDirectionResolver.directionAngle(for: $0, from: node, in: graph)
                                },
                                optionAnglesUseScreenCoordinates: true,
                                interactionState: .eligible
                            )
                            .animation(animatesDeliveries ? .spring(response: 0.24, dampingFraction: 0.8) : nil, value: angle)
                            .opacity(appearance.opacity)
                            .overlay {
                                MultiVanSwitchIndicators(
                                    appearance: appearance,
                                    rejectionToken: switchFeedback.rejectionTokens[node.id],
                                    reduceMotion: !animatesDeliveries
                                )
                                .allowsHitTesting(false)
                                .accessibilityHidden(true)
                            }
                            .keyframeAnimator(initialValue: 0.0, trigger: switchFeedback.rejectionTokens[node.id]) { content, progress in
                                content.offset(x: animatesDeliveries ? MultiVanCrashEffects.shakeOffset(progress: progress) * 0.75 : 0)
                            } keyframes: { _ in
                                MoveKeyframe(0.0)
                                LinearKeyframe(1.0, duration: 0.32)
                            }
                            .frame(width: Self.switchHitSize, height: Self.switchHitSize)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel(MultiVanSwitchAppearance.accessibilityLabel(node: node, gridRows: engine.tuning.gridRows))
                        .accessibilityValue(appearance.routeAccessibilityValue(
                            direction: SwitchOptionIndicatorLayout.cardinalDirectionLabel(for: angle),
                            exitCount: node.outgoingEdgeIDs.count
                        ))
                        .accessibilityHint(appearance.accessibilityHint)
                        .position(point)
                    }
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
            .onChange(of: PreviewKey(engineID: ObjectIdentifier(engine), routes: routes, size: geometry.size), initial: true) { _, _ in
                // Cache sampled paths across movement frames; only route/layout changes rebuild them.
                previewDrawings = MultiVanPreviewDrawing.make(
                    routes: routes, vans: engine.level.vans, graph: graph, layout: layout
                )
            }
        }
        .background { MultiVanBoardBackground() }
    }

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
        // Stable choice if an authored dead end has several incoming roads.
        let road = graph.edgesByID.values.filter { $0.toNodeID == node.id }
            .min { $0.id < $1.id }?.roadPath
        return MultiVanVanView.heading(
            for: road?.tangent(atDistance: road?.totalLength ?? 0) ?? RoadVector(x: 0, y: 1)
        )
    }

    static func boardLayout(level: MultiVanLevel, size: CGSize) -> BoardLayout {
        // Reserve half a hit target even when the grid is scaled below 44pt per unit.
        // Both layers use this MV-12 projection in the full Canvas coordinate space.
        MultiVanBoardLayout.make(
            level: level,
            in: CGRect(origin: .zero, size: size).insetBy(dx: switchHitSize / 2, dy: switchHitSize / 2)
        )
    }

    private func boardCanvas(
        graph: RuntimeRouteGraph, layout: BoardLayout
    ) -> some View {
        Canvas { context, _ in
            guard let scale = layout.coordinateScale, scale > 0 else { return }

            for edge in graph.edgesByID.values {
                context.stroke(
                    RoadPathRenderer.path(for: edge, layout: layout),
                    with: .color(Color(white: 0.85)),
                    style: StrokeStyle(lineWidth: min(14, scale * 0.2), lineCap: .round)
                )
            }

            // Preview order matches authored van order, including delayed departures.
            for drawing in previewDrawings {
                context.stroke(
                    drawing.path,
                    with: .color(drawing.color.boardColor),
                    style: StrokeStyle(lineWidth: min(4, scale * 0.065), lineCap: .round, dash: [6, 5])
                )
                if let point = drawing.endpoint {
                    let clearance = max(18, scale * 0.32 + 6)
                    // Small two-column stacks keep shared endpoints' glyphs distinct.
                    let dx = drawing.indicatorSlot.map { $0.isMultiple(of: 2) ? CGFloat(-10) : 10 } ?? clearance
                    let dy = -clearance - CGFloat((drawing.indicatorSlot ?? 0) / 2) * 26
                    context.draw(
                        Text(drawing.ending == .matchingHouse ? "✓" : "✗")
                            .font(.system(size: max(12, min(16, scale * 0.2)), weight: .bold))
                            .foregroundColor(drawing.color.boardColor),
                        at: CGPoint(x: point.x + dx, y: point.y + dy)
                    )
                }
            }

        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

/// Static artwork stays separate from the engine's per-frame observation.
private struct MultiVanBoardBackground: View {
    var body: some View {
        GeometryReader { geometry in
            let card = RoundedRectangle(cornerRadius: 20, style: .continuous)
            ZStack {
                SpriteImage(name: "background")
                    .scaledToFill()
                    .frame(width: geometry.size.width, height: geometry.size.height)
                    .opacity(0.40)

                // Soften the map's decorative streets beneath the actual road network.
                card.fill(.white.opacity(0.64))
            }
            .clipShape(card)
            .overlay { card.strokeBorder(.white.opacity(0.65), lineWidth: 1) }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
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

private struct MultiVanDeliveryPopup: View {
    let delivery: MultiVanCelebration.Delivery
    let side: CGFloat
    let onComplete: () -> Void

    var body: some View {
        // Each inserted ID owns its animation and cancellable cleanup task.
        Color.clear
            .frame(width: side, height: side)
            .keyframeAnimator(initialValue: 0.0, repeating: false) { content, progress in
                content.overlay {
                    Text(delivery.label)
                        .font(.system(.subheadline, design: .rounded, weight: .heavy))
                        .foregroundStyle(Color(red: 0.10, green: 0.34, blue: 0.22))
                        .padding(.horizontal, 9)
                        .padding(.vertical, 4)
                        .background(.regularMaterial, in: Capsule())
                        .overlay { Capsule().strokeBorder(.white, lineWidth: 1.5) }
                        .fixedSize()
                        .offset(y: -side * 0.8 - 14 * progress)
                        .opacity(min(1, (1 - progress) * 2))
                }
                .overlay {
                    // A tiny parcel pops beside the door, below the score label.
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
            .stroke(Color.red.opacity(reduceMotion ? 0.55 : (isPulsing ? 0.28 : 0.72)), lineWidth: 2)
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

extension VanColor {
    var boardColor: Color {
        switch self {
        case .red: return .red
        case .blue: return .blue
        case .yellow: return .yellow
        case .green: return .green
        }
    }
}

#if DEBUG
struct MultiVanBoardView_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            board(levelID: "proto_01").previewDisplayName("Level 1 — Go!")
            board(levelID: "proto_02").previewDisplayName("Level 2 — Pick a Lane")
            board(levelID: "proto_05").previewDisplayName("Level 5 — Two colours")
            board(levelID: "proto_07").previewDisplayName("Level 7 — Merge")
            board(levelID: "proto_08").previewDisplayName("Level 8 — Loop")
            board(levelID: "proto_09").previewDisplayName("Level 9 — Live switch")
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

/// All decoration stays inside the existing 44-point target, clear of the route arrow.
private struct MultiVanSwitchIndicators: View {
    let appearance: MultiVanSwitchAppearance
    let rejectionToken: UUID?
    let reduceMotion: Bool

    var body: some View {
        ZStack {
            if appearance.isLive {
                Circle()
                    .strokeBorder(Color.orange, style: StrokeStyle(
                        lineWidth: appearance.showsLock ? 3 : 2,
                        dash: appearance.showsLock ? [3, 2] : []
                    ))
                    .frame(width: 38, height: 38)
                    .phaseAnimator(appearance.pulses ? [false, true] : [false]) { content, phase in
                        content.opacity(phase ? 0.55 : 1)
                    } animation: { _ in appearance.pulses ? .easeInOut(duration: 0.9) : nil }
                badge("bolt.fill", color: .orange)
                    .offset(x: -13, y: -13)
            }
            if appearance.showsLock {
                badge("lock.fill", color: .primary)
                    .keyframeAnimator(initialValue: 1.0, trigger: rejectionToken) { content, opacity in
                        content.opacity(reduceMotion ? 1 : opacity)
                    } keyframes: { _ in
                        MoveKeyframe(1.0)
                        LinearKeyframe(0.25, duration: 0.08)
                        LinearKeyframe(1.0, duration: 0.08)
                        LinearKeyframe(0.25, duration: 0.08)
                        LinearKeyframe(1.0, duration: 0.08)
                    }
                    .offset(x: 13, y: -13)
            }
        }
        .frame(width: MultiVanBoardView.switchHitSize, height: MultiVanBoardView.switchHitSize)
    }

    private func badge(_ symbol: String, color: Color) -> some View {
        Image(systemName: symbol)
            .font(.system(size: 9, weight: .heavy))
            .foregroundStyle(color)
            .frame(width: 14, height: 14)
            .background(.white, in: Circle())
    }
}
