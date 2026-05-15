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

    @State private var runtimeGraph: RuntimeRouteGraph?
    @State private var packageNodeID: String = ""
    @State private var destinationNodeID: String = ""
    @State private var loadErrorMessage: String?

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
    }

    private func loadBoard() {
        loadErrorMessage = nil
        runtimeGraph = nil

        do {
            let levelData = try levelRepository.loadLevel(id: levelID)
            try routeEngine.buildGraph(from: levelData)

            runtimeGraph = routeEngine.runtimeGraph
            packageNodeID = levelData.packageNodeID
            destinationNodeID = levelData.destinationNodeID
        } catch {
            loadErrorMessage = error.localizedDescription
        }
    }
}

private struct RouteBoardView: View {
    let runtimeGraph: RuntimeRouteGraph
    let packageNodeID: String
    let destinationNodeID: String

    private let edgeStrokeColor = Color.blue.opacity(0.7)
    private let nodeFillColor = Color.white
    private let nodeBorderColor = Color.blue
    private let boardPadding: CGFloat = 20
    private let nodeSize: CGFloat = 22
    private let specialNodeSize: CGFloat = 30
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
}

private struct BoardLayout {
    let pointsByNodeID: [String: CGPoint]
    private static let fallbackCenterRatio: CGFloat = 0.5

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

        let usableWidth = max(size.width - (padding * 2), 1)
        let usableHeight = max(size.height - (padding * 2), 1)

        if widthRange == 0, heightRange == 0 {
            let centerPoint = CGPoint(x: size.width / 2, y: size.height / 2)
            var pointsByNodeID: [String: CGPoint] = [:]
            for node in nodes {
                pointsByNodeID[node.id] = centerPoint
            }
            return BoardLayout(pointsByNodeID: pointsByNodeID)
        }

        let horizontalScale = widthRange > 0 ? usableWidth / widthRange : 1
        let verticalScale = heightRange > 0 ? usableHeight / heightRange : 1
        let scale = min(horizontalScale, verticalScale)

        let boardWidth = widthRange * scale
        let boardHeight = heightRange * scale
        let originX = (size.width - boardWidth) / 2
        let originY = (size.height - boardHeight) / 2

        var pointsByNodeID: [String: CGPoint] = [:]
        for node in nodes {
            let normalizedX = widthRange > 0 ? (node.x - minX) / widthRange : fallbackCenterRatio
            let normalizedY = heightRange > 0 ? (maxY - node.y) / heightRange : fallbackCenterRatio

            let x = originX + (normalizedX * boardWidth)
            let y = originY + (normalizedY * boardHeight)

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
