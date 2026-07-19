import Foundation

/// Describes how an edge should be converted into a standardized road path.
enum RoadShape: String, Codable {
    case horizontalFirst
    case verticalFirst
}

/// Controls whether a road can be selected before or after package collection.
enum RoadAvailability: String, Codable, CaseIterable {
    case always
    case beforePackage
    case afterPackage

    func isAvailable(hasCollectedPackage: Bool) -> Bool {
        switch self {
        case .always:
            return true
        case .beforePackage:
            return !hasCollectedPackage
        case .afterPackage:
            return hasCollectedPackage
        }
    }
}

/// A schema-3 road condition expressed only in ordered-objective state.
struct EdgeAvailabilityRule: Codable, Equatable {
    var requiredCompletedObjectiveIDs: [String]
    var forbiddenCompletedObjectiveIDs: [String]
    var minimumObjectiveIndex: Int?
    var maximumObjectiveIndex: Int?
    var usageLimit: Int?

    init(
        requiredCompletedObjectiveIDs: [String] = [],
        forbiddenCompletedObjectiveIDs: [String] = [],
        minimumObjectiveIndex: Int? = nil,
        maximumObjectiveIndex: Int? = nil,
        usageLimit: Int? = nil
    ) {
        self.requiredCompletedObjectiveIDs = requiredCompletedObjectiveIDs
        self.forbiddenCompletedObjectiveIDs = forbiddenCompletedObjectiveIDs
        self.minimumObjectiveIndex = minimumObjectiveIndex
        self.maximumObjectiveIndex = maximumObjectiveIndex
        self.usageLimit = usageLimit
    }

    static func adapting(
        _ legacyAvailability: RoadAvailability,
        packageObjectiveID: String = RouteObjective.legacyPickupID
    ) -> EdgeAvailabilityRule {
        switch legacyAvailability {
        case .always:
            return EdgeAvailabilityRule()
        case .beforePackage:
            return EdgeAvailabilityRule(
                forbiddenCompletedObjectiveIDs: [packageObjectiveID]
            )
        case .afterPackage:
            return EdgeAvailabilityRule(
                requiredCompletedObjectiveIDs: [packageObjectiveID]
            )
        }
    }
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
    case smoothTurn
}

struct RoadSegment: Equatable {
    let kind: RoadSegmentKind
    let start: RoadPoint
    let end: RoadPoint
    let center: RoadPoint?
    let control1: RoadPoint?
    let control2: RoadPoint?
    let radius: Double
    let startAngle: Double
    let signedAngleDelta: Double

    var length: Double {
        switch kind {
        case .straight:
            return hypot(end.x - start.x, end.y - start.y)
        case .quarterTurn:
            return abs(signedAngleDelta) * radius
        case .smoothTurn:
            return approximateCubicLength()
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
        case .smoothTurn:
            guard length > 0 else {
                return end
            }
            return cubicPoint(at: clampedDistance / length)
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
        case .smoothTurn:
            let segmentLength = length
            guard segmentLength > 0,
                  let control1,
                  let control2 else {
                return straightTangent()
            }

            let progress = max(0, min(distance, segmentLength)) / segmentLength
            let inverseProgress = 1 - progress
            let dx = (3 * inverseProgress * inverseProgress * (control1.x - start.x))
                + (6 * inverseProgress * progress * (control2.x - control1.x))
                + (3 * progress * progress * (end.x - control2.x))
            let dy = (3 * inverseProgress * inverseProgress * (control1.y - start.y))
                + (6 * inverseProgress * progress * (control2.y - control1.y))
                + (3 * progress * progress * (end.y - control2.y))
            let magnitude = hypot(dx, dy)
            guard magnitude > 0 else {
                return straightTangent()
            }
            return RoadVector(x: dx / magnitude, y: dy / magnitude)
        }
    }

    func trimmed(fromDistance startDistance: Double, toDistance endDistance: Double) -> RoadSegment? {
        let segmentLength = length
        let trimmedStartDistance = max(0, min(startDistance, segmentLength))
        let trimmedEndDistance = max(0, min(endDistance, segmentLength))
        guard trimmedStartDistance < trimmedEndDistance else {
            return nil
        }

        switch kind {
        case .straight:
            return RoadPath.straightSegment(
                from: point(atDistance: trimmedStartDistance),
                to: point(atDistance: trimmedEndDistance)
            )
        case .quarterTurn:
            guard segmentLength > 0 else {
                return nil
            }
            let startProgress = trimmedStartDistance / segmentLength
            let endProgress = trimmedEndDistance / segmentLength
            let updatedStartAngle = startAngle + (signedAngleDelta * startProgress)
            return RoadSegment(
                kind: .quarterTurn,
                start: point(atDistance: trimmedStartDistance),
                end: point(atDistance: trimmedEndDistance),
                center: center,
                control1: nil,
                control2: nil,
                radius: radius,
                startAngle: updatedStartAngle,
                signedAngleDelta: signedAngleDelta * (endProgress - startProgress)
            )
        case .smoothTurn:
            guard segmentLength > 0 else {
                return nil
            }
            let startProgress = trimmedStartDistance / segmentLength
            let endProgress = trimmedEndDistance / segmentLength
            return cubicSubsegment(fromProgress: startProgress, toProgress: endProgress)
        }
    }

    private func straightTangent() -> RoadVector {
        let dx = end.x - start.x
        let dy = end.y - start.y
        let magnitude = hypot(dx, dy)
        guard magnitude > 0 else {
            return RoadVector(x: 0, y: 0)
        }
        return RoadVector(x: dx / magnitude, y: dy / magnitude)
    }

    private func cubicPoint(at progress: Double) -> RoadPoint {
        guard let control1,
              let control2 else {
            return pointOnStraight(at: progress)
        }

        let t = max(0, min(progress, 1))
        let inverseT = 1 - t
        let startWeight = inverseT * inverseT * inverseT
        let control1Weight = 3 * inverseT * inverseT * t
        let control2Weight = 3 * inverseT * t * t
        let endWeight = t * t * t

        return RoadPoint(
            x: (start.x * startWeight) + (control1.x * control1Weight) + (control2.x * control2Weight) + (end.x * endWeight),
            y: (start.y * startWeight) + (control1.y * control1Weight) + (control2.y * control2Weight) + (end.y * endWeight)
        )
    }

    private func pointOnStraight(at progress: Double) -> RoadPoint {
        let t = max(0, min(progress, 1))
        return RoadPoint(
            x: start.x + ((end.x - start.x) * t),
            y: start.y + ((end.y - start.y) * t)
        )
    }

    private func approximateCubicLength(sampleCount: Int = 12) -> Double {
        var total = 0.0
        var previous = start

        for index in 1...sampleCount {
            let point = cubicPoint(at: Double(index) / Double(sampleCount))
            total += hypot(point.x - previous.x, point.y - previous.y)
            previous = point
        }

        return total
    }

    private func cubicSubsegment(fromProgress startProgress: Double, toProgress endProgress: Double) -> RoadSegment? {
        guard let control1,
              let control2 else {
            return RoadPath.straightSegment(
                from: pointOnStraight(at: startProgress),
                to: pointOnStraight(at: endProgress)
            )
        }

        let clampedStart = max(0, min(startProgress, 1))
        let clampedEnd = max(0, min(endProgress, 1))
        guard clampedStart < clampedEnd else {
            return nil
        }

        let points = (start, control1, control2, end)
        let rightSide: (RoadPoint, RoadPoint, RoadPoint, RoadPoint)
        if clampedStart > 0 {
            rightSide = splitCubic(points, at: clampedStart).right
        } else {
            rightSide = points
        }

        let relativeEnd = clampedStart > 0
            ? (clampedEnd - clampedStart) / (1 - clampedStart)
            : clampedEnd
        let subcurve = relativeEnd < 1 ? splitCubic(rightSide, at: relativeEnd).left : rightSide

        return RoadPath.smoothTurnSegment(
            from: subcurve.0,
            control1: subcurve.1,
            control2: subcurve.2,
            to: subcurve.3
        )
    }

    private func splitCubic(
        _ points: (RoadPoint, RoadPoint, RoadPoint, RoadPoint),
        at progress: Double
    ) -> (
        left: (RoadPoint, RoadPoint, RoadPoint, RoadPoint),
        right: (RoadPoint, RoadPoint, RoadPoint, RoadPoint)
    ) {
        let t = max(0, min(progress, 1))
        let p01 = interpolate(from: points.0, to: points.1, progress: t)
        let p12 = interpolate(from: points.1, to: points.2, progress: t)
        let p23 = interpolate(from: points.2, to: points.3, progress: t)
        let p012 = interpolate(from: p01, to: p12, progress: t)
        let p123 = interpolate(from: p12, to: p23, progress: t)
        let p0123 = interpolate(from: p012, to: p123, progress: t)

        return (
            left: (points.0, p01, p012, p0123),
            right: (p0123, p123, p23, points.3)
        )
    }

    private func interpolate(from start: RoadPoint, to end: RoadPoint, progress: Double) -> RoadPoint {
        RoadPoint(
            x: start.x + ((end.x - start.x) * progress),
            y: start.y + ((end.y - start.y) * progress)
        )
    }
}

struct RoadPath: Equatable {
    static let standardTurnRadius: Double = 0.18

    let segments: [RoadSegment]

    struct PerpendicularConnector: Equatable {
        let roadPath: RoadPath
        let entryDistanceAlongIncomingPath: Double
        let exitDistanceAlongOutgoingPath: Double
    }

    var totalLength: Double {
        segments.reduce(0) { $0 + $1.length }
    }

    static func make(from start: RoadPoint, to end: RoadPoint, shape: RoadShape? = nil) -> RoadPath {
        let dx = end.x - start.x
        let dy = end.y - start.y

        guard dx != 0, dy != 0 else {
            return RoadPath(segments: [
                straightSegment(from: start, to: end)
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

    static func makePerpendicularConnector(
        at _: RoadPoint,
        from incomingPath: RoadPath,
        to outgoingPath: RoadPath,
        maxTrimDistance: Double = standardTurnRadius
    ) -> PerpendicularConnector? {
        let incomingLength = incomingPath.totalLength
        let outgoingLength = outgoingPath.totalLength
        guard incomingLength > 0, outgoingLength > 0 else {
            return nil
        }

        let trimDistance = min(maxTrimDistance, incomingLength / 2, outgoingLength / 2)
        guard trimDistance > 0 else {
            return nil
        }

        let entryDistanceAlongIncomingPath = incomingLength - trimDistance
        let exitDistanceAlongOutgoingPath = trimDistance
        let incoming = incomingPath.tangent(atDistance: entryDistanceAlongIncomingPath)
        let outgoing = outgoingPath.tangent(atDistance: exitDistanceAlongOutgoingPath)
        let dotProduct = (incoming.x * outgoing.x) + (incoming.y * outgoing.y)
        let crossProduct = (incoming.x * outgoing.y) - (incoming.y * outgoing.x)

        guard abs(dotProduct) < 0.35,
              abs(crossProduct) > 0.7 else {
            return nil
        }

        let start = incomingPath.point(atDistance: entryDistanceAlongIncomingPath)
        let end = outgoingPath.point(atDistance: exitDistanceAlongOutgoingPath)
        let chordLength = hypot(end.x - start.x, end.y - start.y)
        guard chordLength > 0 else {
            return nil
        }

        let controlDistance = min(trimDistance * 0.552_284_749_8, chordLength * 0.6)
        let control1 = RoadPoint(
            x: start.x + (incoming.x * controlDistance),
            y: start.y + (incoming.y * controlDistance)
        )
        let control2 = RoadPoint(
            x: end.x - (outgoing.x * controlDistance),
            y: end.y - (outgoing.y * controlDistance)
        )

        return PerpendicularConnector(
            roadPath: RoadPath(segments: [
                smoothTurnSegment(
                    from: start,
                    control1: control1,
                    control2: control2,
                    to: end
                )
            ]),
            entryDistanceAlongIncomingPath: entryDistanceAlongIncomingPath,
            exitDistanceAlongOutgoingPath: exitDistanceAlongOutgoingPath
        )
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

    func trimmed(fromDistance startDistance: Double, toDistance endDistance: Double) -> RoadPath {
        let clampedStart = max(0, min(startDistance, totalLength))
        let clampedEnd = max(0, min(endDistance, totalLength))
        guard clampedStart < clampedEnd else {
            return RoadPath(segments: [])
        }

        var trimmedSegments: [RoadSegment] = []
        var traversedDistance = 0.0

        for segment in segments {
            let segmentLength = segment.length
            let segmentStartDistance = max(0, clampedStart - traversedDistance)
            let segmentEndDistance = min(segmentLength, clampedEnd - traversedDistance)

            if segmentStartDistance < segmentEndDistance,
               let trimmedSegment = segment.trimmed(
                fromDistance: segmentStartDistance,
                toDistance: segmentEndDistance
               ) {
                trimmedSegments.append(trimmedSegment)
            }

            traversedDistance += segmentLength
            if traversedDistance >= clampedEnd {
                break
            }
        }

        return RoadPath(segments: trimmedSegments)
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
                control1: nil,
                control2: nil,
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
                control1: nil,
                control2: nil,
                radius: turnRadius,
                startAngle: startAngle,
                signedAngleDelta: signedAngleDelta
            ),
            straightSegment(from: arcEnd, to: end)
        ])
    }

    fileprivate static func straightSegment(from start: RoadPoint, to end: RoadPoint) -> RoadSegment {
        RoadSegment(
            kind: .straight,
            start: start,
            end: end,
            center: nil,
            control1: nil,
            control2: nil,
            radius: 0,
            startAngle: 0,
            signedAngleDelta: 0
        )
    }

    fileprivate static func smoothTurnSegment(
        from start: RoadPoint,
        control1: RoadPoint,
        control2: RoadPoint,
        to end: RoadPoint
    ) -> RoadSegment {
        RoadSegment(
            kind: .smoothTurn,
            start: start,
            end: end,
            center: nil,
            control1: control1,
            control2: control2,
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
    var availability: RoadAvailability
    var availabilityRule: EdgeAvailabilityRule?

    init(
        id: String,
        fromNodeID: String,
        toNodeID: String,
        roadShape: RoadShape? = nil,
        availability: RoadAvailability = .always,
        availabilityRule: EdgeAvailabilityRule? = nil
    ) {
        self.id = id
        self.fromNodeID = fromNodeID
        self.toNodeID = toNodeID
        self.roadShape = roadShape
        self.availability = availability
        self.availabilityRule = availabilityRule
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case fromNodeID
        case toNodeID
        case roadShape
        case availability
        case availabilityRule
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        fromNodeID = try container.decode(String.self, forKey: .fromNodeID)
        toNodeID = try container.decode(String.self, forKey: .toNodeID)
        roadShape = try container.decodeIfPresent(RoadShape.self, forKey: .roadShape)
        availability = try container.decodeIfPresent(RoadAvailability.self, forKey: .availability) ?? .always
        availabilityRule = try container.decodeIfPresent(
            EdgeAvailabilityRule.self,
            forKey: .availabilityRule
        )
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(fromNodeID, forKey: .fromNodeID)
        try container.encode(toNodeID, forKey: .toNodeID)
        try container.encodeIfPresent(roadShape, forKey: .roadShape)
        try container.encode(availability, forKey: .availability)
        try container.encodeIfPresent(availabilityRule, forKey: .availabilityRule)
    }

    func effectiveAvailabilityRule(packageObjectiveID: String) -> EdgeAvailabilityRule {
        availabilityRule ?? EdgeAvailabilityRule.adapting(
            availability,
            packageObjectiveID: packageObjectiveID
        )
    }
}
