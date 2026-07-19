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
    @State private var activeObjective: RouteObjective?
    @State private var tapCount: Int = 0
    @State private var lastRotatedSwitchNodeID: String?
    @State private var switchPressEventToken: Int = 0
    @State private var lastRejectedSwitchNodeID: String?
    @State private var switchRejectionEventToken: Int = 0
    @State private var timeRemaining: TimeInterval?
    @State private var tutorialMessage: String?
    @State private var loadErrorMessage: String?
    @State private var lastFrameDate: Date?
    @State private var hasDispatchedOutcome: Bool = false
    @State private var isShowingLevelPreview: Bool = false
    @State private var previewDismissScheduler = LevelPreviewDismissScheduler()

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

            if let tutorialMessage {
                TRGameplayTutorialCard(message: tutorialMessage)
            }

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
                        activeObjective: activeObjective,
                        cosmeticLoadout: cosmeticLoadout,
                        isShowingPreview: isShowingLevelPreview,
                        pressedSwitchNodeID: lastRotatedSwitchNodeID,
                        switchPressEventToken: switchPressEventToken,
                        rejectedSwitchNodeID: lastRejectedSwitchNodeID,
                        switchRejectionEventToken: switchRejectionEventToken,
                        upcomingSwitchNodeID: routeEngine.switchEligibilitySnapshot.upcomingNodeID,
                        eligibleSwitchNodeID: routeEngine.eligibleSwitchNodeID,
                        onNodeTapped: handleNodeTapped
                    )
                    .onAppear {
                        finishPreviewIfNeeded(for: runtimeGraph)
                    }
                    .onChange(of: runtimeGraph.nodesByID.count) { _, _ in
                        finishPreviewIfNeeded(for: runtimeGraph)
                    }
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
        .onChange(of: isShowingLevelPreview) { _, isPreviewing in
            if isPreviewing {
                lastFrameDate = nil
            }
        }
        .onDisappear {
            previewDismissScheduler.cancel()
        }
    }

    private func loadBoard() {
        resetViewState()

        loadErrorMessage = nil
        runtimeGraph = nil
        deliveryDot = nil
        packageNodeID = ""
        destinationNodeID = ""
        activeObjective = nil

        do {
            let levelData = try levelRepository.loadLevel(id: levelID)
            try routeEngine.buildGraph(from: levelData)
            let didStartMovement = routeEngine.startDotMovement()

            runtimeGraph = routeEngine.runtimeGraph
            deliveryDot = routeEngine.deliveryDot
            packageNodeID = levelData.packageNodeID
            destinationNodeID = levelData.destinationNodeID
            hasCollectedPackage = routeEngine.deliveryDot?.hasCollectedPackage ?? false
            activeObjective = routeEngine.activeObjective
            timeRemaining = routeEngine.timeRemaining
            tapCount = routeEngine.tapCount
            tutorialMessage = levelData.tutorialMessage?.trimmingCharacters(in: .whitespacesAndNewlines)
            if tutorialMessage?.isEmpty == true {
                tutorialMessage = nil
            }
            isShowingLevelPreview = shouldPreviewLevel(runtimeGraph: routeEngine.runtimeGraph)

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
        activeObjective = routeEngine.activeObjective
        timeRemaining = routeEngine.timeRemaining
        tapCount = routeEngine.tapCount
        isShowingLevelPreview = shouldPreviewLevel(runtimeGraph: routeEngine.runtimeGraph)

        if routeEngine.deliveryDot?.currentEdgeID == nil {
            loadErrorMessage = "Level has no active outgoing edge from the start node."
        }
        dispatchLevelOutcomeIfNeeded()
    }

    private func advanceDot(at frameDate: Date) {
        guard !isPaused, !isShowingLevelPreview, runtimeGraph != nil else {
            lastFrameDate = nil
            return
        }

        let deltaTime = lastFrameDate.map { frameDate.timeIntervalSince($0) } ?? 0
        lastFrameDate = frameDate

        guard deltaTime > 0 else {
            runtimeGraph = routeEngine.runtimeGraph
            deliveryDot = routeEngine.deliveryDot
            hasCollectedPackage = routeEngine.deliveryDot?.hasCollectedPackage ?? false
            activeObjective = routeEngine.activeObjective
            timeRemaining = routeEngine.timeRemaining
            return
        }

        routeEngine.updateDot(deltaTime: deltaTime)
        runtimeGraph = routeEngine.runtimeGraph
        deliveryDot = routeEngine.deliveryDot
        hasCollectedPackage = routeEngine.deliveryDot?.hasCollectedPackage ?? false
        activeObjective = routeEngine.activeObjective
        timeRemaining = routeEngine.timeRemaining
        dispatchLevelOutcomeIfNeeded()
    }

    private func handleNodeTapped(_ nodeID: String) {
        guard !isPaused, routeEngine.levelOutcome == nil else {
            return
        }

        let result = routeEngine.rotateSwitchNode(nodeID: nodeID)
        runtimeGraph = routeEngine.runtimeGraph
        if result.didRotate {
            tapCount = routeEngine.tapCount
            lastRotatedSwitchNodeID = nodeID
            switchPressEventToken += 1
        } else {
            lastRejectedSwitchNodeID = nodeID
            switchRejectionEventToken += 1
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

    private func shouldPreviewLevel(runtimeGraph: RuntimeRouteGraph?) -> Bool {
        guard let runtimeGraph else {
            return false
        }

        let extents = LevelPlayableExtents.make(for: runtimeGraph)
        return extents.playableBounds.height >= TRGameplayStyle.Metrics.largeLevelPreviewHeightThreshold
    }

    private func finishPreviewIfNeeded(for runtimeGraph: RuntimeRouteGraph) {
        guard shouldPreviewLevel(runtimeGraph: runtimeGraph), isShowingLevelPreview else {
            return
        }

        previewDismissScheduler.schedule(
            afterNanoseconds: TRGameplayStyle.Metrics.levelPreviewDurationNanoseconds
        ) {
            guard self.shouldPreviewLevel(runtimeGraph: runtimeGraph) else {
                return
            }
            withAnimation(.easeInOut(duration: 0.45)) {
                self.isShowingLevelPreview = false
            }
        }
    }

    private func resetViewState() {
        previewDismissScheduler.cancel()
        hasCollectedPackage = false
        activeObjective = nil
        lastFrameDate = nil
        tapCount = 0
        lastRotatedSwitchNodeID = nil
        switchPressEventToken = 0
        lastRejectedSwitchNodeID = nil
        switchRejectionEventToken = 0
        timeRemaining = nil
        tutorialMessage = nil
        hasDispatchedOutcome = false
        isShowingLevelPreview = false
    }
}

@MainActor
final class LevelPreviewDismissScheduler {
    typealias Sleep = (UInt64) async throws -> Void

    private let sleep: Sleep
    private var previewDismissTask: Task<Void, Never>?
    private var generation = 0

    init(sleep: @escaping Sleep = { try await Task.sleep(nanoseconds: $0) }) {
        self.sleep = sleep
    }

    func schedule(afterNanoseconds durationNanoseconds: UInt64, action: @MainActor @escaping () -> Void) {
        generation += 1
        let scheduledGeneration = generation
        previewDismissTask?.cancel()
        previewDismissTask = Task { @MainActor [weak self] in
            guard let self else {
                return
            }

            do {
                try await sleep(durationNanoseconds)
            } catch {
                return
            }

            guard !Task.isCancelled, generation == scheduledGeneration else {
                return
            }

            action()
        }
    }

    func cancel() {
        generation += 1
        previewDismissTask?.cancel()
        previewDismissTask = nil
    }

    deinit {
        previewDismissTask?.cancel()
    }
}

enum LevelPreviewTapPolicy {
    static func allowsNodeTap(isShowingPreview: Bool) -> Bool {
        !isShowingPreview
    }
}

struct RouteBoardView: View {
    let runtimeGraph: RuntimeRouteGraph
    let deliveryDot: DeliveryDot?
    let packageNodeID: String
    let destinationNodeID: String
    let hasCollectedPackage: Bool
    let activeObjective: RouteObjective?
    let cosmeticLoadout: GameplayCosmeticLoadout
    let isShowingPreview: Bool
    let pressedSwitchNodeID: String?
    let switchPressEventToken: Int
    let rejectedSwitchNodeID: String?
    let switchRejectionEventToken: Int
    let upcomingSwitchNodeID: String?
    let eligibleSwitchNodeID: String?
    let onNodeTapped: (String) -> Void

    private let boardPadding = TRGameplayStyle.Metrics.boardPadding
    private let switchSpriteSize = TRGameplayStyle.Metrics.switchNodeSize
    private let switchRingSize = TRGameplayStyle.Metrics.switchCircleSize
    private let packageBadgeSize = TRGameplayStyle.Metrics.packageBadgeSize
    private let destinationMarkerShellSize = TRGameplayStyle.Metrics.packageMarkerSize * 0.45
    private let specialNodeIconSize = TRGameplayStyle.Metrics.markerIconSize

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
            let deliveryDotWorldPosition = deliveryDot?.runtimePosition(in: runtimeGraph).map {
                RoadPoint(x: $0.x, y: $0.y)
            }
            let layout = BoardLayout.make(
                for: runtimeGraph,
                in: geometry.size,
                padding: boardPadding,
                cameraMode: isShowingPreview ? .preview : .follow(deliveryDotWorldPosition)
            )
            let roadPaths = renderedRoadPaths(for: edges, in: runtimeGraph, layout: layout)
            let roadHubs = renderedRoadHubs(for: runtimeGraph, layout: layout)
            let currentRoadPath = renderedCurrentDeliveryRoadPath(in: runtimeGraph, layout: layout)
            let deliveryDotPoint = deliveryDotPoint(in: layout)
            let isDeliveryDotMoving = deliveryDot?.currentEdgeID != nil || deliveryDot?.transition != nil
            let tapTargetResolver = RouteBoardTapTargetResolver(
                runtimeGraph: runtimeGraph,
                layout: layout,
                hasCollectedPackage: hasCollectedPackage
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
                roadHubLayer(roadHubs, color: cosmeticStyle.roadEdgeColor, size: roadOuterWidth * 1.15)
                roadHubLayer(roadHubs, color: cosmeticStyle.roadFillColor, size: roadInnerWidth * 1.35)
                roadHubLayer(roadHubs, color: cosmeticStyle.roadHighlightColor, size: roadHighlightWidth * 1.15, yOffset: -3)

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
            .clipped()
            .animation(.easeOut(duration: 0.18), value: layout.cameraAnimationKey)
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onEnded { value in
                        guard LevelPreviewTapPolicy.allowsNodeTap(isShowingPreview: isShowingPreview) else {
                            return
                        }
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
                    style: StrokeStyle(lineWidth: lineWidth, lineCap: .round, lineJoin: .round)
                )
                .offset(y: yOffset)
        }
    }

    @ViewBuilder
    private func roadHubLayer(
        _ roadHubs: [RenderedRoadHub],
        color: Color,
        size: CGFloat,
        yOffset: CGFloat = 0
    ) -> some View {
        ForEach(roadHubs) { roadHub in
            Circle()
                .fill(color)
                .frame(width: size, height: size)
                .position(roadHub.point)
                .offset(y: yOffset)
        }
    }

    @ViewBuilder
    private func nodeView(for node: RuntimeRouteNode, layout: BoardLayout) -> some View {
        if let activeObjective, node.id == activeObjective.nodeID {
            TRCurrentObjectiveMarkerView(
                objective: activeObjective,
                destinationOption: cosmeticLoadout.destination
            )
        } else if node.id == packageNodeID, !hasCollectedPackage {
            TRPackageMarkerView(size: packageBadgeSize)
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
            let validOutgoingEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
                for: node,
                hasCollectedPackage: hasCollectedPackage
            )
            SwitchNodeView(
                activeDirectionAngle: activeDirectionAngle,
                spriteSize: switchSpriteSize,
                ringSize: switchRingSize,
                optionCount: validOutgoingEdgeIDs.count,
                optionAngles: optionAngles(for: node, validOutgoingEdgeIDs: validOutgoingEdgeIDs),
                interactionState: interactionState(for: node),
                pressEventToken: pressedSwitchNodeID == node.id ? switchPressEventToken : nil,
                rejectionEventToken: rejectedSwitchNodeID == node.id ? switchRejectionEventToken : nil
            )
        } else {
            EmptyView()
        }
    }

    private func interactionState(for node: RuntimeRouteNode) -> SwitchNodeInteractionState {
        if node.id == eligibleSwitchNodeID { return .eligible }
        if node.id == upcomingSwitchNodeID { return .upcoming }
        if let currentEdgeID = deliveryDot?.currentEdgeID,
           runtimeGraph.edgesByID[currentEdgeID]?.fromNodeID == node.id {
            return .locked
        }
        return .inactive
    }

    private func activeDirectionAngle(for node: RuntimeRouteNode) -> Double? {
        SwitchArrowDirectionResolver.activeDirectionAngle(
            for: node,
            in: runtimeGraph,
            hasCollectedPackage: hasCollectedPackage
        )
    }

    private func optionAngles(for node: RuntimeRouteNode, validOutgoingEdgeIDs: [String]) -> [Double] {
        validOutgoingEdgeIDs.compactMap { edgeID in
            guard let edge = runtimeGraph.edgesByID[edgeID] else {
                return nil
            }
            return SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: runtimeGraph)
        }
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

    private func renderedRoadHubs(
        for runtimeGraph: RuntimeRouteGraph,
        layout: BoardLayout
    ) -> [RenderedRoadHub] {
        let incomingEdgesByNodeID = Dictionary(grouping: runtimeGraph.edgesByID.values, by: \.toNodeID)
        return runtimeGraph.nodesByID.values.compactMap { node in
            let validOutgoingEdgeIDs = runtimeGraph.validOutgoingEdgeIDs(for: node)
            guard validOutgoingEdgeIDs.count >= 3,
                  let point = layout.pointsByNodeID[node.id] else {
                return nil
            }

            let incomingEdges = incomingEdgesByNodeID[node.id] ?? []
            let outgoingEdges = validOutgoingEdgeIDs.compactMap { runtimeGraph.edgesByID[$0] }
            let directionCount = uniqueRouteDirectionCount(
                node: node,
                incomingEdges: incomingEdges,
                outgoingEdges: outgoingEdges,
                in: runtimeGraph
            )
            guard directionCount >= 3, directionCount <= 4 else {
                return nil
            }
            return RenderedRoadHub(id: node.id, point: point)
        }
        .sorted { $0.id < $1.id }
    }

    private func uniqueRouteDirectionCount(
        node: RuntimeRouteNode,
        incomingEdges: [RuntimeRouteEdge],
        outgoingEdges: [RuntimeRouteEdge],
        in runtimeGraph: RuntimeRouteGraph
    ) -> Int {
        let outgoingAngles = outgoingEdges.map {
            SwitchArrowDirectionResolver.directionAngle(for: $0, from: node, in: runtimeGraph)
        }
        let incomingAngles = incomingEdges.map { edge in
            SwitchArrowDirectionResolver.incomingDirectionAngle(for: edge, toward: node, in: runtimeGraph)
        }
        let directionBuckets = Set((outgoingAngles + incomingAngles).map(cardinalDirectionBucket(for:)))
        return directionBuckets.count
    }

    private func cardinalDirectionBucket(for angle: Double) -> Int {
        let twoPi = 2 * Double.pi
        let normalized = angle.truncatingRemainder(dividingBy: twoPi)
        let positiveAngle = normalized < 0 ? normalized + twoPi : normalized
        return Int((positiveAngle / (.pi / 2)).rounded()) % 4
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

struct LevelBoundingBox: Equatable {
    let minX: Double
    let maxX: Double
    let minY: Double
    let maxY: Double

    var width: Double {
        maxX - minX
    }

    var height: Double {
        maxY - minY
    }

    var center: RoadPoint {
        RoadPoint(x: (minX + maxX) / 2, y: (minY + maxY) / 2)
    }

    func expanded(by margin: Double) -> LevelBoundingBox {
        LevelBoundingBox(
            minX: minX - margin,
            maxX: maxX + margin,
            minY: minY - margin,
            maxY: maxY + margin
        )
    }
}

struct LevelPlayableExtents: Equatable {
    let nodeBounds: LevelBoundingBox
    let playableBounds: LevelBoundingBox
    let cameraSafeBounds: LevelBoundingBox
    let cameraSafeMargin: Double

    var levelWidth: Double {
        playableBounds.width
    }

    var levelHeight: Double {
        playableBounds.height
    }

    static func make(
        for runtimeGraph: RuntimeRouteGraph,
        cameraSafeMargin: Double = TRGameplayStyle.Metrics.cameraSafeMarginWorld
    ) -> LevelPlayableExtents {
        let nodePoints = runtimeGraph.nodesByID.values.map { RoadPoint(x: $0.x, y: $0.y) }
        var playablePoints = nodePoints
        for edge in runtimeGraph.edgesByID.values {
            playablePoints.append(contentsOf: sampledPoints(for: edge.roadPath))
        }

        let nodeBounds = bounds(containing: nodePoints)
        let playableBounds = bounds(containing: playablePoints)

        return LevelPlayableExtents(
            nodeBounds: nodeBounds,
            playableBounds: playableBounds,
            cameraSafeBounds: playableBounds.expanded(by: cameraSafeMargin),
            cameraSafeMargin: cameraSafeMargin
        )
    }

    private static func bounds(containing points: [RoadPoint]) -> LevelBoundingBox {
        guard let first = points.first else {
            return LevelBoundingBox(minX: 0, maxX: 0, minY: 0, maxY: 0)
        }

        var minX = first.x
        var maxX = first.x
        var minY = first.y
        var maxY = first.y
        for point in points.dropFirst() {
            minX = min(minX, point.x)
            maxX = max(maxX, point.x)
            minY = min(minY, point.y)
            maxY = max(maxY, point.y)
        }

        return LevelBoundingBox(minX: minX, maxX: maxX, minY: minY, maxY: maxY)
    }

    private static func sampledPoints(for roadPath: RoadPath, sampleCount: Int = 20) -> [RoadPoint] {
        guard sampleCount > 0 else {
            return []
        }
        return (0...sampleCount).map { index in
            roadPath.point(atProgress: Double(index) / Double(sampleCount))
        }
    }
}

struct LevelCameraPlan: Equatable {
    let scale: CGFloat
    let contentSize: CGSize
    let contentOffset: CGPoint
    let isTrackingEnabled: Bool
    let cameraCenter: RoadPoint

    var animationKey: String {
        [
            String(format: "%.3f", scale),
            String(format: "%.3f", contentOffset.x),
            String(format: "%.3f", contentOffset.y),
        ].joined(separator: ":")
    }

    static func make(
        extents: LevelPlayableExtents,
        viewportSize: CGSize,
        padding: CGFloat,
        mode: BoardCameraMode
    ) -> LevelCameraPlan {
        let bounds = extents.cameraSafeBounds
        let widthRange = max(bounds.width, 0)
        let heightRange = max(bounds.height, 0)
        let usableWidth = max(viewportSize.width - (padding * 2), BoardLayout.minimumUsableDimension)
        let usableHeight = max(viewportSize.height - (padding * 2), BoardLayout.minimumUsableDimension)
        let fitScale = scaleToFit(
            widthRange: widthRange,
            heightRange: heightRange,
            usableWidth: usableWidth,
            usableHeight: usableHeight
        )
        let scale = mode.usesReadableTrackingScale
            ? max(fitScale, TRGameplayStyle.Metrics.minimumReadableCoordinateScale)
            : fitScale
        let contentSize = CGSize(
            width: max(CGFloat(widthRange) * scale, BoardLayout.minimumUsableDimension),
            height: max(CGFloat(heightRange) * scale, BoardLayout.minimumUsableDimension)
        )
        let desiredCamera = mode.focusPoint ?? bounds.center
        let desiredContentOffset = CGPoint(
            x: (viewportSize.width / 2) - (CGFloat(desiredCamera.x - bounds.minX) * scale),
            y: (viewportSize.height / 2) - (CGFloat(bounds.maxY - desiredCamera.y) * scale)
        )
        let contentOffset = clampedOffset(
            desiredContentOffset,
            contentSize: contentSize,
            viewportSize: viewportSize
        )
        let resolvedCameraCenter = RoadPoint(
            x: bounds.minX + Double(((viewportSize.width / 2) - contentOffset.x) / scale),
            y: bounds.maxY - Double(((viewportSize.height / 2) - contentOffset.y) / scale)
        )

        return LevelCameraPlan(
            scale: scale,
            contentSize: contentSize,
            contentOffset: contentOffset,
            isTrackingEnabled: contentSize.width > viewportSize.width || contentSize.height > viewportSize.height,
            cameraCenter: resolvedCameraCenter
        )
    }

    private static func scaleToFit(
        widthRange: Double,
        heightRange: Double,
        usableWidth: CGFloat,
        usableHeight: CGFloat
    ) -> CGFloat {
        let hasHorizontalRange = widthRange > 0
        let hasVerticalRange = heightRange > 0

        switch (hasHorizontalRange, hasVerticalRange) {
        case (true, true):
            return min(usableWidth / CGFloat(widthRange), usableHeight / CGFloat(heightRange))
        case (true, false):
            return usableWidth / CGFloat(widthRange)
        case (false, true):
            return usableHeight / CGFloat(heightRange)
        case (false, false):
            return 1
        }
    }

    private static func clampedOffset(
        _ desiredOffset: CGPoint,
        contentSize: CGSize,
        viewportSize: CGSize
    ) -> CGPoint {
        CGPoint(
            x: clampedAxisOffset(desiredOffset.x, contentLength: contentSize.width, viewportLength: viewportSize.width),
            y: clampedAxisOffset(desiredOffset.y, contentLength: contentSize.height, viewportLength: viewportSize.height)
        )
    }

    private static func clampedAxisOffset(
        _ desiredOffset: CGFloat,
        contentLength: CGFloat,
        viewportLength: CGFloat
    ) -> CGFloat {
        guard contentLength > viewportLength else {
            return (viewportLength - contentLength) / 2
        }

        return min(0, max(viewportLength - contentLength, desiredOffset))
    }
}

enum BoardCameraMode: Equatable {
    case preview
    case follow(RoadPoint?)

    var focusPoint: RoadPoint? {
        switch self {
        case .preview:
            return nil
        case let .follow(point):
            return point
        }
    }

    var usesReadableTrackingScale: Bool {
        switch self {
        case .preview:
            return false
        case .follow:
            return true
        }
    }
}

struct SwitchArrowDirectionResolver {
    private static let vectorMagnitudeTolerance = 0.000_001

    static func activeDirectionAngle(
        for node: RuntimeRouteNode,
        in runtimeGraph: RuntimeRouteGraph,
        hasCollectedPackage: Bool = false
    ) -> Double? {
        let validOutgoingEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
            for: node,
            hasCollectedPackage: hasCollectedPackage
        )
        let switchKind = runtimeGraph.switchKind(
            for: node,
            hasCollectedPackage: hasCollectedPackage
        )

        guard switchKind.isSwitchable,
              let activeEdgeID = node.activeOutgoingEdgeID,
              validOutgoingEdgeIDs.contains(activeEdgeID),
              let activeEdge = runtimeGraph.edgesByID[activeEdgeID] else {
            return nil
        }

        return directionAngle(for: activeEdge, from: node, in: runtimeGraph)
    }

    static func directionAngle(for edge: RuntimeRouteEdge, from node: RuntimeRouteNode, in runtimeGraph: RuntimeRouteGraph) -> Double {
        // Switch arrows describe the rendered road exit direction. The target-node vector is only
        // a fallback for malformed or legacy edge data that cannot provide path geometry.
        if let roadPathAngle = directionAngleForRoadPathStart(edge.roadPath) {
            return roadPathAngle
        }

        if let targetNode = runtimeGraph.nodesByID[edge.toNodeID] {
            let fallbackVector = RoadVector(
                x: targetNode.x - node.x,
                y: targetNode.y - node.y
            )

            if hasUsableMagnitude(fallbackVector) {
                return snappedAxisAngle(for: fallbackVector)
            }
        }

        return 0
    }

    static func directionAngleForRoadPathStart(_ roadPath: RoadPath) -> Double? {
        let tangent = roadPath.tangent(atProgress: 0)
        guard hasUsableMagnitude(tangent) else {
            return nil
        }
        return snappedAxisAngle(for: tangent)
    }

    static func incomingDirectionAngle(
        for edge: RuntimeRouteEdge,
        toward node: RuntimeRouteNode,
        in runtimeGraph: RuntimeRouteGraph
    ) -> Double {
        let tangent = edge.roadPath.tangent(atProgress: 1)
        let incomingVector = RoadVector(x: -tangent.x, y: -tangent.y)

        if hasUsableMagnitude(incomingVector) {
            return snappedAxisAngle(for: incomingVector)
        }

        if let sourceNode = runtimeGraph.nodesByID[edge.fromNodeID] {
            let fallbackVector = RoadVector(
                x: sourceNode.x - node.x,
                y: sourceNode.y - node.y
            )

            if hasUsableMagnitude(fallbackVector) {
                return snappedAxisAngle(for: fallbackVector)
            }
        }

        return 0
    }

    private static func hasUsableMagnitude(_ vector: RoadVector) -> Bool {
        hypot(vector.x, vector.y) > vectorMagnitudeTolerance
    }

    private static func snappedAxisAngle(for vector: RoadVector) -> Double {
        if abs(vector.x) >= abs(vector.y) {
            return vector.x >= 0 ? 0 : .pi
        }

        return vector.y >= 0 ? -.pi / 2 : .pi / 2
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

private struct RenderedRoadHub: Identifiable {
    let id: String
    let point: CGPoint
}

struct RouteBoardTapTargetResolver {
    let runtimeGraph: RuntimeRouteGraph
    let layout: BoardLayout
    let tapRadius: CGFloat
    let hasCollectedPackage: Bool

    init(
        runtimeGraph: RuntimeRouteGraph,
        layout: BoardLayout,
        tapRadius: CGFloat = TRGameplayStyle.Metrics.switchTapTargetSize / 2,
        hasCollectedPackage: Bool = false
    ) {
        self.runtimeGraph = runtimeGraph
        self.layout = layout
        self.tapRadius = tapRadius
        self.hasCollectedPackage = hasCollectedPackage
    }

    func nodeID(at point: CGPoint) -> String? {
        let tapRadiusSquared = tapRadius * tapRadius

        return runtimeGraph.nodesByID.values
            .compactMap { node -> (nodeID: String, distanceSquared: CGFloat)? in
                guard runtimeGraph.switchKind(
                    for: node,
                    hasCollectedPackage: hasCollectedPackage
                ).isSwitchable,
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
    let extents: LevelPlayableExtents?
    let cameraPlan: LevelCameraPlan?
    private let minX: Double
    private let maxY: Double
    private let originX: CGFloat
    private let originY: CGFloat

    init(
        pointsByNodeID: [String: CGPoint],
        coordinateScale: CGFloat? = nil,
        extents: LevelPlayableExtents? = nil,
        cameraPlan: LevelCameraPlan? = nil,
        minX: Double = 0,
        maxY: Double = 0,
        originX: CGFloat = 0,
        originY: CGFloat = 0
    ) {
        self.pointsByNodeID = pointsByNodeID
        self.coordinateScale = coordinateScale
        self.extents = extents
        self.cameraPlan = cameraPlan
        self.minX = minX
        self.maxY = maxY
        self.originX = originX
        self.originY = originY
    }

    /// Ensures non-zero usable dimensions for board layout calculations.
    static let minimumUsableDimension: CGFloat = 1
    /// Multiplier used to compute circular spread radius for identical node coordinates.
    private static let degenerateLayoutSpreadFactor: CGFloat = 0.15

    var cameraAnimationKey: String {
        cameraPlan?.animationKey ?? "static"
    }

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

    static func make(
        for runtimeGraph: RuntimeRouteGraph,
        in size: CGSize,
        padding: CGFloat,
        cameraMode: BoardCameraMode
    ) -> BoardLayout {
        let nodes = runtimeGraph.nodesByID.values.sorted { $0.id < $1.id }
        guard !nodes.isEmpty else {
            return BoardLayout(pointsByNodeID: [:])
        }

        let extents = LevelPlayableExtents.make(for: runtimeGraph)
        let playableBounds = extents.playableBounds
        guard playableBounds.width > 0 || playableBounds.height > 0 else {
            return make(for: nodes, in: size, padding: padding)
        }

        let legacyLayout = make(for: nodes, in: size, padding: padding)
        if case .follow = cameraMode,
           let legacyScale = legacyLayout.coordinateScale,
           legacyScale >= TRGameplayStyle.Metrics.minimumReadableCoordinateScale,
           !requiresTrackingCamera(for: extents.cameraSafeBounds, in: size) {
            return legacyLayout
        }

        let cameraPlan = LevelCameraPlan.make(
            extents: extents,
            viewportSize: size,
            padding: padding,
            mode: cameraMode
        )
        let cameraBounds = extents.cameraSafeBounds
        var pointsByNodeID: [String: CGPoint] = [:]
        for node in nodes {
            pointsByNodeID[node.id] = CGPoint(
                x: cameraPlan.contentOffset.x + (CGFloat(node.x - cameraBounds.minX) * cameraPlan.scale),
                y: cameraPlan.contentOffset.y + (CGFloat(cameraBounds.maxY - node.y) * cameraPlan.scale)
            )
        }

        return BoardLayout(
            pointsByNodeID: pointsByNodeID,
            coordinateScale: cameraPlan.scale,
            extents: extents,
            cameraPlan: cameraPlan,
            minX: cameraBounds.minX,
            maxY: cameraBounds.maxY,
            originX: cameraPlan.contentOffset.x,
            originY: cameraPlan.contentOffset.y
        )
    }

    private static func requiresTrackingCamera(
        for bounds: LevelBoundingBox,
        in size: CGSize,
        readableScale: CGFloat = TRGameplayStyle.Metrics.minimumReadableCoordinateScale
    ) -> Bool {
        let readableWidth = CGFloat(max(bounds.width, 0)) * readableScale
        let readableHeight = CGFloat(max(bounds.height, 0)) * readableScale
        return readableWidth > size.width || readableHeight > size.height
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
