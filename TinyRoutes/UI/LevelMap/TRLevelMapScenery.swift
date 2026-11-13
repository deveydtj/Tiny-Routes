import Foundation

/// What stands on the level map besides the road and the van: groves of trees,
/// bushes, flower beds, a cottage every few levels and a pond or two. Seeded, so
/// the map looks the same every visit, and kept clear of the road and the tiles.
struct TRLevelMapScenery: Equatable {
    struct House: Equatable {
        let color: VanColor
        let point: RoadPoint
        /// Towards the road, for its front door.
        let facing: RoadVector
    }

    let items: [MultiVanDioramaScenery.Item]
    let houses: [House]
    let ponds: [MultiVanDioramaScenery.Pond]

    enum Measure {
        /// Half the painted road's width, from `TRLevelMapLawn`.
        static let roadEdge = TRLevelMapLawn.Measure.curbWidth / 2
        static let treeClearance = 0.42
        static let bushClearance = 0.22
        static let flowerClearance = 0.1
        /// Nothing tall stands this close to a level's stop, where its tile is.
        static let tileClearance = 0.62
        static let edgeMargin = 0.25
        /// Scenery keeps this far from a cottage's middle.
        static let houseClearance = 0.5
    }

    init(layout: TRLevelMapLayout) {
        var random = MultiVanDioramaRandom(seed: 41)
        let halfWidth = TRLevelMapLayout.width / 2
        let stations = (0..<layout.levelCount).map(layout.station)
        let depth = layout.depth

        func nearStation(_ point: RoadPoint, within distance: Double) -> Bool {
            stations.contains { hypot($0.x - point.x, $0.y - point.y) < distance }
        }

        /// Whether something `halfWidth` across, whose top shows `reach` up the
        /// screen from its foot, keeps clear of every tile.
        func clearOfTiles(_ point: RoadPoint, halfWidth: Double, reach: Double) -> Bool {
            layout.tileOverlap(
                minX: point.x - halfWidth, maxX: point.x + halfWidth, minY: point.y - halfWidth, maxY: point.y + reach
            ) == 0
        }

        /// Spots across a stretch of the island, every 0.2 units.
        func candidates(fromY low: Double, toY high: Double) -> [RoadPoint] {
            var points: [RoadPoint] = []
            for y in stride(from: max(low, 0.6), through: min(high, depth - 0.6), by: 0.2) {
                for x in stride(from: -halfWidth + 0.6, through: halfWidth - 0.6, by: 0.2) {
                    points.append(RoadPoint(x: x, y: y))
                }
            }
            return points
        }

        // A cottage by the road for every three levels, in a gap between their tiles.
        var houses: [House] = []
        let colors: [VanColor] = [.red, .yellow, .blue, .green]
        for (index, levelIndex) in stride(from: 0, to: layout.levelCount, by: 3).enumerated() {
            let low = layout.station(levelIndex).y, high = layout.station(min(levelIndex + 2, layout.levelCount - 1)).y + 0.6
            let spots = candidates(fromY: low, toY: high).compactMap { point -> (RoadPoint, Double)? in
                let clearance = layout.distanceToRoad(point) - Measure.roadEdge
                guard clearance > 0.42, clearance < 1.0,
                      clearOfTiles(point, halfWidth: 0.42, reach: 0.75),
                      !houses.contains(where: { hypot($0.point.x - point.x, $0.point.y - point.y) < 1.6 }) else { return nil }
                // Snug against the road, with a little seeded variety.
                return (point, abs(clearance - 0.5) + random.next() * 0.15)
            }
            guard let spot = spots.min(by: { $0.1 < $1.1 })?.0 else { continue }
            let nearest = layout.roadSamples(fromY: spot.y - 1.2, toY: spot.y + 1.2, spacing: 0.05)
                .min { hypot($0.x - spot.x, $0.y - spot.y) < hypot($1.x - spot.x, $1.y - spot.y) } ?? spot
            houses.append(House(
                color: colors[index % colors.count], point: spot,
                facing: RoadVector(x: nearest.x - spot.x, y: nearest.y - spot.y)
            ))
        }
        self.houses = houses

        // A pond in a wide clearing every eight levels or so.
        var ponds: [MultiVanDioramaScenery.Pond] = []
        for levelIndex in stride(from: 1, to: max(layout.levelCount, 2), by: 8) {
            let low = layout.station(levelIndex).y, high = layout.station(min(levelIndex + 5, layout.levelCount - 1)).y
            let spots = candidates(fromY: low, toY: high).compactMap { point -> (RoadPoint, Double)? in
                let clearance = layout.distanceToRoad(point) - Measure.roadEdge
                guard clearance > 0.85, abs(point.x) < halfWidth - 0.85,
                      clearOfTiles(point, halfWidth: 0.75, reach: 0.45),
                      !houses.contains(where: { hypot($0.point.x - point.x, $0.point.y - point.y) < 1.3 }) else { return nil }
                return (point, -clearance)
            }
            guard let centre = spots.min(by: { $0.1 < $1.1 })?.0 else { continue }
            ponds.append(MultiVanDioramaScenery.Pond(centre: centre, radiusX: 0.6, radiusY: 0.38, angle: centre.x > 0 ? -0.15 : 0.15))
        }
        self.ponds = ponds

        func clearOfPieces(_ point: RoadPoint, by distance: Double) -> Bool {
            !houses.contains { hypot($0.point.x - point.x, $0.point.y - point.y) < Measure.houseClearance + distance }
                && !ponds.contains { pond in
                    let dx = (point.x - pond.centre.x) / (pond.radiusX + distance)
                    let dy = (point.y - pond.centre.y) / (pond.radiusY + distance)
                    return dx * dx + dy * dy < 1
                }
        }

        // Groves sit in the bays the road's swings leave either side.
        var groves: [RoadPoint] = []
        for _ in 0..<Int(depth / 1.6) + 2 {
            let point = RoadPoint(x: (random.next() - 0.5) * (TRLevelMapLayout.width - 1), y: random.next() * depth)
            if layout.distanceToRoad(point) > 0.9 { groves.append(point) }
        }
        let scatter = { (random: inout MultiVanDioramaRandom) in (random.next() + random.next() + random.next() - 1.5) * 0.6 }

        var items: [MultiVanDioramaScenery.Item] = []
        let maxTrees = Int(depth * 3.2), maxBushes = Int(depth * 1.4), maxFlowers = Int(depth * 2.6)
        var counts = (trees: 0, bushes: 0, flowers: 0)
        for _ in 0..<Int(depth * 160) {
            let grove = !groves.isEmpty && random.next() < 0.65 ? groves[Int(random.next() * Double(groves.count))] : nil
            let point = grove.map { RoadPoint(x: $0.x + scatter(&random), y: $0.y + scatter(&random)) }
                ?? RoadPoint(x: (random.next() - 0.5) * TRLevelMapLayout.width, y: random.next() * depth)
            guard abs(point.x) < halfWidth - Measure.edgeMargin,
                  point.y > Measure.edgeMargin, point.y < depth - Measure.edgeMargin else { continue }
            let isCrowded = items.contains { item in
                let gap = hypot(item.point.x - point.x, item.point.y - point.y)
                if case .flowers = item.kind { return gap < 0.22 }
                return gap < 0.38
            }
            guard !isCrowded else { continue }
            let clearance = layout.distanceToRoad(point) - Measure.roadEdge
            let roll = random.next()
            if clearance > Measure.treeClearance, counts.trees < maxTrees, roll < (grove == nil ? 0.25 : 0.85),
               !nearStation(point, within: Measure.tileClearance + 0.3), clearOfPieces(point, by: 0.3) {
                let tree: MultiVanDioramaScenery.Tree = random.next() < 0.32 ? .pine : .round(Int(random.next() * 3))
                items.append(.init(kind: .tree(tree), point: point, height: 0.62 + random.next() * 0.36))
                counts.trees += 1
            } else if clearance > Measure.bushClearance, counts.bushes < maxBushes, roll < 0.7,
                      !nearStation(point, within: Measure.tileClearance), clearOfPieces(point, by: 0.15) {
                items.append(.init(kind: .bush(Int(random.next() * 3)), point: point, height: 0.17 + random.next() * 0.08))
                counts.bushes += 1
            } else if clearance > Measure.flowerClearance, counts.flowers < maxFlowers, clearOfPieces(point, by: 0.1) {
                let color = Int(random.next() * Double(MultiVanDioramaScenery.flowerColors.count))
                items.append(.init(kind: .flowers(color), point: point, height: 0))
                counts.flowers += 1
            }
        }
        self.items = items
    }
}
