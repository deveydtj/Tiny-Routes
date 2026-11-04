import SceneKit
import XCTest
@testable import TinyRoutes

final class MultiVanDioramaSceneryTests: XCTestCase {
    func testTheSameLevelAlwaysGetsTheSameScenery() throws {
        var layouts: [MultiVanDioramaScenery] = []
        for level in try MultiVanLevelRepository().loadAllLevels() {
            let graph = try Self.graph(for: level)
            let scenery = MultiVanDioramaScenery(level: level, graph: graph)
            XCTAssertEqual(scenery, MultiVanDioramaScenery(level: level, graph: try Self.graph(for: level)), level.id)
            XCTAssertNotNil(scenery.pond, "\(level.id) has room for a pond")
            let trees = scenery.items.filter { if case .tree = $0.kind { return true } else { return false } }
            XCTAssertGreaterThanOrEqual(trees.count, 8, "\(level.id) has groves")
            layouts.append(scenery)
        }
        // Seeded by level, so no two levels share a layout.
        for (index, layout) in layouts.enumerated() {
            XCTAssertFalse(layouts[..<index].contains(layout), "level \(index + 1)")
        }
    }

    /// Measured against the road as the lawn paints it, independently of the rules
    /// that place the scenery: every curb's edge and every plaza's rim.
    func testNoSceneryCoversARoadOrStandsInFrontOfOne() throws {
        for level in try MultiVanLevelRepository().loadAllLevels() {
            let graph = try Self.graph(for: level)
            let scenery = MultiVanDioramaScenery(level: level, graph: graph)
            let paint = Paint(graph: graph)
            var failures: [String] = []
            for item in scenery.items {
                let name = "\(item.kind) at (\(item.point.x), \(item.point.y))"
                let paint = paint.near(item.point, within: 2)
                // A bed must lie wholly on the lawn; a standing piece's foot off the road.
                let foot = item.height > 0 ? 0 : item.footprint
                if paint.clearance(item.point) <= foot { failures.append("\(name) covers a road") }
                // Nothing tall hides road behind it from the resting lens.
                if let hidden = item.hiddenGround(spacing: 0.02).first(where: { paint.clearance($0) <= 0 }) {
                    failures.append("\(name) hides road at (\(hidden.x), \(hidden.y))")
                }
            }
            if let pond = scenery.pond {
                // The bank reaches 12 texels past the water.
                let bank = 12 / MultiVanDioramaLawn.pixelsPerUnit
                for step in 0..<72 {
                    let t = Double(step) / 72 * 2 * .pi
                    let x = cos(t) * (pond.radiusX + bank), y = sin(t) * (pond.radiusY + bank)
                    let point = RoadPoint(
                        x: pond.centre.x + x * cos(pond.angle) - y * sin(pond.angle),
                        y: pond.centre.y + x * sin(pond.angle) + y * cos(pond.angle)
                    )
                    if paint.clearance(point) <= 0 { failures.append("pond's bank covers a road at (\(point.x), \(point.y))") }
                }
            }
            XCTAssertEqual(failures, [], level.id)
        }
    }

    func testSceneryKeepsOffThePieces() throws {
        for level in try MultiVanLevelRepository().loadAllLevels() {
            let graph = try Self.graph(for: level)
            let scenery = MultiVanDioramaScenery(level: level, graph: graph)
            let features = MultiVanDioramaLawn.Features(level: level, graph: graph)
            // Half a house's diagonal at its scale, a dial's rim, a roadblock's cones.
            let pieces = features.houses.map { ($0.centre, 0.51) } + features.plazas.map { ($0, 0.31) }
                + features.barriers.map { ($0.point, 0.33) }
            for item in scenery.items {
                for (point, radius) in pieces {
                    XCTAssertGreaterThan(hypot(item.point.x - point.x, item.point.y - point.y), radius, "\(level.id) \(item)")
                }
            }
            guard let pond = scenery.pond else { continue }
            for item in scenery.items where item.height > 0 {
                XCTAssertGreaterThan(hypot(item.point.x - pond.centre.x, item.point.y - pond.centre.y), pond.radiusX, "\(level.id) \(item) in the pond")
            }
        }
    }

    @MainActor
    func testEveryCutoutComesFromTheAssetCatalogAtItsAspect() throws {
        let kinds: [MultiVanDioramaScenery.Kind] = (0..<3).map { .tree(.round($0)) } + [.tree(.pine)]
            + (0..<3).map { .bush($0) } + (0..<4).map { .resident($0) }
        for kind in kinds {
            let name = try XCTUnwrap(MultiVanDioramaPieces.Texture.sceneryArtName(kind))
            let cutout = try XCTUnwrap(MultiVanDioramaPieces.Texture.scenery(named: name), name)
            XCTAssertEqual(cutout.front.scale, 1, name)
            XCTAssertEqual(cutout.front.size.width / cutout.front.size.height, kind.aspect, accuracy: 1e-9, name)
            // Cut out, not printed on a card.
            let pixels = try XCTUnwrap(cutout.front.cgImage?.dataProvider?.data as Data?)
            XCTAssertEqual(pixels[3], 0, "\(name) top-left corner is clear")
        }
        XCTAssertNil(MultiVanDioramaPieces.Texture.sceneryArtName(.flowers(0)))
    }

    @MainActor
    func testSceneStandsEveryCutoutOnItsSpotAndSwaysUnlessMotionIsReduced() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_010" })
        let engine = try MultiVanEngine(level: level)
        let scene = MultiVanDioramaScene()
        scene.load(level, graph: engine.runtimeGraph)
        let scenery = try XCTUnwrap(scene.scenery)
        XCTAssertEqual(scenery, MultiVanDioramaScenery(level: level, graph: engine.runtimeGraph))
        let standing = scenery.items.filter { $0.height > 0 }
        XCTAssertEqual(scene.sceneryNodes.count, standing.count)
        for (item, node) in zip(standing, scene.sceneryNodes) {
            let world = MultiVanDioramaGeometry.world(gridX: item.point.x, gridY: item.point.y)
            XCTAssertEqual(node.simdPosition.x, Float(world.x), accuracy: 1e-5)
            XCTAssertEqual(node.simdPosition.y, 0)
            XCTAssertEqual(node.simdPosition.z, Float(world.z), accuracy: 1e-5)
            // Standing on its foot, as tall as the scenery says.
            let (low, high) = node.boundingBox
            XCTAssertEqual(Double(low.y) * Double(node.simdScale.y), 0, accuracy: 1e-5)
            XCTAssertEqual(Double(high.y) * Double(node.simdScale.y), item.height, accuracy: 1e-5)
            XCTAssertNotNil(node.childNode(withName: MultiVanDioramaPieces.Part.sway, recursively: false))
        }
        XCTAssertNotNil(scene.pondNode)

        let swaying = { () -> Int in
            scene.sceneryNodes.filter { $0.childNode(withName: MultiVanDioramaPieces.Part.sway, recursively: false)?.hasActions == true }.count
        }
        let sways = standing.filter { if case .bush = $0.kind { return false } else { return true } }.count
        XCTAssertGreaterThan(sways, 0)
        scene.sync(MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: false))
        XCTAssertEqual(swaying(), sways, "trees and residents sway; bushes stay put")
        XCTAssertFalse(scene.clouds.isEmpty)
        XCTAssertTrue(scene.clouds.allSatisfy(\.hasActions), "clouds drift")
        XCTAssertTrue(scene.clouds.allSatisfy { !$0.castsShadow })
        let cloudHomes = scene.clouds.map(\.simdPosition)
        scene.sync(MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: true))
        XCTAssertEqual(swaying(), 0, "\"Reduce Animations\" stills them")
        XCTAssertFalse(scene.clouds.contains(where: \.hasActions), "and the clouds")
        XCTAssertEqual(scene.clouds.map(\.simdPosition), cloudHomes)
        for node in scene.sceneryNodes {
            XCTAssertEqual(node.childNode(withName: MultiVanDioramaPieces.Part.sway, recursively: false)?.simdEulerAngles.z, 0)
        }
        scene.sync(MultiVanDioramaFrame(engine: engine, systemReduceMotion: true, reducesExtraAnimations: false))
        XCTAssertEqual(swaying(), 0, "so does Reduce Motion")
    }

    // MARK: - Helpers

    private static func graph(for level: MultiVanLevel) throws -> RuntimeRouteGraph {
        try RuntimeRouteGraph.make(from: level.graph) { $0.availabilityRule }
    }

    /// The roads' and plazas' paint, from fine polylines of each road.
    private struct Paint {
        private let segments: [(RoadPoint, RoadPoint)]
        private let plazas: [RoadPoint]

        private init(segments: [(RoadPoint, RoadPoint)], plazas: [RoadPoint]) {
            self.segments = segments
            self.plazas = plazas
        }

        init(graph: RuntimeRouteGraph) {
            segments = graph.edgesByID.values.flatMap { edge -> [(RoadPoint, RoadPoint)] in
                let road = edge.roadPath
                let points = stride(from: 0, through: road.totalLength, by: 0.02).map { road.point(atDistance: $0) }
                    + [road.point(atDistance: road.totalLength)]
                return zip(points, points.dropFirst()).map { ($0, $1) }
            }
            plazas = MultiVanBoardRules.switchNodes(in: graph).map { RoadPoint(x: $0.x, y: $0.y) }
        }

        /// Only the paint within `radius` of `point`, for checking around it quickly.
        func near(_ point: RoadPoint, within radius: Double) -> Self {
            let isNear = { (p: RoadPoint) in hypot(p.x - point.x, p.y - point.y) < radius }
            return Self(segments: segments.filter { isNear($0.0) }, plazas: plazas.filter(isNear))
        }

        /// How far `point` is from paint; zero or less on it.
        func clearance(_ point: RoadPoint) -> Double {
            var road = Double.infinity
            for (a, b) in segments {
                road = min(road, Self.distance(from: point, toSegment: a, b))
            }
            let plaza = plazas.map { hypot($0.x - point.x, $0.y - point.y) }.min() ?? .infinity
            return min(road - MultiVanDioramaLawn.Measure.curbWidth / 2, plaza - MultiVanDioramaLawn.Measure.plazaRadii.curb)
        }

        private static func distance(from p: RoadPoint, toSegment a: RoadPoint, _ b: RoadPoint) -> Double {
            let dx = b.x - a.x, dy = b.y - a.y, lengthSquared = dx * dx + dy * dy
            let t = lengthSquared > 0 ? max(0, min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / lengthSquared)) : 0
            return hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))
        }
    }
}
