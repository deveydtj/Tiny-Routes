import Foundation

/// Describes how an edge should be converted into a standardized road path.
enum RoadShape: String, Codable {
    case horizontalFirst
    case verticalFirst
}

struct RoadPoint: Equatable {
    let x: Double
    let y: Double
}

struct RoadVector: Equatable {
    let x: Double
    let y: Double
}

enum RoadSegmentKind: Equatable {
    case straight
    case quarterTurn
}

struct RoadSegment: Equatable {
    let kind: RoadSegmentKind
    let start: RoadPoint
    let end: RoadPoint
    let center: RoadPoint?
    let radius: Double
    let startAngle: Double
    let signedAngleDelta: Double

    var length: Double {
        switch kind {
        case .straight:
            return hypot(end.x - start.x, end.y - start.y)
        case .quarterTurn:
            return abs(signedAngleDelta) * radius
        }
    }

    func point(atDistance distance: Double) -> RoadPoint {
        let clampedDistance = max(0, min(distance, length))

        switch kind {
        case .straight:
            guard length > 0 else {
                return end
            }
            let progress = clampedDistance / length
            return RoadPoint(
                x: start.x + ((end.x - start.x) * progress),
                y: start.y + ((end.y - start.y) * progress)
            )
        case .quarterTurn:
            guard let center, radius > 0, length > 0 else {
                return end
            }
            let progress = clampedDistance / length
            let angle = startAngle + (signedAngleDelta * progress)
            return RoadPoint(
                x: center.x + (cos(angle) * radius),
                y: center.y + (sin(angle) * radius)
            )
        }
    }

    func tangent(atDistance distance: Double) -> RoadVector {
        switch kind {
        case .straight:
            let dx = end.x - start.x
            let dy = end.y - start.y
            let magnitude = hypot(dx, dy)
            guard magnitude > 0 else {
                return RoadVector(x: 0, y: 0)
            }
            return RoadVector(x: dx / magnitude, y: dy / magnitude)
        case .quarterTurn:
            let clampedDistance = max(0, min(distance, length))
            let progress = length > 0 ? clampedDistance / length : 0
            let angle = startAngle + (signedAngleDelta * progress)
            let turnSign = signedAngleDelta >= 0 ? 1.0 : -1.0
            return RoadVector(x: -sin(angle) * turnSign, y: cos(angle) * turnSign)
        }
    }
}

struct RoadPath: Equatable {
    static let standardTurnRadius: Double = 0.18

    let segments: [RoadSegment]

    var totalLength: Double {
        segments.reduce(0) { $0 + $1.length }
    }

    static func make(from start: RoadPoint, to end: RoadPoint, shape: RoadShape? = nil) -> RoadPath {
        let dx = end.x - start.x
        let dy = end.y - start.y

        guard dx != 0, dy != 0 else {
            return RoadPath(segments: [
                RoadSegment(
                    kind: .straight,
                    start: start,
                    end: end,
                    center: nil,
                    radius: 0,
                    startAngle: 0,
                    signedAngleDelta: 0
                )
            ])
        }

        let turnRadius = min(standardTurnRadius, abs(dx) / 2, abs(dy) / 2)
        guard turnRadius > 0 else {
            return RoadPath(segments: [])
        }

        switch shape ?? .horizontalFirst {
        case .horizontalFirst:
            return makeHorizontalFirstPath(from: start, to: end, turnRadius: turnRadius)
        case .verticalFirst:
            return makeVerticalFirstPath(from: start, to: end, turnRadius: turnRadius)
        }
    }

    func point(atProgress progress: Double) -> RoadPoint {
        point(atDistance: max(0, min(progress, 1)) * totalLength)
    }

    func tangent(atProgress progress: Double) -> RoadVector {
        tangent(atDistance: max(0, min(progress, 1)) * totalLength)
    }

    func point(atDistance distance: Double) -> RoadPoint {
        guard let firstSegment = segments.first else {
            return RoadPoint(x: 0, y: 0)
        }

        var remainingDistance = max(0, min(distance, totalLength))
        for segment in segments {
            if remainingDistance <= segment.length {
                return segment.point(atDistance: remainingDistance)
            }
            remainingDistance -= segment.length
        }

        return segments.last?.end ?? firstSegment.start
    }

    func tangent(atDistance distance: Double) -> RoadVector {
        guard !segments.isEmpty else {
            return RoadVector(x: 0, y: 0)
        }

        var remainingDistance = max(0, min(distance, totalLength))
        for segment in segments {
            if remainingDistance <= segment.length {
                return segment.tangent(atDistance: remainingDistance)
            }
            remainingDistance -= segment.length
        }

        return segments.last?.tangent(atDistance: segments.last?.length ?? 0) ?? RoadVector(x: 0, y: 0)
    }

    private static func makeHorizontalFirstPath(from start: RoadPoint, to end: RoadPoint, turnRadius: Double) -> RoadPath {
        let xDirection = end.x > start.x ? 1.0 : -1.0
        let yDirection = end.y > start.y ? 1.0 : -1.0
        let corner = RoadPoint(x: end.x, y: start.y)
        let arcStart = RoadPoint(x: corner.x - (xDirection * turnRadius), y: start.y)
        let arcEnd = RoadPoint(x: corner.x, y: start.y + (yDirection * turnRadius))
        let center = RoadPoint(x: arcStart.x, y: arcEnd.y)
        let startAngle = yDirection > 0 ? -Double.pi / 2 : Double.pi / 2
        let signedAngleDelta = xDirection * yDirection * Double.pi / 2

        return RoadPath(segments: [
            straightSegment(from: start, to: arcStart),
            RoadSegment(
                kind: .quarterTurn,
                start: arcStart,
                end: arcEnd,
                center: center,
                radius: turnRadius,
                startAngle: startAngle,
                signedAngleDelta: signedAngleDelta
            ),
            straightSegment(from: arcEnd, to: end)
        ])
    }

    private static func makeVerticalFirstPath(from start: RoadPoint, to end: RoadPoint, turnRadius: Double) -> RoadPath {
        let xDirection = end.x > start.x ? 1.0 : -1.0
        let yDirection = end.y > start.y ? 1.0 : -1.0
        let corner = RoadPoint(x: start.x, y: end.y)
        let arcStart = RoadPoint(x: start.x, y: corner.y - (yDirection * turnRadius))
        let arcEnd = RoadPoint(x: start.x + (xDirection * turnRadius), y: corner.y)
        let center = RoadPoint(x: arcEnd.x, y: arcStart.y)
        let startAngle = xDirection > 0 ? Double.pi : 0
        let signedAngleDelta = -xDirection * yDirection * Double.pi / 2

        return RoadPath(segments: [
            straightSegment(from: start, to: arcStart),
            RoadSegment(
                kind: .quarterTurn,
                start: arcStart,
                end: arcEnd,
                center: center,
                radius: turnRadius,
                startAngle: startAngle,
                signedAngleDelta: signedAngleDelta
            ),
            straightSegment(from: arcEnd, to: end)
        ])
    }

    private static func straightSegment(from start: RoadPoint, to end: RoadPoint) -> RoadSegment {
        RoadSegment(
            kind: .straight,
            start: start,
            end: end,
            center: nil,
            radius: 0,
            startAngle: 0,
            signedAngleDelta: 0
        )
    }
}

/// Represents a directed connection from one route node to another.
struct RouteEdge: Identifiable, Codable {
    let id: String
    let fromNodeID: String
    let toNodeID: String
    var roadShape: RoadShape?

    init(id: String, fromNodeID: String, toNodeID: String, roadShape: RoadShape? = nil) {
        self.id = id
        self.fromNodeID = fromNodeID
        self.toNodeID = toNodeID
        self.roadShape = roadShape
    }
}
