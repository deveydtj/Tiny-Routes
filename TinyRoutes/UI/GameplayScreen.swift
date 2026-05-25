import SwiftUI

struct GameplayScreen: View {
    let levelID: String
    let isPaused: Bool
    let cosmeticLoadout: GameplayCosmeticLoadout
    let onPauseResumeTapped: () -> Void
    let onCompleteTapped: (TimeInterval, Int) -> Void
    let onFailTapped: (LevelFailureReason, TimeInterval, Int) -> Void
    let onExitTapped: () -> Void

    private let levelRepository: LevelRepository
    private let frameTimer = Timer.publish(every: 1.0 / 60.0, on: .main, in: .common).autoconnect()

    @State private var routeEngine: RouteEngine
    @State private var runtimeGraph: RuntimeRouteGraph?
    @State private var deliveryDot: DeliveryDot?
    @State private var packageNodeID: String = ""
    @State private var destinationNodeID: String = ""
    @State private var hasCollectedPackage: Bool = false
    @State private var tapCount: Int = 0
    @State private var timeRemaining: TimeInterval?
    @State private var loadErrorMessage: String?
    @State private var lastFrameDate: Date?
    @State private var hasDispatchedOutcome: Bool = false

    init(
        levelID: String,
        isPaused: Bool,
        cosmeticLoadout: GameplayCosmeticLoadout = .default,
        onPauseResumeTapped: @escaping () -> Void,
        onCompleteTapped: @escaping (TimeInterval, Int) -> Void,
        onFailTapped: @escaping (LevelFailureReason, TimeInterval, Int) -> Void,
        onExitTapped: @escaping () -> Void,
        levelRepository: LevelRepository = LevelRepository(),
        routeEngine: RouteEngine = RouteEngine()
    ) {
        self.levelID = levelID
        self.isPaused = isPaused
        self.cosmeticLoadout = cosmeticLoadout
        self.onPauseResumeTapped = onPauseResumeTapped
        self.onCompleteTapped = onCompleteTapped
        self.onFailTapped = onFailTapped
        self.onExitTapped = onExitTapped
        self.levelRepository = levelRepository
        _routeEngine = State(initialValue: routeEngine)
    }

    var body: some View {
        VStack(spacing: 12) {
            TRGameplayTopHUD(
                levelID: levelID,
                isPaused: isPaused,
                timeRemaining: timeRemaining,
                tapCount: tapCount
            )
            .padding(.top, 4)

            Group {
                if let loadErrorMessage {
                    Text(loadErrorMessage)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                        .padding(16)
                        .background {
                            TRGlassCardBackground(cornerRadius: 18)
                        }
                } else if let runtimeGraph {
                    RouteBoardView(
                        runtimeGraph: runtimeGraph,
                        deliveryDot: deliveryDot,
                        packageNodeID: packageNodeID,
                        destinationNodeID: destinationNodeID,
                        hasCollectedPackage: hasCollectedPackage,
                        cosmeticLoadout: cosmeticLoadout,
                        onNodeTapped: handleNodeTapped
                    )
                } else {
                    ProgressView("Loading board…")
                        .padding(16)
                        .background {
                            TRGlassCardBackground(cornerRadius: 18)
                        }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.horizontal, 2)

            TRGameplayBottomControls(
                isPaused: isPaused,
                onRestartTapped: restartLevel,
                onPauseResumeTapped: onPauseResumeTapped,
                onExitTapped: onExitTapped
            )
            .padding(.bottom, 4)
        }
        .task(id: levelID) {
            loadBoard()
        }
        .onReceive(frameTimer) { frameDate in
            advanceDot(at: frameDate)
        }
        .onChange(of: isPaused) { _, paused in
            if paused {
                lastFrameDate = nil
            }
        }
    }

    private func loadBoard() {
        resetViewState()

        loadErrorMessage = nil
        runtimeGraph = nil
        deliveryDot = nil
        packageNodeID = ""
        destinationNodeID = ""

        do {
            let levelData = try levelRepository.loadLevel(id: levelID)
            try routeEngine.buildGraph(from: levelData)
            let didStartMovement = routeEngine.startDotMovement()

            runtimeGraph = routeEngine.runtimeGraph
            deliveryDot = routeEngine.deliveryDot
            packageNodeID = levelData.packageNodeID
            destinationNodeID = levelData.destinationNodeID
            hasCollectedPackage = routeEngine.deliveryDot?.hasCollectedPackage ?? false
            timeRemaining = routeEngine.timeRemaining
            tapCount = routeEngine.tapCount

            if !didStartMovement {
                loadErrorMessage = "Level has no active outgoing edge from the start node."
            }
            dispatchLevelOutcomeIfNeeded()
        } catch {
            loadErrorMessage = error.localizedDescription
        }
    }

    private func restartLevel() {
        resetViewState()
        loadErrorMessage = nil

        guard routeEngine.restartLevel() else {
            loadBoard()
            return
        }

        runtimeGraph = routeEngine.runtimeGraph
        deliveryDot = routeEngine.deliveryDot
        packageNodeID = routeEngine.packageNodeID ?? ""
        destinationNodeID = routeEngine.destinationNodeID ?? ""
        hasCollectedPackage = routeEngine.deliveryDot?.hasCollectedPackage ?? false
        timeRemaining = routeEngine.timeRemaining
        tapCount = routeEngine.tapCount

        if routeEngine.deliveryDot?.currentEdgeID == nil {
            loadErrorMessage = "Level has no active outgoing edge from the start node."
        }
        dispatchLevelOutcomeIfNeeded()
    }

    private func advanceDot(at frameDate: Date) {
        guard !isPaused, runtimeGraph != nil else {
            lastFrameDate = nil
            return
        }

        let deltaTime = lastFrameDate.map { frameDate.timeIntervalSince($0) } ?? 0
        lastFrameDate = frameDate

        guard deltaTime > 0 else {
            deliveryDot = routeEngine.deliveryDot
            hasCollectedPackage = routeEngine.deliveryDot?.hasCollectedPackage ?? false
            timeRemaining = routeEngine.timeRemaining
            return
        }

        routeEngine.updateDot(deltaTime: deltaTime)
        deliveryDot = routeEngine.deliveryDot
        hasCollectedPackage = routeEngine.deliveryDot?.hasCollectedPackage ?? false
        timeRemaining = routeEngine.timeRemaining
        dispatchLevelOutcomeIfNeeded()
    }

    private func handleNodeTapped(_ nodeID: String) {
        guard !isPaused, routeEngine.levelOutcome == nil else {
            return
        }

        let didRotate = routeEngine.rotateSwitchNode(nodeID: nodeID)
        runtimeGraph = routeEngine.runtimeGraph
        if didRotate {
            tapCount = routeEngine.tapCount
        }
    }

    private func dispatchLevelOutcomeIfNeeded() {
        guard !hasDispatchedOutcome,
              let levelOutcome = routeEngine.levelOutcome else {
            return
        }

        hasDispatchedOutcome = true
        lastFrameDate = nil
        switch levelOutcome {
        case .completed:
            onCompleteTapped(routeEngine.elapsedTime ?? 0, routeEngine.tapCount)
        case let .failed(reason):
            onFailTapped(reason, routeEngine.elapsedTime ?? 0, routeEngine.tapCount)
        }
    }

    private func resetViewState() {
        hasCollectedPackage = false
        lastFrameDate = nil
        tapCount = 0
        timeRemaining = nil
        hasDispatchedOutcome = false
    }
}

struct RouteBoardView: View {
    let runtimeGraph: RuntimeRouteGraph
    let deliveryDot: DeliveryDot?
    let packageNodeID: String
    let destinationNodeID: String
    let hasCollectedPackage: Bool
    let cosmeticLoadout: GameplayCosmeticLoadout
    let onNodeTapped: (String) -> Void

    private let boardPadding = TRGameplayStyle.Metrics.boardPadding
    private let switchSpriteSize = TRGameplayStyle.Metrics.switchNodeSize
    private let switchRingSize = TRGameplayStyle.Metrics.switchCircleSize
    private let specialNodeSize = TRGameplayStyle.Metrics.packageMarkerSize
    private let destinationMarkerShellSize = TRGameplayStyle.Metrics.packageMarkerSize * 0.45
    private let specialNodeIconSize = TRGameplayStyle.Metrics.markerIconSize
    private let collectedPackageMarkerSize = TRGameplayStyle.Metrics.collectedPackageMarkerSize

    private let playerOuterSize = TRGameplayStyle.Metrics.playerOuterSize
    private let playerCoreSize = TRGameplayStyle.Metrics.playerCoreSize
    private let playerScale = TRGameplayStyle.Metrics.playerScale
    private let roadOuterWidth = TRGameplayStyle.Metrics.roadOuterWidth
    private let roadInnerWidth = TRGameplayStyle.Metrics.roadInnerWidth
    private let roadHighlightWidth = TRGameplayStyle.Metrics.roadHighlightWidth

    var body: some View {
        GeometryReader { geometry in
            let cosmeticStyle = TRGameplayCosmeticStyle(loadout: cosmeticLoadout)
            let nodes = runtimeGraph.nodesByID.values.sorted { $0.id < $1.id }
            let edges = runtimeGraph.edgesByID.values.sorted { $0.id < $1.id }
            let layout = BoardLayout.make(
                for: nodes,
                in: geometry.size,
                padding: boardPadding
            )
            let roadPaths = renderedRoadPaths(for: edges, in: runtimeGraph, layout: layout)
            let currentRoadPath = renderedCurrentDeliveryRoadPath(in: runtimeGraph, layout: layout)
            let deliveryDotPoint = deliveryDotPoint(in: layout)
            let isDeliveryDotMoving = deliveryDot?.currentEdgeID != nil || deliveryDot?.transition != nil
            let tapTargetResolver = RouteBoardTapTargetResolver(
                runtimeGraph: runtimeGraph,
                layout: layout,
                tapRadius: max(switchSpriteSize, specialNodeSize) * 0.65
            )

            ZStack {
                cosmeticStyle.boardOverlayGradient
                    .opacity(0.16)
                    .allowsHitTesting(false)
                    .accessibilityHidden(true)

                roadLayer(roadPaths, color: cosmeticStyle.roadShadowColor, lineWidth: roadOuterWidth + 3, yOffset: 2)
                roadLayer(roadPaths, color: cosmeticStyle.roadEdgeColor, lineWidth: roadOuterWidth)
                roadLayer(roadPaths, color: cosmeticStyle.roadFillColor, lineWidth: roadInnerWidth)
                roadLayer(roadPaths, color: cosmeticStyle.roadHighlightColor, lineWidth: roadHighlightWidth, yOffset: -3)

                ForEach(nodes, id: \.id) { node in
                    if let nodePoint = layout.pointsByNodeID[node.id] {
                        nodeView(for: node, layout: layout)
                            .position(nodePoint)
                    }
                }

                if let deliveryDotPoint {
                    TRDeliveryTrailView(
                        option: cosmeticLoadout.trail,
                        dotPoint: deliveryDotPoint,
                        isMoving: isDeliveryDotMoving,
                        roadPath: currentRoadPath
                    )
                    .frame(width: geometry.size.width, height: geometry.size.height)
                    .allowsHitTesting(false)

                    TRDeliveryDotView(
                        option: cosmeticLoadout.deliveryDot,
                        isMoving: isDeliveryDotMoving,
                        outerSize: playerOuterSize,
                        coreSize: playerCoreSize,
                        scale: playerScale
                    )
                        .position(deliveryDotPoint)
                        .allowsHitTesting(false)
                }
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
            .background(Color.clear)
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onEnded { value in
                        guard let nodeID = tapTargetResolver.nodeID(at: value.location) else {
                            return
                        }
                        onNodeTapped(nodeID)
                    }
            )
        }
    }

    @ViewBuilder
    private func roadLayer(
        _ roadPaths: [RenderedRoadPath],
        color: Color,
        lineWidth: CGFloat,
        yOffset: CGFloat = 0
    ) -> some View {
        ForEach(roadPaths) { roadPath in
            roadPath.path
                .stroke(
                    color,
                    style: StrokeStyle(lineWidth: lineWidth, lineCap: .butt, lineJoin: .round)
                )
                .offset(y: yOffset)
        }
    }

    @ViewBuilder
    private func nodeView(for node: RuntimeRouteNode, layout: BoardLayout) -> some View {
        if node.id == packageNodeID, !hasCollectedPackage {
            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: specialNodeIconSize, height: specialNodeIconSize)
                .scaleEffect(1.10)
        } else if node.id == packageNodeID {
            Image(systemName: "checkmark")
                .font(.system(size: 14, weight: .heavy))
                .foregroundStyle(TRGameplayStyle.Colors.successGreen)
        } else if node.id == destinationNodeID {
            TRDestinationMarkerView(
                option: cosmeticLoadout.destination,
                shellSize: destinationMarkerShellSize,
                iconSize: specialNodeIconSize
            )
        } else if let activeDirectionAngle = activeDirectionAngle(for: node) {
            SwitchNodeView(
                activeDirectionAngle: activeDirectionAngle,
                spriteSize: switchSpriteSize,
                ringSize: switchRingSize
            )
        } else {
            EmptyView()
        }
    }

    private func activeDirectionAngle(for node: RuntimeRouteNode) -> Double? {
        SwitchArrowDirectionResolver.activeDirectionAngle(for: node, in: runtimeGraph)
    }

    private func deliveryDotPoint(in layout: BoardLayout) -> CGPoint? {
        guard let deliveryDot else {
            return nil
        }

        if let transition = deliveryDot.transition {
            let clampedProgress = CGFloat(max(0, min(transition.progressAlongTransition, 1)))
            let roadPoint = transition.roadPath.point(atProgress: Double(clampedProgress))
            return layout.point(for: roadPoint)
        }

        if let currentEdgeID = deliveryDot.currentEdgeID,
           let edge = runtimeGraph.edgesByID[currentEdgeID] {
            let clampedProgress = CGFloat(max(0, min(deliveryDot.progressAlongEdge, 1)))
            let roadPoint = edge.roadPath.point(atProgress: Double(clampedProgress))
            return layout.point(for: roadPoint)
        }

        return layout.pointsByNodeID[deliveryDot.currentNodeID]
    }

    private func renderedCurrentDeliveryRoadPath(
        in runtimeGraph: RuntimeRouteGraph,
        layout: BoardLayout
    ) -> Path? {
        if let transition = deliveryDot?.transition {
            return roadPath(for: transition.roadPath, layout: layout)
        }

        if let currentEdgeID = deliveryDot?.currentEdgeID,
           let edge = runtimeGraph.edgesByID[currentEdgeID] {
            return roadPath(for: edge, layout: layout)
        }

        return nil
    }

    private func renderedRoadPaths(
        for edges: [RuntimeRouteEdge],
        in runtimeGraph: RuntimeRouteGraph,
        layout: BoardLayout
    ) -> [RenderedRoadPath] {
        let connectorGeometry = inferredConnectorGeometry(for: runtimeGraph, layout: layout)
        let edgePaths = edges.map { edge in
            let startDistance = connectorGeometry.startTrimDistanceByEdgeID[edge.id] ?? 0
            let endDistance = connectorGeometry.endTrimDistanceByEdgeID[edge.id] ?? edge.roadPath.totalLength
            let visibleRoadPath = edge.roadPath.trimmed(
                fromDistance: startDistance,
                toDistance: endDistance
            )
            return RenderedRoadPath(id: "edge-\(edge.id)", path: roadPath(for: visibleRoadPath, layout: layout))
        }

        return edgePaths + connectorGeometry.paths
    }

    private func inferredConnectorGeometry(
        for runtimeGraph: RuntimeRouteGraph,
        layout: BoardLayout
    ) -> RenderedConnectorGeometry {
        let nodes = runtimeGraph.nodesByID.values.sorted { $0.id < $1.id }
        let edges = runtimeGraph.edgesByID.values.sorted { $0.id < $1.id }
        let incomingEdgesByNodeID = Dictionary(grouping: edges, by: \.toNodeID)
        var paths: [RenderedRoadPath] = []
        var startTrimDistanceByEdgeID: [String: Double] = [:]
        var endTrimDistanceByEdgeID: [String: Double] = [:]

        for node in nodes {
            let outgoingEdges = runtimeGraph.validOutgoingEdgeIDs(for: node).compactMap { runtimeGraph.edgesByID[$0] }
            guard let incomingEdges = incomingEdgesByNodeID[node.id],
                  !incomingEdges.isEmpty,
                  outgoingEdges.count == 1 else {
                continue
            }

            let nodePoint = RoadPoint(x: node.x, y: node.y)
            for incomingEdge in incomingEdges {
                for outgoingEdge in outgoingEdges {
                    guard let connector = RoadPath.makePerpendicularConnector(
                        at: nodePoint,
                        from: incomingEdge.roadPath,
                        to: outgoingEdge.roadPath
                    ) else {
                        continue
                    }

                    endTrimDistanceByEdgeID[incomingEdge.id] = min(
                        endTrimDistanceByEdgeID[incomingEdge.id] ?? incomingEdge.roadPath.totalLength,
                        connector.entryDistanceAlongIncomingPath
                    )
                    startTrimDistanceByEdgeID[outgoingEdge.id] = max(
                        startTrimDistanceByEdgeID[outgoingEdge.id] ?? 0,
                        connector.exitDistanceAlongOutgoingPath
                    )
                    paths.append(RenderedRoadPath(
                        id: "connector-\(incomingEdge.id)-\(outgoingEdge.id)",
                        path: roadPath(for: connector.roadPath, layout: layout)
                    ))
                }
            }
        }

        return RenderedConnectorGeometry(
            paths: paths,
            startTrimDistanceByEdgeID: startTrimDistanceByEdgeID,
            endTrimDistanceByEdgeID: endTrimDistanceByEdgeID
        )
    }

    private func roadPath(for edge: RuntimeRouteEdge, layout: BoardLayout) -> Path {
        roadPath(for: edge.roadPath, layout: layout)
    }

    private func roadPath(for roadPath: RoadPath, layout: BoardLayout) -> Path {
        Path { path in
            guard let firstSegment = roadPath.segments.first,
                  let startPoint = layout.point(for: firstSegment.start) else {
                return
            }

            path.move(to: startPoint)
            for segment in roadPath.segments {
                switch segment.kind {
                case .straight:
                    if let endPoint = layout.point(for: segment.end) {
                        path.addLine(to: endPoint)
                    }
                case .quarterTurn:
                    guard let center = segment.center,
                          let centerPoint = layout.point(for: center),
                          let scale = layout.coordinateScale else {
                        if let endPoint = layout.point(for: segment.end) {
                            path.addLine(to: endPoint)
                        }
                        continue
                    }

                    path.addArc(
                        center: centerPoint,
                        radius: CGFloat(segment.radius) * scale,
                        startAngle: .radians(-segment.startAngle),
                        endAngle: .radians(-(segment.startAngle + segment.signedAngleDelta)),
                        clockwise: segment.signedAngleDelta > 0
                    )
                case .smoothTurn:
                    guard let endPoint = layout.point(for: segment.end),
                          let control1 = segment.control1,
                          let control2 = segment.control2,
                          let controlPoint1 = layout.point(for: control1),
                          let controlPoint2 = layout.point(for: control2) else {
                        if let endPoint = layout.point(for: segment.end) {
                            path.addLine(to: endPoint)
                        }
                        continue
                    }

                    path.addCurve(to: endPoint, control1: controlPoint1, control2: controlPoint2)
                }
            }
        }
    }

}

struct SwitchArrowDirectionResolver {
    static func activeDirectionAngle(for node: RuntimeRouteNode, in runtimeGraph: RuntimeRouteGraph) -> Double? {
        let validOutgoingEdgeIDs = runtimeGraph.validOutgoingEdgeIDs(for: node)

        guard validOutgoingEdgeIDs.count > 1,
              let activeEdgeID = node.activeOutgoingEdgeID,
              validOutgoingEdgeIDs.contains(activeEdgeID),
              let activeEdge = runtimeGraph.edgesByID[activeEdgeID] else {
            return nil
        }

        if let targetNode = runtimeGraph.nodesByID[activeEdge.toNodeID] {
            let dx = targetNode.x - node.x
            let dy = targetNode.y - node.y
            if dx != 0 || dy != 0 {
                return atan2(-dy, dx)
            }
        }

        let tangent = activeEdge.roadPath.tangent(atProgress: 0)
        return atan2(-tangent.y, tangent.x)
    }
}

private struct RenderedRoadPath: Identifiable {
    let id: String
    let path: Path
}

private struct RenderedConnectorGeometry {
    let paths: [RenderedRoadPath]
    let startTrimDistanceByEdgeID: [String: Double]
    let endTrimDistanceByEdgeID: [String: Double]
}

struct RouteBoardTapTargetResolver {
    let runtimeGraph: RuntimeRouteGraph
    let layout: BoardLayout
    let tapRadius: CGFloat

    func nodeID(at point: CGPoint) -> String? {
        let tapRadiusSquared = tapRadius * tapRadius

        return runtimeGraph.nodesByID.values
            .compactMap { node -> (nodeID: String, distanceSquared: CGFloat)? in
                let validOutgoingEdgeIDs = runtimeGraph.validOutgoingEdgeIDs(for: node)
                guard validOutgoingEdgeIDs.count > 1,
                      let nodePoint = layout.pointsByNodeID[node.id] else {
                    return nil
                }

                let dx = nodePoint.x - point.x
                let dy = nodePoint.y - point.y
                let distanceSquared = (dx * dx) + (dy * dy)
                guard distanceSquared <= tapRadiusSquared else {
                    return nil
                }

                return (node.id, distanceSquared)
            }
            .min { lhs, rhs in
                if lhs.distanceSquared == rhs.distanceSquared {
                    return lhs.nodeID < rhs.nodeID
                }
                return lhs.distanceSquared < rhs.distanceSquared
            }?
            .nodeID
    }
}

struct BoardLayout {
    let pointsByNodeID: [String: CGPoint]
    let coordinateScale: CGFloat?
    private let minX: Double
    private let maxY: Double
    private let originX: CGFloat
    private let originY: CGFloat

    init(
        pointsByNodeID: [String: CGPoint],
        coordinateScale: CGFloat? = nil,
        minX: Double = 0,
        maxY: Double = 0,
        originX: CGFloat = 0,
        originY: CGFloat = 0
    ) {
        self.pointsByNodeID = pointsByNodeID
        self.coordinateScale = coordinateScale
        self.minX = minX
        self.maxY = maxY
        self.originX = originX
        self.originY = originY
    }

    /// Ensures non-zero usable dimensions for board layout calculations.
    private static let minimumUsableDimension: CGFloat = 1
    /// Multiplier used to compute circular spread radius for identical node coordinates.
    private static let degenerateLayoutSpreadFactor: CGFloat = 0.15

    static func make(
        for nodes: [RuntimeRouteNode],
        in size: CGSize,
        padding: CGFloat
    ) -> BoardLayout {
        guard !nodes.isEmpty else {
            return BoardLayout(pointsByNodeID: [:])
        }

        let minX = nodes.map(\.x).min() ?? 0
        let maxX = nodes.map(\.x).max() ?? 0
        let minY = nodes.map(\.y).min() ?? 0
        let maxY = nodes.map(\.y).max() ?? 0

        let widthRange = maxX - minX
        let heightRange = maxY - minY

        let usableWidth = max(size.width - (padding * 2), minimumUsableDimension)
        let usableHeight = max(size.height - (padding * 2), minimumUsableDimension)

        if widthRange == 0, heightRange == 0 {
            let centerPoint = CGPoint(x: size.width / 2, y: size.height / 2)
            let count = nodes.count
            let averageUsableDimension = (usableWidth + usableHeight) / 2
            let spreadRadius = averageUsableDimension * degenerateLayoutSpreadFactor
            var pointsByNodeID: [String: CGPoint] = [:]
            for (index, node) in nodes.enumerated() {
                guard count > 1 else {
                    pointsByNodeID[node.id] = centerPoint
                    continue
                }

                let angle = (2 * .pi * CGFloat(index)) / CGFloat(count)
                let point = CGPoint(
                    x: centerPoint.x + (cos(angle) * spreadRadius),
                    y: centerPoint.y + (sin(angle) * spreadRadius)
                )
                pointsByNodeID[node.id] = point
            }
            return BoardLayout(pointsByNodeID: pointsByNodeID)
        }

        let hasHorizontalRange = widthRange > 0
        let hasVerticalRange = heightRange > 0

        let scale: CGFloat
        switch (hasHorizontalRange, hasVerticalRange) {
        case (true, true):
            scale = min(usableWidth / widthRange, usableHeight / heightRange)
        case (true, false):
            scale = usableWidth / widthRange
        case (false, true):
            scale = usableHeight / heightRange
        case (false, false):
            scale = 1
        }

        let boardWidth = widthRange * scale
        let boardHeight = heightRange * scale
        let originX = (size.width - boardWidth) / 2
        let originY = (size.height - boardHeight) / 2

        var pointsByNodeID: [String: CGPoint] = [:]
        for node in nodes {
            let x: CGFloat
            if widthRange > 0 {
                let normalizedX = (node.x - minX) / widthRange
                x = originX + (normalizedX * boardWidth)
            } else {
                x = size.width / 2
            }

            let y: CGFloat
            if heightRange > 0 {
                let normalizedY = (maxY - node.y) / heightRange
                y = originY + (normalizedY * boardHeight)
            } else {
                y = size.height / 2
            }

            pointsByNodeID[node.id] = CGPoint(x: x, y: y)
        }

        return BoardLayout(
            pointsByNodeID: pointsByNodeID,
            coordinateScale: scale,
            minX: minX,
            maxY: maxY,
            originX: originX,
            originY: originY
        )
    }

    func point(for roadPoint: RoadPoint) -> CGPoint? {
        guard let coordinateScale else {
            return nil
        }

        return CGPoint(
            x: originX + (CGFloat(roadPoint.x - minX) * coordinateScale),
            y: originY + (CGFloat(maxY - roadPoint.y) * coordinateScale)
        )
    }
}

struct GameplayScreen_Previews: PreviewProvider {
    static var previews: some View {
        GameplayScreen(
            levelID: "level_001",
            isPaused: false,
            onPauseResumeTapped: {},
            onCompleteTapped: { _, _ in },
            onFailTapped: { _, _, _ in },
            onExitTapped: {}
        )
    }
}
