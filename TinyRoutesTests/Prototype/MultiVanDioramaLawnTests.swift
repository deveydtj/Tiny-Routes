import SceneKit
import XCTest
@testable import TinyRoutes

final class MultiVanDioramaLawnTests: XCTestCase {
    private let unit = MultiVanDioramaLawn.pixelsPerUnit

    func testLawnLayoutIsTheFlatBoardsLayoutAtTextureScale() throws {
        let levels = try MultiVanLevelRepository().loadAllLevels()
        XCTAssertEqual(levels.count, 19)
        // The flat board insets its grid by half a hit target on every side.
        let inset = MultiVanSwitchButton.hitSize
        let flatSize = CGSize(width: 5 * unit + inset, height: 7 * unit + inset)
        for level in levels {
            let lawn = MultiVanDioramaLawn.layout(for: level)
            let flat = MultiVanBoardView.boardLayout(level: level, size: flatSize)
            XCTAssertEqual(lawn.coordinateScale, unit, level.id)
            XCTAssertEqual(flat.coordinateScale, unit, level.id)
            let first = try XCTUnwrap(level.graph.nodes.first)
            let shift = try offset(lawn.pointsByNodeID[first.id], flat.pointsByNodeID[first.id])
            for node in level.graph.nodes {
                let point = try XCTUnwrap(lawn.pointsByNodeID[node.id])
                // Where the grid sits on the slab's top face, far edge at the image's top.
                let world = MultiVanDioramaGeometry.world(gridX: node.x, gridY: node.y)
                XCTAssertEqual(point.x, (world.x + MultiVanDioramaGeometry.slabWidth / 2) * unit, accuracy: 1e-6, level.id)
                XCTAssertEqual(point.y, (world.z + MultiVanDioramaGeometry.slabDepth / 2) * unit, accuracy: 1e-6, level.id)
                // At the same scale the flat board draws the same picture, only shifted.
                let nodeShift = try offset(lawn.pointsByNodeID[node.id], flat.pointsByNodeID[node.id])
                XCTAssertEqual(nodeShift.dx, shift.dx, accuracy: 1e-6, "\(level.id) \(node.id)")
                XCTAssertEqual(nodeShift.dy, shift.dy, accuracy: 1e-6, "\(level.id) \(node.id)")
            }
        }
    }

    func testEveryRoadIsPaintedWhereTheFlatBoardRunsIt() throws {
        for level in try MultiVanLevelRepository().loadAllLevels() {
            let graph = try Self.graph(for: level)
            let layout = MultiVanDioramaLawn.layout(for: level)
            let pixels = Pixels(MultiVanDioramaLawn.image(for: level, graph: graph))
            let features = MultiVanDioramaLawn.Features(level: level, graph: graph)
            // Depot bays and barrier hatching are painted over the road on purpose.
            let covered = features.depots.map(\.point) + features.barriers.map(\.point)
            var misses: [String] = []
            for edge in graph.edgesByID.values.sorted(by: { $0.id < $1.id }) {
                for point in Self.samples(of: edge.roadPath) where !covered.contains(where: { Self.distance($0, point) < 0.42 }) {
                    // Averaged, so the paper grain's fibres don't count as gaps.
                    let colour = pixels.mean(around: try XCTUnwrap(layout.point(for: point)))
                    if !Self.matches(colour, MultiVanDioramaLawn.Palette.asphalt, tolerance: 12) {
                        misses.append("\(edge.id) at (\(point.x), \(point.y)): \(colour)")
                    }
                }
            }
            XCTAssertEqual(misses, [], level.id)
        }
    }

    func testLawnStaysGrassAwayFromRoads() throws {
        // A chapter's ground wash tints the lawn; the meadow is the plain grass.
        for level in try MultiVanLevelRepository().loadAllLevels() where level.biome == .meadow {
            let graph = try Self.graph(for: level)
            let layout = MultiVanDioramaLawn.layout(for: level)
            let pixels = Pixels(MultiVanDioramaLawn.image(for: level, graph: graph))
            let features = MultiVanDioramaLawn.Features(level: level, graph: graph)
            let scenery = MultiVanDioramaScenery(level: level, graph: graph)
            let painted = graph.edgesByID.values.flatMap { Self.samples(of: $0.roadPath) }
                + features.plazas + features.depots.map(\.point) + features.houses.map(\.marking.point)
            let beds = scenery.items.filter { $0.height == 0 }.map(\.point)
            var checked = 0
            for x in stride(from: -1.1, through: 5.1, by: 0.25) {
                for y in stride(from: -1.1, through: 7.1, by: 0.25) {
                    let point = RoadPoint(x: x, y: y)
                    guard !painted.contains(where: { Self.distance($0, point) < 0.5 }) else { continue }
                    guard !beds.contains(where: { Self.distance($0, point) < 0.2 }) else { continue }
                    if let pond = scenery.pond, Self.distance(pond.centre, point) < pond.radiusX + 0.1 { continue }
                    let colour = pixels[try XCTUnwrap(layout.point(for: point))]
                    XCTAssert(colour.y > colour.x + 25 && colour.y > colour.z + 40, "\(level.id) (\(x), \(y)): \(colour)")
                    checked += 1
                }
            }
            XCTAssertGreaterThan(checked, 200, level.id)
        }
    }

    func testRoadCrossSectionStepsFromAsphaltToEdgeLineToCurbToLawn() throws {
        // Level 1 runs one road straight up column 0 before turning across the top.
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_001" })
        let layout = MultiVanDioramaLawn.layout(for: level)
        let pixels = Pixels(MultiVanDioramaLawn.image(for: level, graph: try Self.graph(for: level)))
        let point = { (offset: Double) in layout.point(for: RoadPoint(x: offset, y: 3))! }
        for side in [-1.0, 1.0] {
            XCTAssertTrue(Self.matches(pixels.mean(around: point(0.1 * side)), MultiVanDioramaLawn.Palette.asphalt, tolerance: 12), "\(side)")
            // Grain greys light colours, so tell the white line from the cream curb
            // by warmth. The edge line is only three pixels wide.
            let line = pixels[point(0.159 * side)]
            XCTAssert(line.min() > 205 && line.x - line.z < 10, "edge line, side \(side): \(line)")
            let curb = pixels.mean(around: point(0.2 * side))
            XCTAssert(curb.min() > 170 && curb.x - curb.z > 15, "curb, side \(side): \(curb)")
            let lawn = pixels.mean(around: point(0.32 * side))
            XCTAssert(lawn.y > lawn.x + 25 && lawn.y > lawn.z + 30, "lawn, side \(side): \(lawn)")
        }
    }

    func testSharedStartGetsOneBayStripedInEachVansColour() throws {
        // No authored level shares a start any more; put Convoy's Blue back on Red's spot.
        let url = try XCTUnwrap(Bundle.main.url(forResource: "level_007", withExtension: "json", subdirectory: "PrototypeLevels"))
        let json = try String(contentsOf: url, encoding: .utf8)
            .replacingOccurrences(of: #""startNodeID": "blue_start""#, with: #""startNodeID": "start""#)
        let level = try JSONDecoder().decode(MultiVanLevel.self, from: Data(json.utf8))
        XCTAssertEqual(Set(level.vans.map(\.startNodeID)), ["start"])
        let graph = try Self.graph(for: level)
        let features = MultiVanDioramaLawn.Features(level: level, graph: graph)
        XCTAssertEqual(features.depots.count, 1)
        let depot = try XCTUnwrap(features.depots.first)
        XCTAssertEqual(depot.colors, level.vans.map(\.color))
        XCTAssertEqual(Set(depot.colors).count, 2)

        let pixels = Pixels(MultiVanDioramaLawn.image(for: level, graph: graph))
        let centre = try XCTUnwrap(MultiVanDioramaLawn.layout(for: level).point(for: depot.point))
        let length = hypot(depot.heading.x, depot.heading.y)
        let along = CGVector(dx: depot.heading.x / length, dy: -depot.heading.y / length)
        let across = CGVector(dx: -along.dy, dy: along.dx)
        for (index, color) in depot.colors.enumerated() {
            let side = index == 0 ? -0.09 : 0.09
            let point = CGPoint(
                x: centre.x + (along.dx * -0.305 + across.dx * side) * unit,
                y: centre.y + (along.dy * -0.305 + across.dy * side) * unit
            )
            // The grain greys every colour a little, so check which channel leads.
            let colour = pixels.mean(around: point)
            let leads: Bool
            switch color {
            case .red: leads = colour.x > colour.y + 80 && colour.x > colour.z + 80
            case .blue: leads = colour.z > colour.x + 80 && colour.z > colour.y + 50
            default: leads = false
            }
            XCTAssertTrue(leads, "\(color): \(colour)")
        }
    }

    func testPondAndFlowerBedsArePaintedUnderTheScenery() throws {
        for level in try MultiVanLevelRepository().loadAllLevels() {
            let graph = try Self.graph(for: level)
            let scenery = MultiVanDioramaScenery(level: level, graph: graph)
            let layout = MultiVanDioramaLawn.layout(for: level)
            let pixels = Pixels(MultiVanDioramaLawn.image(for: level, graph: graph, scenery: scenery))
            let pond = try XCTUnwrap(scenery.pond, level.id)
            // Off-centre, past the highlight, where the water shows its deeper blue.
            let water = pixels.mean(around: try XCTUnwrap(layout.point(for: RoadPoint(x: pond.centre.x, y: pond.centre.y - pond.radiusY * 0.75))))
            XCTAssert(water.z > water.x + 80 && water.z > water.y + 10, "\(level.id) pond: \(water)")
            // Each bed shows dots of its colour among the grass.
            for item in scenery.items {
                guard case let .flowers(color) = item.kind, color != 0 else { continue }
                let centre = try XCTUnwrap(layout.point(for: item.point))
                let target = UIColor(dioramaHex: MultiVanDioramaScenery.flowerColors[color])
                var found = false
                for dx in stride(from: -20, through: 20, by: 2) where !found {
                    for dy in stride(from: -16, through: 16, by: 2) where !found {
                        found = Self.matches(pixels[CGPoint(x: centre.x + CGFloat(dx), y: centre.y + CGFloat(dy))], target, tolerance: 30)
                    }
                }
                XCTAssertTrue(found, "\(level.id) bed at (\(item.point.x), \(item.point.y))")
            }
        }
    }

    func testPaintingIsTheSameEveryTime() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_014" })
        let graph = try Self.graph(for: level)
        let first = MultiVanDioramaLawn.image(for: level, graph: graph)
        XCTAssertEqual(first.size, MultiVanDioramaLawn.imageSize)
        XCTAssertEqual(first.scale, 1)
        XCTAssertEqual(first.pngData(), MultiVanDioramaLawn.image(for: level, graph: graph).pngData())
    }

    /// The other half of lining up: SceneKit must lay the image on the slab so each
    /// grid point's pixel lands on that grid point's world position.
    @MainActor
    func testLawnTextureLandsOnTheSlabAtEachNode() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_014" })
        let scene = MultiVanDioramaScene()
        scene.load(level, graph: try MultiVanEngine(level: level).runtimeGraph)
        let image = try XCTUnwrap(scene.lawn.diffuse.contents as? UIImage)
        XCTAssertEqual(image.size, MultiVanDioramaLawn.imageSize)
        // SCNShape builds its mesh on first render.
        let renderer = SCNRenderer(device: MTLCreateSystemDefaultDevice(), options: nil)
        renderer.scene = scene.scene
        renderer.pointOfView = scene.cameraNode
        _ = renderer.snapshot(atTime: 0, with: CGSize(width: 64, height: 64), antialiasingMode: .none)
        let lawnNode = try XCTUnwrap(scene.scene.rootNode.childNode(withName: MultiVanDioramaScene.lawnNodeName, recursively: true))
        let layout = MultiVanDioramaLawn.layout(for: level)
        for node in level.graph.nodes {
            let world = MultiVanDioramaGeometry.world(gridX: node.x, gridY: node.y)
            let from = lawnNode.convertPosition(SCNVector3(world.x, 1, world.z), from: nil)
            let to = lawnNode.convertPosition(SCNVector3(world.x, -0.05, world.z), from: nil)
            let hit = try XCTUnwrap(lawnNode.hitTestWithSegment(from: from, to: to, options: nil).first, node.id)
            XCTAssertEqual(hit.geometryIndex, 0, "top face, \(node.id)")
            let uv = hit.textureCoordinates(withMappingChannel: 0)
            let expected = try XCTUnwrap(layout.pointsByNodeID[node.id])
            XCTAssertEqual(uv.x * image.size.width, expected.x, accuracy: 0.5, node.id)
            XCTAssertEqual(uv.y * image.size.height, expected.y, accuracy: 0.5, node.id)
        }
    }

    // MARK: - Helpers

    private static func graph(for level: MultiVanLevel) throws -> RuntimeRouteGraph {
        try RuntimeRouteGraph.make(from: level.graph) { $0.availabilityRule }
    }

    private static func samples(of road: RoadPath) -> [RoadPoint] {
        stride(from: 0, through: road.totalLength, by: 0.05).map { road.point(atDistance: $0) }
    }

    private static func distance(_ a: RoadPoint, _ b: RoadPoint) -> Double {
        hypot(a.x - b.x, a.y - b.y)
    }

    private static func matches(_ colour: SIMD3<Int>, _ expected: UIColor, tolerance: Int) -> Bool {
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        expected.getRed(&r, green: &g, blue: &b, alpha: &a)
        let target = SIMD3(Int((r * 255).rounded()), Int((g * 255).rounded()), Int((b * 255).rounded()))
        return (colour &- target).abs().max() <= tolerance
    }

    private func offset(_ a: CGPoint?, _ b: CGPoint?) throws -> CGVector {
        let a = try XCTUnwrap(a), b = try XCTUnwrap(b)
        return CGVector(dx: b.x - a.x, dy: b.y - a.y)
    }
}

/// An image's sRGB pixels, for reading back what the painter drew.
private struct Pixels {
    let width: Int
    let height: Int
    private let bytes: [UInt8]

    init(_ image: UIImage) {
        let cgImage = image.cgImage!
        width = cgImage.width
        height = cgImage.height
        var bytes = [UInt8](repeating: 0, count: width * height * 4)
        bytes.withUnsafeMutableBytes { buffer in
            let context = CGContext(
                data: buffer.baseAddress, width: cgImage.width, height: cgImage.height, bitsPerComponent: 8,
                bytesPerRow: cgImage.width * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
            )!
            context.draw(cgImage, in: CGRect(x: 0, y: 0, width: cgImage.width, height: cgImage.height))
        }
        self.bytes = bytes
    }

    /// The average over a square `radius` pixels either side of `point`.
    func mean(around point: CGPoint, radius: Int = 2) -> SIMD3<Int> {
        var sum = SIMD3<Int>.zero
        for dx in -radius...radius {
            for dy in -radius...radius {
                sum &+= self[CGPoint(x: point.x + CGFloat(dx), y: point.y + CGFloat(dy))]
            }
        }
        return sum / ((2 * radius + 1) * (2 * radius + 1))
    }

    subscript(point: CGPoint) -> SIMD3<Int> {
        let x = min(max(Int(point.x), 0), width - 1), y = min(max(Int(point.y), 0), height - 1)
        let index = (y * width + x) * 4
        return SIMD3(Int(bytes[index]), Int(bytes[index + 1]), Int(bytes[index + 2]))
    }
}

private extension SIMD3 where Scalar == Int {
    func abs() -> Self { Self(Swift.abs(x), Swift.abs(y), Swift.abs(z)) }
}
