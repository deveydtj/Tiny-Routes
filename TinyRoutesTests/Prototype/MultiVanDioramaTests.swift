import SceneKit
import XCTest
@testable import TinyRoutes

final class MultiVanDioramaTests: XCTestCase {
    func testGridMapsToWorldWithRowZeroNearestTheCamera() {
        XCTAssertEqual(MultiVanDioramaGeometry.world(gridX: 0, gridY: 0), SIMD3(-2, 0, 3))
        XCTAssertEqual(MultiVanDioramaGeometry.world(gridX: 4, gridY: 6), SIMD3(2, 0, -3))
        XCTAssertEqual(MultiVanDioramaGeometry.world(gridX: 2, gridY: 3, height: 0.5), SIMD3(0, 0.5, 0))
        // The whole grid sits on the slab with lawn to spare.
        for x in [0.0, 4.0] {
            for y in [0.0, 6.0] {
                let point = MultiVanDioramaGeometry.world(gridX: x, gridY: y)
                XCTAssertLessThan(abs(point.x) + 0.5, MultiVanDioramaGeometry.slabWidth / 2)
                XCTAssertLessThan(abs(point.z) + 0.5, MultiVanDioramaGeometry.slabDepth / 2)
            }
        }
    }

    func testRowZeroProjectsBelowRowSix() throws {
        let camera = MultiVanDioramaCamera()
        let near = try XCTUnwrap(camera.project(MultiVanDioramaGeometry.world(gridX: 2, gridY: 0), aspect: 0.8))
        let far = try XCTUnwrap(camera.project(MultiVanDioramaGeometry.world(gridX: 2, gridY: 6), aspect: 0.8))
        XCTAssertLessThan(near.y, far.y)
        let left = try XCTUnwrap(camera.project(MultiVanDioramaGeometry.world(gridX: 0, gridY: 3), aspect: 0.8))
        let right = try XCTUnwrap(camera.project(MultiVanDioramaGeometry.world(gridX: 4, gridY: 3), aspect: 0.8))
        XCTAssertLessThan(left.x, right.x)
    }

    func testFramingFitsTheSlabSnuglyAndCentred() throws {
        let inset = 10.0
        for size in [CGSize(width: 343, height: 420), CGSize(width: 390, height: 700), CGSize(width: 700, height: 360)] {
            var camera = MultiVanDioramaCamera()
            camera.frame(MultiVanDioramaGeometry.fitPoints, in: size, inset: inset)
            let aspect = size.width / size.height
            let points = try MultiVanDioramaGeometry.fitPoints.map { try XCTUnwrap(camera.project($0, aspect: aspect)) }
            // Back to points from the view's centre.
            let xs = points.map { $0.x * size.width / 2 }, ys = points.map { $0.y * size.height / 2 }
            let halfWidth = size.width / 2 - inset, halfHeight = size.height / 2 - inset
            let label = "\(size)"
            XCTAssertLessThanOrEqual(xs.map(abs).max()!, halfWidth + 0.01, label)
            XCTAssertLessThanOrEqual(ys.map(abs).max()!, halfHeight + 0.01, label)
            // One axis touches its limit, and the slab is centred within a point.
            let slack = min(halfWidth - xs.map(abs).max()!, halfHeight - ys.map(abs).max()!)
            XCTAssertLessThan(slack, 0.5, label)
            XCTAssertEqual((xs.max()! + xs.min()!) / 2, 0, accuracy: 1, label)
            XCTAssertEqual((ys.max()! + ys.min()!) / 2, 0, accuracy: 1, label)
            XCTAssertEqual(camera.yaw, MultiVanDioramaCamera.restingYaw)
            XCTAssertEqual(camera.pitch, MultiVanDioramaCamera.restingPitch)
            XCTAssertGreaterThan(camera.focusDistance, 0, label)
        }
    }

    @MainActor
    func testApertureStopsDownAsTheCameraComesCloser() {
        var tall = MultiVanDioramaCamera(), wide = MultiVanDioramaCamera()
        tall.frame(MultiVanDioramaGeometry.fitPoints, in: CGSize(width: 360, height: 460), inset: 10)
        wide.frame(MultiVanDioramaGeometry.fitPoints, in: CGSize(width: 360, height: 330), inset: 10)
        XCTAssertLessThan(wide.focusDistance, tall.focusDistance)
        XCTAssertEqual(MultiVanDioramaScene.fStop(focusDistance: tall.focusDistance), MultiVanDioramaScene.Look.fStop, accuracy: 1e-9)
        XCTAssertEqual(
            MultiVanDioramaScene.fStop(focusDistance: wide.focusDistance) * wide.focusDistance,
            MultiVanDioramaScene.Look.fStop * tall.focusDistance,
            accuracy: 1e-9
        )
    }

    func testDragsTurnTheTableWithinThePrototypesLimits() {
        let rest = MultiVanDioramaOrbit.resting
        let turned = rest.dragged(by: CGSize(width: 50, height: 25))
        XCTAssertEqual(turned.yaw, rest.yaw - 0.3, accuracy: 1e-12)
        XCTAssertEqual(turned.pitch, rest.pitch + 0.1, accuracy: 1e-12)
        XCTAssertEqual(rest.dragged(by: CGSize(width: -1000, height: 1000)), MultiVanDioramaOrbit(yaw: 0.85, pitch: 1.3))
        XCTAssertEqual(rest.dragged(by: CGSize(width: 1000, height: -1000)), MultiVanDioramaOrbit(yaw: -0.85, pitch: 0.45))

        // Turning keeps the framing; turning back to rest restores it exactly.
        let framed = MultiVanDioramaCamera.framed(in: CGSize(width: 360, height: 460))
        let orbited = framed.orbited(turned)
        XCTAssertEqual(orbited.distance, framed.distance)
        XCTAssertEqual(orbited.pan, framed.pan)
        XCTAssertEqual(orbited.yaw, turned.yaw)
        XCTAssertEqual(orbited.pitch, turned.pitch)
        XCTAssertEqual(framed.orbited(.resting), framed)
    }

    func testPinchesZoomTowardsTheFingersWithinTheFramedView() {
        let size = CGSize(width: 360, height: 460)
        let framed = MultiVanDioramaCamera.framed(in: size)
        let rest = MultiVanDioramaOrbit.resting

        // A pinch in the middle moves straight in.
        let centred = rest.pinched(by: 2, anchor: CGPoint(x: 0.5, y: 0.5), in: size)
        XCTAssertEqual(centred.zoom, 2)
        XCTAssertEqual(centred.zoomCentre, .zero)
        XCTAssertEqual(framed.orbited(centred).distance, framed.distance / 2, accuracy: 1e-9)

        // The spot under the fingers stays put.
        let anchor = CGPoint(x: 0.7, y: 0.4)
        let spot = MultiVanDioramaGeometry.world(gridX: 2.6, gridY: 3.6)
        let before = framed.orbited(rest)
        let after = framed.orbited(rest.pinched(by: 1.5, anchor: anchor, in: size))
        let under = { (camera: MultiVanDioramaCamera) -> CGPoint? in camera.viewPoint(for: spot, in: size) }
        let fingers = CGPoint(x: anchor.x * size.width, y: anchor.y * size.height)
        if let start = under(before), let end = under(after) {
            // Not exact in perspective; within a few points of where the zoom pulls it.
            let expected = CGPoint(x: fingers.x + (start.x - fingers.x) * 1.5, y: fingers.y + (start.y - fingers.y) * 1.5)
            XCTAssertEqual(end.x, expected.x, accuracy: 4)
            XCTAssertEqual(end.y, expected.y, accuracy: 4)
        } else {
            XCTFail("spot behind the lens")
        }

        // Zoom stays in range, and a corner pinch can't look past the framed view.
        let corner = rest.pinched(by: 10, anchor: CGPoint(x: 0, y: 0), in: size)
        XCTAssertEqual(corner.zoom, MultiVanDioramaOrbit.zoomRange.upperBound)
        let reach = 1 - 1 / corner.zoom
        XCTAssertEqual(corner.zoomCentre.x, -reach * Double(size.width / size.height), accuracy: 1e-9)
        XCTAssertEqual(corner.zoomCentre.y, reach, accuracy: 1e-9)
        XCTAssertEqual(rest.pinched(by: 0.2, anchor: anchor, in: size), rest)

        // Turning keeps the zoom.
        XCTAssertEqual(centred.dragged(by: CGSize(width: 40, height: 0)).zoom, 2)
    }

    /// The buttons are placed by the renderer-free camera, so it has to agree with
    /// SceneKit's own lens and camera node about where every grid point lands.
    @MainActor
    func testViewPointsMatchSceneKitsProjection() throws {
        let size = CGSize(width: 360, height: 460)
        let scene = MultiVanDioramaScene()
        let lens = try XCTUnwrap(scene.cameraNode.camera)
        let orbits = [
            MultiVanDioramaOrbit.resting,
            .resting.dragged(by: CGSize(width: -120, height: 90)),
            .resting.dragged(by: CGSize(width: 400, height: -400)),
            .resting.pinched(by: 2.5, anchor: CGPoint(x: 0.3, y: 0.7), in: size).dragged(by: CGSize(width: 80, height: 40)),
        ]
        for orbit in orbits {
            let camera = MultiVanDioramaCamera.framed(in: size).orbited(orbit)
            scene.setCamera(camera)
            let clip = simd_float4x4(lens.projectionTransform(withViewportSize: size)) * scene.cameraNode.simdWorldTransform.inverse
            for x in 0...4 {
                for y in 0...6 {
                    let point = MultiVanDioramaGeometry.world(gridX: Double(x), gridY: Double(y), height: MultiVanDioramaGeometry.dialFaceHeight)
                    let projected = clip * SIMD4<Float>(Float(point.x), Float(point.y), Float(point.z), 1)
                    let ndc = SIMD2<Float>(projected.x, projected.y) / projected.w
                    let actual = try XCTUnwrap(camera.viewPoint(for: point, in: size))
                    let label = "\(orbit) at (\(x), \(y))"
                    XCTAssertEqual(actual.x, CGFloat(ndc.x + 1) / 2 * size.width, accuracy: 0.5, label)
                    XCTAssertEqual(actual.y, CGFloat(1 - ndc.y) / 2 * size.height, accuracy: 0.5, label)
                }
            }
        }
    }

    func testFramingFitsTheSlabBetweenTheCoveredStrips() throws {
        let inset = 10.0
        // A full-screen phone under a HUD and a control bar, and the same view
        // with overlays too tall to honour in full.
        let cases: [(CGSize, MultiVanDioramaCamera.Covered)] = [
            (CGSize(width: 393, height: 852), .init(top: 230, bottom: 120)),
            (CGSize(width: 852, height: 393), .init(top: 200, bottom: 110)),
        ]
        for (size, requested) in cases {
            let covered = requested.fitted(toHeight: size.height)
            XCTAssertLessThanOrEqual(covered.top + covered.bottom, size.height * 0.5 + 1e-9)
            let camera = MultiVanDioramaCamera.framed(in: size, inset: inset, covered: requested)
            let points = try MultiVanDioramaGeometry.fitPoints.map { try XCTUnwrap(camera.viewPoint(for: $0, in: size)) }
            let ys = points.map(\.y), xs = points.map(\.x)
            let label = "\(size)"
            XCTAssertGreaterThanOrEqual(ys.min()!, covered.top + inset - 0.01, label)
            XCTAssertLessThanOrEqual(ys.max()!, size.height - covered.bottom - inset + 0.01, label)
            XCTAssertGreaterThanOrEqual(xs.min()!, inset - 0.01, label)
            XCTAssertLessThanOrEqual(xs.max()!, size.width - inset + 0.01, label)
            // Centred in the open band.
            XCTAssertEqual((ys.max()! + ys.min()!) / 2, (covered.top + size.height - covered.bottom) / 2, accuracy: 1, label)
            XCTAssertEqual((xs.max()! + xs.min()!) / 2, size.width / 2, accuracy: 1, label)
        }
        // Nothing covered frames exactly as before.
        let size = CGSize(width: 360, height: 460)
        XCTAssertEqual(MultiVanDioramaCamera.framed(in: size, covered: .init()), MultiVanDioramaCamera.framed(in: size))
    }

    func testOverheadViewLaysTheLawnWhereTheFlatBoardDrawsIt() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_014" })
        // Full screen under a HUD and controls, as wide and as tall as the band
        // allows; and a stacked board with nothing covered.
        let cases: [(CGSize, MultiVanDioramaCamera.Covered, Double)] = [
            (CGSize(width: 393, height: 852), .init(top: 230, bottom: 120), 16),
            (CGSize(width: 393, height: 600), .init(top: 150, bottom: 110), 16),
            (CGSize(width: 360, height: 460), .init(), 0),
        ]
        for (size, covered, sideInset) in cases {
            let camera = MultiVanDioramaCamera.overhead(
                in: size, covered: covered, sideInset: sideInset, edgeInset: Double(MultiVanSwitchButton.hitSize / 2)
            )
            // The gameplay screen pads the flat board by the covered strips and the side inset.
            let rect = CGRect(
                x: sideInset, y: covered.top,
                width: size.width - 2 * sideInset, height: size.height - covered.top - covered.bottom
            )
            let layout = MultiVanBoardView.boardLayout(level: level, size: rect.size)
            for node in level.graph.nodes {
                let flat = try XCTUnwrap(layout.pointsByNodeID[node.id])
                let overhead = try XCTUnwrap(camera.viewPoint(for: MultiVanDioramaGeometry.world(gridX: node.x, gridY: node.y), in: size))
                let label = "\(size) \(node.id)"
                XCTAssertEqual(overhead.x, flat.x + rect.minX, accuracy: 2, label)
                XCTAssertEqual(overhead.y, flat.y + rect.minY, accuracy: 2, label)
            }
        }
    }

    func testBlendingCamerasRunsFromOneToTheOther() {
        let size = CGSize(width: 393, height: 852)
        let table = MultiVanDioramaCamera.framed(in: size)
        let overhead = MultiVanDioramaCamera.overhead(in: size, covered: .init(), sideInset: 16, edgeInset: 22)
        XCTAssertEqual(table.blended(to: overhead, by: 0), table)
        let end = table.blended(to: overhead, by: 1)
        XCTAssertEqual(end.pitch, overhead.pitch, accuracy: 1e-12)
        XCTAssertEqual(end.yaw, overhead.yaw, accuracy: 1e-12)
        XCTAssertEqual(end.distance, overhead.distance, accuracy: 1e-9)
        XCTAssertEqual(end.position.x, overhead.position.x, accuracy: 1e-9)
        XCTAssertEqual(end.position.z, overhead.position.z, accuracy: 1e-9)
        let middle = table.blended(to: overhead, by: 0.5)
        XCTAssertEqual(middle.pitch, (table.pitch + overhead.pitch) / 2, accuracy: 1e-12)
    }

    func testFramingAnEmptyViewLeavesTheCameraAlone() {
        var camera = MultiVanDioramaCamera()
        camera.frame(MultiVanDioramaGeometry.fitPoints, in: .zero, inset: 10)
        XCTAssertEqual(camera, MultiVanDioramaCamera())
    }

    func testRandomMatchesThePrototypesMulberry32() {
        // Values from the HTML prototype's mulberry32(3).
        var random = MultiVanDioramaRandom(seed: 3)
        XCTAssertEqual(random.next(), 0.7202267837710679, accuracy: 1e-12)
        XCTAssertEqual(random.next(), 0.03866216051392257, accuracy: 1e-12)
        XCTAssertEqual(random.next(), 0.4561921926215291, accuracy: 1e-12)
    }

    @MainActor
    func testLoadingRebuildsPiecesOnlyForANewLevel() throws {
        let levels = try MultiVanLevelRepository().loadAllLevels()
        let level12 = try XCTUnwrap(levels.first { $0.id == "level_014" })
        let level4 = try XCTUnwrap(levels.first { $0.id == "level_004" })
        let scene = MultiVanDioramaScene()
        let graph12 = try MultiVanEngine(level: level12).runtimeGraph
        scene.load(level12, graph: graph12)
        let firstHouse = try XCTUnwrap(scene.houses[level12.houses[0].nodeID])
        XCTAssertEqual(scene.houses.count, level12.houses.count)
        XCTAssertEqual(scene.vans.count, level12.vans.count)
        XCTAssertEqual(scene.dials.count, MultiVanBoardRules.switchNodes(in: graph12).count)
        XCTAssertEqual(scene.roadblocks.count, MultiVanBoardRules.barrierNodes(in: graph12, houses: level12.houses).count)
        scene.load(level12, graph: graph12)
        XCTAssertTrue(scene.houses[level12.houses[0].nodeID] === firstHouse, "a retry keeps the pieces")

        let graph4 = try MultiVanEngine(level: level4).runtimeGraph
        scene.load(level4, graph: graph4)
        XCTAssertEqual(scene.levelID, "level_004")
        XCTAssertNil(firstHouse.parent)
        XCTAssertEqual(scene.houses.count, level4.houses.count)
        XCTAssertEqual(scene.vans.count, level4.vans.count)
        XCTAssertFalse(scene.roadblocks.isEmpty, "level 4 has a dead end")
        let pieces = scene.houses.count + scene.deliveredBadges.count + scene.vans.count + scene.dials.count + scene.roadblocks.count
            + scene.sceneryNodes.count + (scene.pondNode == nil ? 0 : 1)
        XCTAssertFalse(scene.sceneryNodes.isEmpty, "level 4's scenery replaced level 12's")
        XCTAssertEqual(scene.vans.values.first?.parent?.childNodes.count, pieces)
    }

    // MARK: - MW-05 pieces

    func testYawTurnsAPiecesFrontToItsHeading() {
        // A piece's front is +z; yaw θ turns it to (sin θ, 0, cos θ).
        func front(_ yaw: Double) -> SIMD3<Double> { SIMD3(sin(yaw), 0, cos(yaw)) }
        let cases: [(RoadVector, SIMD3<Double>)] = [
            (RoadVector(x: 0, y: 1), SIMD3(0, 0, -1)), // up the board, away from the lens
            (RoadVector(x: 0, y: -1), SIMD3(0, 0, 1)),
            (RoadVector(x: 1, y: 0), SIMD3(1, 0, 0)),
            (RoadVector(x: -2, y: 0), SIMD3(-1, 0, 0)),
        ]
        for (heading, expected) in cases {
            let turned = front(MultiVanDioramaGeometry.yaw(facing: heading))
            XCTAssertEqual(simd_distance(turned, expected), 0, accuracy: 1e-12, "\(heading)")
        }
        // Screen angles run clockwise with y down; both forms agree.
        for angle in stride(from: -Double.pi, through: .pi, by: .pi / 6) {
            let grid = RoadVector(x: cos(angle), y: -sin(angle))
            XCTAssertEqual(
                MultiVanDioramaGeometry.yaw(screenAngle: angle).remainder(dividingBy: 2 * .pi),
                MultiVanDioramaGeometry.yaw(facing: grid).remainder(dividingBy: 2 * .pi), accuracy: 1e-12
            )
            let direction = MultiVanDioramaGeometry.worldDirection(screenAngle: angle)
            XCTAssertEqual(simd_distance(direction, front(MultiVanDioramaGeometry.yaw(screenAngle: angle))), 0, accuracy: 1e-12)
        }
        let moved = MultiVanDioramaGeometry.offset(RoadPoint(x: 1, y: 2), along: RoadVector(x: 0, y: -3), by: 0.5)
        XCTAssertEqual(moved.x, 1, accuracy: 1e-12)
        XCTAssertEqual(moved.y, 1.5, accuracy: 1e-12)
        XCTAssertEqual(MultiVanDioramaGeometry.offset(RoadPoint(x: 1, y: 2), along: RoadVector(x: 0, y: 0), by: 0.5), RoadPoint(x: 1, y: 2))
    }

    /// Every piece stands on the mark the lawn paints for it and faces the right way:
    /// houses front onto their driveway, vans nose along their first exit, dial
    /// arrows point down the active exit, and cones stand across a closed road.
    @MainActor
    func testPiecesStandOnTheirMarksFacingTheirRoads() throws {
        for level in try MultiVanLevelRepository().loadAllLevels() {
            let engine = try MultiVanEngine(level: level)
            let graph = engine.runtimeGraph
            let scene = MultiVanDioramaScene()
            scene.load(level, graph: graph)
            let features = MultiVanDioramaLawn.Features(level: level, graph: graph)

            for house in features.houses {
                let node = try XCTUnwrap(scene.houses[house.marking.nodeID], level.id)
                let heading = house.marking.heading
                // The front wall's centre, back towards the node, meets the driveway's end.
                let front = node.simdConvertPosition(SIMD3(0, 0, Float(MultiVanDioramaPieces.Measure.houseDepth / 2)), to: nil)
                let drivewayEnd = MultiVanDioramaGeometry.offset(house.marking.point, along: heading, by: MultiVanDioramaLawn.Measure.drivewayLength)
                let world = MultiVanDioramaGeometry.world(gridX: drivewayEnd.x, gridY: drivewayEnd.y)
                XCTAssertLessThan(simd_distance(SIMD3<Double>(front), world), 0.05, "\(level.id) \(house.marking.nodeID)")
            }
            for van in level.vans {
                let node = try XCTUnwrap(scene.vans[van.id], level.id)
                let start = try XCTUnwrap(graph.nodesByID[van.startNodeID])
                XCTAssertLessThan(simd_distance(SIMD3<Double>(node.simdWorldPosition), MultiVanDioramaGeometry.world(gridX: start.x, gridY: start.y)), 1e-5)
                let tangent = try XCTUnwrap(MultiVanBoardRules.departureTangent(from: van.startNodeID, in: graph))
                assertFront(of: node, faces: tangent, "\(level.id) \(van.id)")
            }
            for node in MultiVanBoardRules.switchNodes(in: graph) {
                let dial = try XCTUnwrap(scene.dials[node.id], level.id)
                let pivot = try XCTUnwrap(dial.childNode(withName: MultiVanDioramaPieces.Part.pivot, recursively: false))
                let edge = try XCTUnwrap(node.activeOutgoingEdgeID.flatMap { graph.edgesByID[$0] })
                let expected = MultiVanDioramaGeometry.worldDirection(
                    screenAngle: SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: graph)
                )
                let tip = pivot.simdConvertVector(SIMD3(1, 0, 0), to: nil)
                XCTAssertLessThan(simd_distance(SIMD3<Double>(simd_normalize(tip)), expected), 1e-5, "\(level.id) \(node.id)")
            }
            for barrier in features.barriers {
                let node = try XCTUnwrap(scene.roadblocks[barrier.nodeID], level.id)
                assertFront(of: node, faces: barrier.heading, "\(level.id) \(barrier.nodeID)")
            }
        }
    }

    private func assertFront(of node: SCNNode, faces heading: RoadVector, _ message: String, line: UInt = #line) {
        let front = SIMD3<Double>(simd_normalize(node.simdConvertVector(SIMD3(0, 0, 1), to: nil)))
        let length = hypot(heading.x, heading.y)
        let expected = SIMD3(heading.x / length, 0, -heading.y / length)
        XCTAssertLessThan(simd_distance(front, expected), 1e-5, message, line: line)
    }

    /// Red and blue bodies print the same grey, so the symbol carries the colour in
    /// grayscale. Each symbol's ink must hold strong contrast on white.
    func testSymbolInkReadsOnWhiteInGrayscale() {
        func luminance(_ color: UIColor) -> Double {
            var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
            color.getRed(&r, green: &g, blue: &b, alpha: &a)
            let linear = { (c: CGFloat) -> Double in
                let c = Double(c)
                return c <= 0.04045 ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4)
            }
            return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
        }
        for color in VanColor.allCases {
            let contrast = 1.05 / (luminance(color.dioramaInk) + 0.05)
            XCTAssertGreaterThanOrEqual(contrast, 4.5, "\(color)")
        }
    }

    /// At about the size a van's roof symbol covers on a phone, every pair of
    /// symbols still differs in a good share of its pixels.
    @MainActor
    func testSymbolShapesStayDistinctAtBoardSize() {
        let side = 24
        func mask(_ color: VanColor) -> [Bool] {
            let format = MultiVanDioramaLawn.textureFormat(opaque: true)
            let image = UIGraphicsImageRenderer(size: CGSize(width: side, height: side), format: format).image { context in
                UIColor.white.setFill()
                context.fill(CGRect(x: 0, y: 0, width: side, height: side))
                context.cgContext.setFillColor(UIColor.black.cgColor)
                context.cgContext.addPath(color.dioramaSymbolPath(centre: CGPoint(x: 12, y: 12.6), radius: 7))
                context.cgContext.fillPath()
            }
            let data = image.cgImage!.dataProvider!.data! as Data
            let bytesPerRow = image.cgImage!.bytesPerRow
            return (0..<side * side).map { data[($0 / side) * bytesPerRow + ($0 % side) * 4] < 128 }
        }
        let colors = VanColor.allCases
        for (index, first) in colors.enumerated() {
            for second in colors.dropFirst(index + 1) {
                let a = mask(first), b = mask(second)
                let differing = zip(a, b).filter { $0 != $1 }.count
                let union = zip(a, b).filter { $0 || $1 }.count
                XCTAssertGreaterThan(Double(differing) / Double(union), 0.15, "\(first) vs \(second)")
            }
        }
    }

    @MainActor
    func testDialTintFollowsTheFlatBoardsKnob() throws {
        let dial = MultiVanDioramaPieces.dial(optionAngles: [0, .pi / 2], activeAngle: 0, tint: .ready)
        let face = try XCTUnwrap(dial.childNode(withName: MultiVanDioramaPieces.Part.dialFace, recursively: false)?.geometry?.firstMaterial)
        let arrow = try XCTUnwrap(dial.childNode(withName: MultiVanDioramaPieces.Part.arrow, recursively: true)?.geometry?.firstMaterial)
        let ready = (face.diffuse.contents as? UIColor, arrow.diffuse.contents as? UIColor)
        MultiVanDioramaPieces.setDial(dial, activeAngle: .pi / 2, tint: .live)
        XCTAssertNotEqual(face.diffuse.contents as? UIColor, ready.0)
        XCTAssertEqual(arrow.diffuse.contents as? UIColor, ready.1)
        MultiVanDioramaPieces.setDial(dial, activeAngle: .pi / 2, tint: .locked)
        XCTAssertEqual(face.diffuse.contents as? UIColor, ready.0)
        XCTAssertNotEqual(arrow.diffuse.contents as? UIColor, ready.1)
        // Screen angle π/2 points down the board, towards the lens.
        let pivot = try XCTUnwrap(dial.childNode(withName: MultiVanDioramaPieces.Part.pivot, recursively: false))
        let tip = simd_normalize(pivot.simdConvertVector(SIMD3(1, 0, 0), to: nil))
        XCTAssertEqual(tip.z, 1, accuracy: 1e-5)
    }

    @MainActor
    func testDismantlingTheViewReleasesTheScene() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_014" })
        weak var weakScene: SCNScene?
        weak var weakRenderer: MultiVanDioramaRenderer?
        var view: SCNView?
        autoreleasepool {
            var renderer: MultiVanDioramaRenderer? = MultiVanDioramaRenderer()
            let sceneView = renderer!.view
            sceneView.frame = CGRect(x: 0, y: 0, width: 360, height: 460)
            renderer?.scene.load(level, graph: try! MultiVanEngine(level: level).runtimeGraph)
            renderer?.scene.setCamera(.framed(in: sceneView.bounds.size))
            sceneView.layoutIfNeeded()
            weakScene = renderer?.scene.scene
            weakRenderer = renderer
            MultiVanDioramaSceneView.dismantleUIView(sceneView, coordinator: renderer!)
            XCTAssertNil(sceneView.scene)
            XCTAssertNil(sceneView.pointOfView)
            renderer = nil
            view = sceneView
        }
        XCTAssertNil(weakRenderer)
        XCTAssertNil(weakScene)
        XCTAssertNotNil(view)
    }

    @MainActor
    func testThePreloadKeepsADismantledRendererForTheNextBoard() throws {
        let preload = MultiVanDioramaPreload()
        let renderer = MultiVanDioramaRenderer()
        renderer.preload = preload
        MultiVanDioramaSceneView.dismantleUIView(renderer.view, coordinator: renderer)
        // Parked whole, so the next board draws at once.
        XCTAssertNotNil(renderer.view.scene)
        XCTAssertTrue(preload.hasRenderer)
        // Only one waits; a second is dropped.
        let second = MultiVanDioramaRenderer()
        second.preload = preload
        MultiVanDioramaSceneView.dismantleUIView(second.view, coordinator: second)
        XCTAssertNil(second.view.scene)
        XCTAssertTrue(preload.take() === renderer)
        XCTAssertFalse(preload.hasRenderer)
        XCTAssertNil(preload.take())
    }

    @MainActor
    func testWarmingBuildsTheLevelBeforeTheBoardAsksForIt() async throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_014" })
        let preload = MultiVanDioramaPreload()
        await preload.warm(level, graph: try MultiVanEngine(level: level).runtimeGraph)
        let renderer = try XCTUnwrap(preload.take())
        XCTAssertEqual(renderer.scene.levelID, level.id)
        XCTAssertFalse(renderer.scene.dials.isEmpty)
        XCTAssertTrue(renderer.view.scene === renderer.scene.scene)
        preload.release()
        await preload.warm(level, graph: try MultiVanEngine(level: level).runtimeGraph)
        XCTAssertTrue(preload.hasRenderer)
        preload.release()
        XCTAssertFalse(preload.hasRenderer)
    }

    @MainActor
    func testATapRebuildsOnlyTheTrailsItReroutes() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_014" })
        let engine = try MultiVanEngine(level: level)
        let scene = MultiVanDioramaScene()
        scene.load(level, graph: engine.runtimeGraph)
        let frame = { MultiVanDioramaFrame(engine: engine, systemReduceMotion: true, reducesExtraAnimations: false) }
        scene.sync(frame())
        var checked = false
        for node in MultiVanBoardRules.switchNodes(in: engine.runtimeGraph) {
            let before = scene.trails
            let lines = scene.trailNodes
            XCTAssertEqual(engine.tapSwitch(nodeID: node.id), .accepted)
            scene.sync(frame())
            // Shared lanes and stacked badges mean one van's reroute can move another's line.
            let changed = zip(before, scene.trails).map { $0 != $1 }
            for (index, rerouted) in changed.enumerated() {
                XCTAssertEqual(scene.trailNodes[index] !== lines[index], rerouted, "\(node.id) van \(index)")
                XCTAssertNotNil(scene.trailNodes[index].parent)
            }
            XCTAssertEqual(scene.trailNodes.count, level.vans.count)
            if changed.contains(true), changed.contains(false) { checked = true }
        }
        // Only the rebuilt lines and badges stay in the scene.
        let markers = scene.markerNodes.compactMap { $0 }.count
        XCTAssertEqual(scene.trailNodes.first?.parent?.childNodes.count, level.vans.count + markers)
        XCTAssertTrue(checked, "no tap moved some lines but not others")
    }

    @MainActor
    func testAHandedOverSceneSetsDialsFlippedWhileItWaited() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_014" })
        let engine = try MultiVanEngine(level: level)
        let waiting = MultiVanDioramaScene()
        let showing = MultiVanDioramaScene()
        waiting.load(level, graph: engine.runtimeGraph)
        showing.load(level, graph: engine.runtimeGraph)
        let frame = { MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: false) }
        showing.sync(frame())
        let nodeID = try XCTUnwrap(MultiVanBoardRules.switchNodes(in: engine.runtimeGraph).first?.id)
        XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted)
        let pivot = { (scene: MultiVanDioramaScene) in
            try XCTUnwrap(scene.dials[nodeID]?.childNode(withName: MultiVanDioramaPieces.Part.pivot, recursively: false))
        }
        // On screen the arrow turns to the new exit; handed over, it's already there.
        showing.sync(frame())
        XCTAssertTrue(try pivot(showing).hasActions)
        waiting.prepareForBoard()
        waiting.sync(frame())
        XCTAssertFalse(try pivot(waiting).hasActions)
        // Later flips turn as usual.
        XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted)
        waiting.sync(frame())
        XCTAssertTrue(try pivot(waiting).hasActions)
    }
}
