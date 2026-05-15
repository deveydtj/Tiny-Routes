import SwiftUI

struct GameplayScreen: View {
    let levelID: String
    let isPaused: Bool
    let onPauseResumeTapped: () -> Void
    let onCompleteTapped: () -> Void
    let onFailTapped: () -> Void
    let onExitTapped: () -> Void

    private let levelRepository: LevelRepository
    private let routeEngine: RouteEngine
    private let frameTimer = Timer.publish(every: 1.0 / 60.0, on: .main, in: .common).autoconnect()

    @State private var runtimeGraph: RuntimeRouteGraph?
    @State private var deliveryDot: DeliveryDot?
    @State private var packageNodeID: String = ""
    @State private var destinationNodeID: String = ""
    @State private var loadErrorMessage: String?
    @State private var lastFrameDate: Date?

    init(
        levelID: String,
        isPaused: Bool,
        onPauseResumeTapped: @escaping () -> Void,
        onCompleteTapped: @escaping () -> Void,
        onFailTapped: @escaping () -> Void,
        onExitTapped: @escaping () -> Void,
        levelRepository: LevelRepository = LevelRepository(),
        routeEngine: RouteEngine = RouteEngine()
    ) {
        self.levelID = levelID
        self.isPaused = isPaused
        self.onPauseResumeTapped = onPauseResumeTapped
        self.onCompleteTapped = onCompleteTapped
        self.onFailTapped = onFailTapped
        self.onExitTapped = onExitTapped
        self.levelRepository = levelRepository
        self.routeEngine = routeEngine
    }

    var body: some View {
        VStack(spacing: 16) {
            Text("Level: \(levelID)")
                .font(.headline)
            Text(isPaused ? "Paused" : "Running")
                .foregroundColor(isPaused ? .orange : .green)

            Group {
                if let loadErrorMessage {
                    Text(loadErrorMessage)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                } else if let runtimeGraph {
                    RouteBoardView(
                        runtimeGraph: runtimeGraph,
                        deliveryDot: deliveryDot,
                        packageNodeID: packageNodeID,
                        destinationNodeID: destinationNodeID
                    )
                } else {
                    ProgressView("Loading board…")
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.vertical, 8)

            VStack(spacing: 10) {
                Button(isPaused ? "Resume" : "Pause", action: onPauseResumeTapped)
                Button("Simulate Level Complete", action: onCompleteTapped)
                Button("Simulate Level Failed", action: onFailTapped)
                Button("Exit to Menu", action: onExitTapped)
            }
        }
        .task(id: levelID) {
            loadBoard()
        }
        .onReceive(frameTimer) { frameDate in
            advanceDot(at: frameDate)
        }
        .onChange(of: isPaused) { paused in
            if paused {
                lastFrameDate = nil
            }
        }
    }

    private func loadBoard() {
        loadErrorMessage = nil
        runtimeGraph = nil
        deliveryDot = nil
        lastFrameDate = nil

        do {
            let levelData = try levelRepository.loadLevel(id: levelID)
            try routeEngine.buildGraph(from: levelData)
            _ = routeEngine.startDotMovement()

            runtimeGraph = routeEngine.runtimeGraph
            deliveryDot = routeEngine.deliveryDot
            packageNodeID = levelData.packageNodeID
            destinationNodeID = levelData.destinationNodeID
        } catch {
            loadErrorMessage = error.localizedDescription
        }
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
            return
        }

        routeEngine.updateDot(deltaTime: deltaTime)
        deliveryDot = routeEngine.deliveryDot
    }
}

private struct RouteBoardView: View {
    let runtimeGraph: RuntimeRouteGraph
    let deliveryDot: DeliveryDot?
    let packageNodeID: String
    let destinationNodeID: String

    private let edgeStrokeColor = Color.blue.opacity(0.7)
    private let nodeFillColor = Color.white
    private let nodeBorderColor = Color.blue
    private let deliveryDotColor = Color.purple
    private let boardPadding: CGFloat = 20
    private let nodeSize: CGFloat = 22
    private let specialNodeSize: CGFloat = 30
    private let deliveryDotSize: CGFloat = 18
    private let edgeWidth: CGFloat = 8

    var body: some View {
        GeometryReader { geometry in
            let nodes = runtimeGraph.nodesByID.values.sorted { $0.id < $1.id }
            let edges = runtimeGraph.edgesByID.values.sorted { $0.id < $1.id }
            let layout = BoardLayout.make(
                for: nodes,
                in: geometry.size,
                padding: boardPadding
            )

            ZStack {
                ForEach(edges, id: \.id) { edge in
                    if let fromPoint = layout.pointsByNodeID[edge.fromNodeID],
                       let toPoint = layout.pointsByNodeID[edge.toNodeID] {
                        Path { path in
                            path.move(to: fromPoint)
                            path.addLine(to: toPoint)
                        }
                        .stroke(
                            edgeStrokeColor,
                            style: StrokeStyle(
                                lineWidth: edgeWidth,
                                lineCap: .round,
                                lineJoin: .round
                            )
                        )
                    }
                }

                ForEach(nodes, id: \.id) { node in
                    if let nodePoint = layout.pointsByNodeID[node.id] {
                        nodeView(for: node.id)
                            .position(nodePoint)
                    }
                }

                if let deliveryDotPoint = deliveryDotPoint(in: layout) {
                    Circle()
                        .fill(deliveryDotColor)
                        .overlay(
                            Circle()
                                .stroke(Color.white.opacity(0.9), lineWidth: 2)
                        )
                        .frame(width: deliveryDotSize, height: deliveryDotSize)
                        .shadow(color: deliveryDotColor.opacity(0.35), radius: 6, x: 0, y: 2)
                        .position(deliveryDotPoint)
                }
            }
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
    }

    @ViewBuilder
    private func nodeView(for nodeID: String) -> some View {
        if nodeID == packageNodeID {
            Circle()
                .fill(Color.orange.opacity(0.9))
                .overlay(
                    Text("📦")
                        .font(.system(size: 16))
                )
                .overlay(
                    Circle()
                        .stroke(Color.orange, lineWidth: 2)
                )
                .frame(width: specialNodeSize, height: specialNodeSize)
        } else if nodeID == destinationNodeID {
            Circle()
                .fill(Color.green.opacity(0.9))
                .overlay(
                    Image(systemName: "flag.checkered")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(.white)
                )
                .overlay(
                    Circle()
                        .stroke(Color.green, lineWidth: 2)
                )
                .frame(width: specialNodeSize, height: specialNodeSize)
        } else {
            Circle()
                .fill(nodeFillColor)
                .overlay(
                    Circle()
                        .stroke(nodeBorderColor, lineWidth: 2)
                )
                .frame(width: nodeSize, height: nodeSize)
        }
    }

    private func deliveryDotPoint(in layout: BoardLayout) -> CGPoint? {
        guard let deliveryDot else {
            return nil
        }

        if let currentEdgeID = deliveryDot.currentEdgeID,
           let edge = runtimeGraph.edgesByID[currentEdgeID],
           let fromPoint = layout.pointsByNodeID[edge.fromNodeID],
           let toPoint = layout.pointsByNodeID[edge.toNodeID] {
            let clampedProgress = max(0, min(deliveryDot.progressAlongEdge, 1))
            return CGPoint(
                x: fromPoint.x + ((toPoint.x - fromPoint.x) * clampedProgress),
                y: fromPoint.y + ((toPoint.y - fromPoint.y) * clampedProgress)
            )
        }

        return layout.pointsByNodeID[deliveryDot.currentNodeID]
    }
}

private struct BoardLayout {
    let pointsByNodeID: [String: CGPoint]
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

        return BoardLayout(pointsByNodeID: pointsByNodeID)
    }
}

#Preview {
    GameplayScreen(
        levelID: "level_001",
        isPaused: false,
        onPauseResumeTapped: {},
        onCompleteTapped: {},
        onFailTapped: {},
        onExitTapped: {}
    )
}
