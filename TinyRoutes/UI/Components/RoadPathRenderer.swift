import SwiftUI

enum RoadPathRenderer {
    static func path(for edge: RuntimeRouteEdge, layout: BoardLayout) -> Path {
        path(for: edge.roadPath, layout: layout)
    }

    static func path(for roadPath: RoadPath, layout: BoardLayout) -> Path {
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

/// Derived drawing data only; routes and their endings still come from the engine.
struct MultiVanPreviewDrawing {
    let path: Path
    let endpoint: CGPoint?
    let color: VanColor
    let ending: MultiVanPreviewEnding
    let indicatorSlot: Int?

    static func laneOffsets(routes: [MultiVanPreviewRoute]) -> [[String: CGFloat]] {
        var users: [String: [Int]] = [:]
        for (index, route) in routes.enumerated() {
            // A looping route occupies one lane, however often it visits the edge.
            for edgeID in Set(route.edgeIDs) {
                users[edgeID, default: []].append(index)
            }
        }
        var offsets = Array(repeating: [String: CGFloat](), count: routes.count)
        for (edgeID, indices) in users {
            // Indices were appended in authored van order, never dictionary order.
            for (lane, index) in indices.enumerated() {
                offsets[index][edgeID] = (CGFloat(lane) - CGFloat(indices.count - 1) / 2) * 4
            }
        }
        return offsets
    }

    static func offsetPoint(
        on road: RoadPath, at distance: Double, offset: CGFloat, layout: BoardLayout
    ) -> CGPoint? {
        guard let point = layout.point(for: road.point(atDistance: distance)) else { return nil }
        let tangent = road.tangent(atDistance: distance)
        let magnitude = hypot(tangent.x, tangent.y)
        guard magnitude.isFinite, magnitude > 1e-9 else { return point }
        // MV-12 flips world Y. Rotate the projected tangent to get a screen normal.
        return CGPoint(x: point.x + CGFloat(tangent.y / magnitude) * offset,
                       y: point.y + CGFloat(tangent.x / magnitude) * offset)
    }

    static func offsetPath(for road: RoadPath, offset: CGFloat, layout: BoardLayout) -> Path {
        guard offset != 0 else { return RoadPathRenderer.path(for: road, layout: layout) }
        return Path { path in
            guard let scale = layout.coordinateScale, scale > 0,
                  !road.segments.isEmpty,
                  let start = offsetPoint(on: road, at: 0, offset: offset, layout: layout) else { return }
            path.move(to: start)
            var distance = 0.0
            for segment in road.segments {
                let length = segment.length
                // At most 3 screen points per step, with extra samples on small turns.
                let turnSteps: Int
                switch segment.kind {
                case .straight: turnSteps = 1
                case .quarterTurn: turnSteps = Int(ceil(abs(segment.signedAngleDelta) / (.pi / 16)))
                case .smoothTurn: turnSteps = 16
                }
                let steps = max(1, turnSteps, Int(ceil(length * Double(scale) / 3)))
                for step in 1...steps {
                    let sampleDistance = distance + length * Double(step) / Double(steps)
                    if let point = offsetPoint(on: road, at: sampleDistance, offset: offset, layout: layout) {
                        path.addLine(to: point)
                    }
                }
                distance += length
            }
        }
    }

    static func make(
        routes: [MultiVanPreviewRoute], vans: [MultiVanVan],
        graph: RuntimeRouteGraph, layout: BoardLayout
    ) -> [Self] {
        let offsets = laneOffsets(routes: routes)
        let terminalIDs = zip(vans, routes).map { van, route in
            route.edgeIDs.last.flatMap { graph.edgesByID[$0]?.toNodeID } ?? van.startNodeID
        }
        return zip(vans, routes).enumerated().map { index, pair in
            let (van, route) = pair
            var path = Path()
            var endpoint = layout.pointsByNodeID[van.startNodeID]
            for edgeID in route.edgeIDs {
                guard let edge = graph.edgesByID[edgeID] else { continue }
                let offset = offsets[index][edgeID] ?? 0
                // Each edge starts a new subpath: no diagonal joins between lanes.
                path.addPath(offsetPath(for: edge.roadPath, offset: offset, layout: layout))
                if !edge.roadPath.segments.isEmpty {
                    endpoint = offsetPoint(on: edge.roadPath, at: edge.roadPath.totalLength,
                                           offset: offset, layout: layout)
                } else {
                    endpoint = layout.pointsByNodeID[edge.toNodeID]
                }
            }
            let peers = terminalIDs.indices.filter { terminalIDs[$0] == terminalIDs[index] }
            return Self(path: path, endpoint: endpoint, color: van.color, ending: route.ending,
                        indicatorSlot: peers.count > 1 ? peers.firstIndex(of: index) : nil)
        }
    }
}
