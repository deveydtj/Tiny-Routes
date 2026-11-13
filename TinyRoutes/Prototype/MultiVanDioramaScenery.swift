import Foundation

/// Where the diorama's scenery stands on a level: groves of trees, bushes, flower
/// beds, one pond and a few residents by their front doors. Renderer-free and seeded
/// by the level, in the HTML prototype's order, so a level always gets the same
/// scenery. Nothing covers a road or crowds a piece, and nothing tall stands where
/// it would hide one from the lens at its resting angle.
///
/// The prototype's rules are kept with two changes: a flower bed sits wholly on the
/// lawn, and a standing piece keeps clear the whole patch it hides, not only the
/// line straight up the board behind its foot.
struct MultiVanDioramaScenery: Equatable {
    enum Tree: Equatable {
        /// One of three palettes of round tree.
        case round(Int)
        case pine
    }

    enum Kind: Equatable {
        case tree(Tree)
        case bush(Int)
        /// A bed painted on the lawn, in one of `flowerColors`.
        case flowers(Int)
        case resident(Int)

        /// Width over height of the cutout's art; the scene's art must match.
        var aspect: Double {
            switch self {
            case .tree(.round): 256.0 / 320
            case .tree(.pine): 220.0 / 340
            case .bush: 220.0 / 150
            case .resident: 120.0 / 260
            case .flowers: 0
            }
        }
    }

    struct Item: Equatable {
        let kind: Kind
        /// Where it stands, in grid space.
        let point: RoadPoint
        /// Height of a standing cutout in grid units; zero for a flower bed.
        let height: Double

        /// How far its foot, or its bed, reaches across the lawn.
        var footprint: Double {
            if case .flowers = kind { return Measure.flowerBedRadius }
            return height * kind.aspect * Measure.artFill / 2
        }

        /// The lawn this piece hides from the resting lens: a patch reaching back
        /// `sightline × height` behind its foot, as wide as its art. Sampled no
        /// further apart than `spacing`; empty for a flower bed.
        func hiddenGround(spacing: Double) -> [RoadPoint] {
            guard height > 0 else { return [] }
            let reach = height * Measure.sightline, half = footprint
            let back = MultiVanDioramaScenery.awayFromLens, across = RoadVector(x: back.y, y: -back.x)
            var points: [RoadPoint] = []
            for along in MultiVanDioramaScenery.stops(from: 0, to: reach, spacing: spacing) {
                for side in MultiVanDioramaScenery.stops(from: -half, to: half, spacing: spacing) {
                    points.append(RoadPoint(
                        x: point.x + back.x * along + across.x * side,
                        y: point.y + back.y * along + across.y * side
                    ))
                }
            }
            return points
        }
    }

    struct Pond: Equatable {
        let centre: RoadPoint
        let radiusX: Double
        let radiusY: Double
        /// The ellipse's turn, anticlockwise as seen from above, in radians.
        let angle: Double
    }

    /// The prototype's tuning, in grid units.
    enum Measure {
        /// Half the curb's width: where a road's paint ends.
        static let roadEdge = MultiVanDioramaLawn.Measure.curbWidth / 2
        static let plazaEdge = MultiVanDioramaLawn.Measure.plazaRadii.curb
        static let roadClearance = 0.34
        static let houseClearance = 0.62
        static let doorClearance = 0.36
        static let switchClearance = 0.42
        static let depotClearance = 0.42
        static let barrierClearance = 0.45
        /// Standing art fills about this much of its image's width.
        static let artFill = 0.8
        /// A piece hides this many times its height of lawn behind it.
        static let sightline = 0.95
        /// Flower dots scatter 0.094 by 0.072 either side of the bed's centre.
        static let flowerBedRadius = 0.12
        static let residentHeight = 0.2
        static let maxTrees = 34
        static let maxBushes = 18
        static let maxFlowerBeds = 34
        static let maxGroves = 9
    }

    static let flowerColors = [0xFFFFFF, 0xFFD75E, 0xFF9FB4, 0xC9A8FF, 0xFF8A5C]

    /// Away from the lens at its resting angle, in grid space.
    static let awayFromLens = RoadVector(x: -sin(MultiVanDioramaCamera.restingYaw), y: cos(MultiVanDioramaCamera.restingYaw))

    let items: [Item]
    let pond: Pond?

    init(level: MultiVanLevel, graph: RuntimeRouteGraph) {
        let features = MultiVanDioramaLawn.Features(level: level, graph: graph)
        let ground = Ground(features: features, graph: graph)
        var random = MultiVanDioramaRandom(seed: UInt32(truncatingIfNeeded: level.scenerySeed) &* 1013 &+ 7)
        var keepOut = ground.keepOut
        var items: [Item] = []

        // One pond in the roomiest open patch.
        var best: (point: RoadPoint, clearance: Double)?
        for _ in 0..<400 {
            let point = RoadPoint(x: -1 + random.next() * 6, y: -0.8 + random.next() * 7.6)
            guard Self.isOnSlab(point, margin: 0.7) else { continue }
            let clearance = Self.clearance(of: point, from: keepOut)
            if clearance > 0.55, clearance > best?.clearance ?? -.infinity { best = (point, clearance) }
        }
        pond = best.map { best in
            let radiusX = min(0.62, best.clearance * 0.9)
            keepOut.append((best.point, radiusX + 0.15))
            return Pond(centre: best.point, radiusX: radiusX, radiusY: radiusX * 0.68, angle: -0.2)
        }

        // Trees grow in groves, the way a model maker would plant them.
        var groves: [RoadPoint] = []
        for _ in 0..<600 where groves.count < Measure.maxGroves {
            let point = RoadPoint(x: -1.1 + random.next() * 6.2, y: -0.3 + random.next() * 7.5)
            if Self.isOnSlab(point, margin: 0.3), Self.clearance(of: point, from: keepOut) > 0.25,
               groves.allSatisfy({ Self.distance($0, point) > 1.1 }) {
                groves.append(point)
            }
        }
        let scatter = { (random: inout MultiVanDioramaRandom) in (random.next() + random.next() + random.next() - 1.5) * 0.55 }
        var counts = (trees: 0, bushes: 0, flowers: 0)
        for _ in 0..<1600 {
            let grove = !groves.isEmpty && random.next() < 0.7 ? groves[Int(random.next() * Double(groves.count))] : nil
            let point = grove.map { RoadPoint(x: $0.x + scatter(&random), y: $0.y + scatter(&random)) }
                ?? RoadPoint(x: -1.2 + random.next() * 6.4, y: -1.2 + random.next() * 8.4)
            guard Self.isOnSlab(point, margin: 0.22) else { continue }
            let isFront = point.y < -0.45, clearance = Self.clearance(of: point, from: keepOut)
            let isCrowded = items.contains { item in
                if case .flowers = item.kind { return Self.distance(item.point, point) < 0.22 }
                return Self.distance(item.point, point) < 0.36
            }
            guard !isCrowded else { continue }
            let roll = random.next()
            if !isFront, clearance > 0.12, counts.trees < Measure.maxTrees, roll < (grove == nil ? 0.2 : 0.85) {
                let height = 0.6 + random.next() * 0.38
                // Checked as a round tree, the widest; a pine hides less.
                guard ground.isInView(Item(kind: .tree(.round(0)), point: point, height: height)) else { continue }
                let tree: Tree = random.next() < 0.28 ? .pine : .round(Int(random.next() * 3))
                items.append(Item(kind: .tree(tree), point: point, height: height))
                counts.trees += 1
            } else if clearance > 0.06, counts.bushes < Measure.maxBushes, roll < 0.75 {
                let height = 0.17 + random.next() * 0.08
                guard ground.isInView(Item(kind: .bush(0), point: point, height: height)) else { continue }
                items.append(Item(kind: .bush(Int(random.next() * 3)), point: point, height: height))
                counts.bushes += 1
            } else if clearance > -0.05, counts.flowers < Measure.maxFlowerBeds,
                      ground.paintClearance(point) > Measure.flowerBedRadius {
                items.append(Item(kind: .flowers(Int(random.next() * Double(Self.flowerColors.count))), point: point, height: 0))
                counts.flowers += 1
            }
        }

        // A few residents chatting beside their front doors.
        let nearby = ground.keepOut.filter { $0.radius < 0.4 }
        for (index, house) in features.houses.enumerated() {
            let heading = Self.unit(house.marking.heading), side = RoadVector(x: -heading.y, y: heading.x)
            let sign = index.isMultiple(of: 2) ? -1.0 : 1.0
            let point = RoadPoint(
                x: house.marking.point.x + side.x * 0.48 * sign - heading.x * 0.05,
                y: house.marking.point.y + side.y * 0.48 * sign - heading.y * 0.05
            )
            let resident = Item(kind: .resident(index % 4), point: point, height: Measure.residentHeight)
            if Self.clearance(of: point, from: nearby) > -0.05, Self.isOnSlab(point, margin: 0.15),
               ground.paintClearance(point) > resident.footprint, ground.isInView(resident) {
                items.append(resident)
            }
        }
        self.items = items
    }

    // MARK: - What scenery keeps clear of

    /// The level's roads and pieces, as the scenery sees them.
    private struct Ground {
        /// Points along every road, close enough that the nearest is within a
        /// hair of the road's true distance.
        let roadSamples: [RoadPoint]
        let plazas: [RoadPoint]
        /// Everything scenery keeps clear of, as a point and a radius.
        let keepOut: [(point: RoadPoint, radius: Double)]

        init(features: MultiVanDioramaLawn.Features, graph: RuntimeRouteGraph) {
            roadSamples = MultiVanDioramaScenery.roadSamples(in: graph)
            plazas = features.plazas
            keepOut = roadSamples.map { ($0, Measure.roadClearance) }
                + features.houses.map { ($0.centre, Measure.houseClearance) }
                + features.houses.map { ($0.marking.point, Measure.doorClearance) }
                + features.plazas.map { ($0, Measure.switchClearance) }
                + features.depots.map { ($0.point, Measure.depotClearance) }
                + features.barriers.map { ($0.point, Measure.barrierClearance) }
                + features.reserved
        }

        /// How far `point` is from the paint of the nearest road or switch plaza;
        /// negative on it.
        func paintClearance(_ point: RoadPoint) -> Double {
            let road = roadSamples.reduce(.infinity) { min($0, MultiVanDioramaScenery.distance($1, point)) }
            let plaza = plazas.reduce(.infinity) { min($0, MultiVanDioramaScenery.distance($1, point)) }
            return min(road - Measure.roadEdge, plaza - Measure.plazaEdge)
        }

        /// Whether the lawn `item` hides is clear of every road and piece. Samples
        /// sit 0.12 apart and must clear the keep-out by 0.02, so no point between
        /// them, at most 0.085 from one, reaches paint: a road's at 0.235 against
        /// 0.36 − 0.085, a plaza's at 0.34 against 0.44 − 0.085.
        func isInView(_ item: Item) -> Bool {
            item.hiddenGround(spacing: 0.12).allSatisfy { MultiVanDioramaScenery.clearance(of: $0, from: keepOut) > 0.02 }
        }
    }

    static func roadSamples(in graph: RuntimeRouteGraph) -> [RoadPoint] {
        graph.edgesByID.values.sorted { $0.id < $1.id }.flatMap { edge in
            stride(from: 0, through: edge.roadPath.totalLength, by: 0.05).map { edge.roadPath.point(atDistance: $0) }
        }
    }

    /// How far `point` is from the nearest keep-out circle's edge; negative inside one.
    private static func clearance(of point: RoadPoint, from keepOut: [(point: RoadPoint, radius: Double)]) -> Double {
        keepOut.reduce(.infinity) { min($0, distance($1.point, point) - $1.radius) }
    }

    /// Inside the slab's rim, less `margin`.
    private static func isOnSlab(_ point: RoadPoint, margin: Double) -> Bool {
        let halfWidth = MultiVanDioramaGeometry.slabWidth / 2, halfDepth = MultiVanDioramaGeometry.slabDepth / 2
        return abs(point.x - 2) < halfWidth - margin && abs(point.y - 3) < halfDepth - margin
    }

    /// Evenly spaced values from `start` to `end`, both included, no more than `spacing` apart.
    fileprivate static func stops(from start: Double, to end: Double, spacing: Double) -> [Double] {
        let count = max(1, Int(((end - start) / spacing).rounded(.up)))
        return (0...count).map { start + (end - start) * Double($0) / Double(count) }
    }

    private static func distance(_ a: RoadPoint, _ b: RoadPoint) -> Double {
        hypot(a.x - b.x, a.y - b.y)
    }

    private static func unit(_ vector: RoadVector) -> RoadVector {
        let length = hypot(vector.x, vector.y)
        guard length.isFinite, length > 1e-9 else { return RoadVector(x: 0, y: 1) }
        return RoadVector(x: vector.x / length, y: vector.y / length)
    }
}
