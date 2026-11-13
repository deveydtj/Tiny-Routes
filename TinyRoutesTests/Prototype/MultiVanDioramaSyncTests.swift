import SceneKit
import XCTest
@testable import TinyRoutes

/// MW-06: the diorama follows the engine exactly as the flat board does. Every
/// level's recorded solution, and its unchanged plan, plays through both: after
/// each step the scene's pieces must stand where the flat board would draw them.
@MainActor
final class MultiVanDioramaSyncTests: XCTestCase {
    private func levels() throws -> [MultiVanLevel] {
        let levels = try MultiVanLevelRepository().loadAllLevels()
        XCTAssertEqual(levels.count, 19)
        return levels
    }

    func testEveryLevelPlaysTheSameOnBothBoards() throws {
        var statuses = Set<String>()
        for level in try levels() {
            let scripts = [
                ("solution", try PrototypeSolutionScript.load(levelID: level.id)),
                ("as authored", PrototypeSolutionScript()),
            ]
            for (name, script) in scripts {
                let scene = MultiVanDioramaScene()
                scene.load(level, graph: try MultiVanEngine(level: level).runtimeGraph)
                var step = 0
                let check = { (engine: MultiVanEngine) in
                    step += 1
                    // Every third frame keeps the corpus quick; the sync carries no history it could skip.
                    guard step.isMultiple(of: 3) || engine.phase != .run else { return }
                    scene.sync(MultiVanDioramaFrame(engine: engine, systemReduceMotion: true, reducesExtraAnimations: false))
                    self.assertScene(scene, matches: engine, "\(level.id) \(name) step \(step)")
                    engine.vans.forEach { statuses.insert("\($0.status)") }
                }
                if name == "solution" {
                    let engine = try PrototypeSolutionRunner.run(level: level, script: script, onStep: check)
                    XCTAssertEqual(engine.outcome, .win, level.id)
                } else {
                    // An untouched plan may loop until the runner gives up; every frame was checked by then.
                    _ = try? PrototypeSolutionRunner.run(level: level, script: script, onStep: check)
                }
            }
        }
        // The corpus reaches every status, so every pose above was checked.
        XCTAssertEqual(statuses, ["waiting", "driving", "parked", "crashed", "stuck", "missingCargo"])
    }

    private func assertScene(_ scene: MultiVanDioramaScene, matches engine: MultiVanEngine, _ label: String) {
        let level = engine.level
        let graph = engine.runtimeGraph

        for van in engine.vans {
            guard let node = scene.vans[van.id] else { return XCTFail("\(label): no van \(van.id)") }
            let world = MultiVanDioramaGeometry.world(gridX: van.position.x, gridY: van.position.y)
            XCTAssertLessThan(simd_distance(SIMD3<Double>(node.simdWorldPosition), world), 1e-4, "\(label) \(van.id)")
            // The flat board turns the van clockwise from screen-up by this angle.
            let startNodeID = level.vans.first { $0.id == van.id }?.startNodeID
            let flat = MultiVanVanView.heading(for: van, startNodeID: startNodeID, graph: graph).radians
            let front = simd_normalize(SIMD3<Double>(node.simdConvertVector(SIMD3(0, 0, 1), to: nil)))
            XCTAssertLessThan(simd_distance(SIMD2(front.x, -front.z), SIMD2(sin(flat), cos(flat))), 1e-4, "\(label) \(van.id) heading")

            let pose = try! XCTUnwrap(node.childNode(withName: MultiVanDioramaPieces.Part.pose, recursively: false))
            switch van.status {
            case .crashed: XCTAssertNotEqual(pose.simdEulerAngles.z, 0, "\(label) \(van.id) tips over")
            case .stuck: XCTAssertNotEqual(pose.simdEulerAngles.y, 0, "\(label) \(van.id) skews")
            case .waiting, .driving, .parked, .missingCargo: XCTAssertEqual(pose.simdEulerAngles, .zero, "\(label) \(van.id) stands straight")
            }
            let chassis = try! XCTUnwrap(pose.childNode(withName: MultiVanDioramaPieces.Part.chassis, recursively: false))
            let signal = engine.phase == .run ? MultiVanVanView.turnSignal(for: van, graph: graph) : nil
            XCTAssertEqual(lampIsAmber(chassis, MultiVanDioramaPieces.Part.leftLamps), signal == .left || van.status == .stuck, "\(label) \(van.id) left lamps")
            XCTAssertEqual(lampIsAmber(chassis, MultiVanDioramaPieces.Part.rightLamps), signal == .right || van.status == .stuck, "\(label) \(van.id) right lamps")
        }

        for control in MultiVanSwitchControl.controls(engine: engine, graph: graph) {
            guard let dial = scene.dials[control.nodeID],
                  let pivot = dial.childNode(withName: MultiVanDioramaPieces.Part.pivot, recursively: false) else {
                return XCTFail("\(label): no dial \(control.nodeID)")
            }
            let tip = simd_normalize(SIMD3<Double>(pivot.simdConvertVector(SIMD3(1, 0, 0), to: nil)))
            let expected = MultiVanDioramaGeometry.worldDirection(screenAngle: control.activeAngle)
            XCTAssertLessThan(simd_distance(tip, expected), 1e-4, "\(label) \(control.nodeID) arrow")
            XCTAssertEqual(tint(of: dial), control.appearance.dialTint, "\(label) \(control.nodeID) tint")
        }

        for house in level.houses {
            let delivered = MultiVanBoardRules.isDelivered(house, vans: engine.vans, graph: graph)
            XCTAssertEqual(scene.deliveredBadges[house.nodeID]?.isHidden, !delivered, "\(label) \(house.nodeID) ✓")
        }

        // The flat board draws a line, trimmed behind a driving van, and its marker
        // for every van still waiting or driving.
        let markers = MultiVanPreviewMarker.make(routes: engine.previewRoutes, vans: level.vans, graph: graph)
        XCTAssertEqual(scene.trails.count, engine.vans.count, label)
        for (index, van) in engine.vans.enumerated() {
            let trail = scene.trails[index]
            let dots = scene.trailNodes[index].childNodes
            XCTAssertEqual(dots.count, trail.dots.count, label)
            let shown = dots.indices.filter { !dots[$0].isHidden }
            let drawsLine = van.status == .waiting || van.status == .driving
            if !drawsLine { XCTAssertTrue(shown.isEmpty, "\(label) \(van.id) has no line") }
            XCTAssertEqual(scene.markerNodes[index]?.isHidden ?? true, !(drawsLine && markers[index] != nil), "\(label) \(van.id) marker")
            XCTAssertEqual(trail.marker, markers[index], label)
            if let marker = markers[index], let node = scene.markerNodes[index] {
                let image = node.geometry?.firstMaterial?.diffuse.contents as? UIImage
                XCTAssertTrue(image === MultiVanDioramaPieces.Texture.badge(.ending(marker.ending, van.color)), "\(label) \(van.id) glyph")
            }
            guard drawsLine else { continue }
            // Nothing behind the van, and every dot ahead of it beyond the clearance.
            let covered = van.status == .driving && van.currentEdgeID == trail.leadEdgeID ? van.distanceAlongEdge : 0
            for dotIndex in dots.indices {
                let ahead = trail.dots[dotIndex].distance >= covered + MultiVanDioramaTrail.clearance
                XCTAssertEqual(!dots[dotIndex].isHidden, ahead, "\(label) \(van.id) dot \(dotIndex)")
            }
            for dotIndex in shown {
                let point = trail.dots[dotIndex].point
                let world = MultiVanDioramaGeometry.world(gridX: point.x, gridY: point.y)
                XCTAssertLessThan(simd_distance(SIMD2(world.x, world.z), SIMD2(Double(dots[dotIndex].simdPosition.x), Double(dots[dotIndex].simdPosition.z))), 1e-4)
            }
        }
    }

    /// A headlamp showing anything but its own colour is signalling.
    private func lampIsAmber(_ chassis: SCNNode, _ side: String) -> Bool {
        let material = chassis.childNode(withName: side, recursively: false)?.childNodes.first?.geometry?.firstMaterial
        return (material?.diffuse.contents as? UIColor) != headlampColour
    }

    private lazy var headlampColour = MultiVanDioramaPieces.van(.red)
        .childNode(withName: MultiVanDioramaPieces.Part.leftLamps, recursively: true)?
        .childNodes.first?.geometry?.firstMaterial?.diffuse.contents as? UIColor

    private lazy var referenceDials = Dictionary(uniqueKeysWithValues: [MultiVanSwitchDialView.Tint.ready, .live, .locked].map {
        ($0, MultiVanDioramaPieces.dial(optionAngles: [], activeAngle: 0, tint: $0))
    })

    private func tint(of dial: SCNNode) -> MultiVanSwitchDialView.Tint? {
        func colours(_ dial: SCNNode) -> [UIColor?] {
            [MultiVanDioramaPieces.Part.dialFace, MultiVanDioramaPieces.Part.arrow].map {
                dial.childNode(withName: $0, recursively: true)?.geometry?.firstMaterial?.diffuse.contents as? UIColor
            }
        }
        return referenceDials.first { colours($0.value) == colours(dial) }?.key
    }

    // MARK: - Trails

    /// Preview dots sit in the same lanes as the flat board's dashes: drawn at the
    /// lawn texture's scale, both offset the same way off the same roads.
    func testTrailLanesMatchTheFlatBoardsDashes() throws {
        for level in try levels() {
            let engine = try MultiVanEngine(level: level)
            let graph = engine.runtimeGraph
            let layout = MultiVanDioramaLawn.layout(for: level)
            let scale = MultiVanDioramaLawn.pixelsPerUnit
            let lanes = MultiVanPreviewLanes.make(routes: engine.previewRoutes)
            let trails = MultiVanDioramaTrail.make(routes: engine.previewRoutes, vans: level.vans, graph: graph)
            let drawings = MultiVanPreviewDrawing.make(routes: engine.previewRoutes, vans: level.vans, graph: graph, layout: layout)
            for (index, route) in engine.previewRoutes.enumerated() {
                let trail = trails[index]
                XCTAssertEqual(trail.color, level.vans[index].color)
                XCTAssertEqual(trail.leadEdgeID, route.edgeIDs.first)
                // Each road's dots start half a gap in and keep the spacing.
                var start = 0.0
                var expected: [MultiVanDioramaTrail.Dot] = []
                var drawn = Set<String>()
                for (position, edgeID) in route.edgeIDs.enumerated() {
                    let road = try XCTUnwrap(graph.edgesByID[edgeID]?.roadPath)
                    let lane = lanes[index][edgeID] ?? 0
                    if position == 0 || drawn.insert(edgeID).inserted {
                        for distance in stride(from: MultiVanDioramaTrail.spacing / 2, to: road.totalLength, by: MultiVanDioramaTrail.spacing) {
                            let point = MultiVanDioramaTrail.lanePoint(on: road, at: distance, offset: lane * MultiVanDioramaTrail.laneWidth)
                            expected.append(.init(point: point, distance: start + distance))
                            let flat = try XCTUnwrap(MultiVanPreviewDrawing.offsetPoint(
                                on: road, at: distance, offset: CGFloat(lane * MultiVanDioramaTrail.laneWidth) * scale, layout: layout
                            ))
                            let painted = try XCTUnwrap(layout.point(for: point))
                            XCTAssertEqual(hypot(flat.x - painted.x, flat.y - painted.y), 0, accuracy: 1e-6, "\(level.id) \(edgeID)")
                        }
                    }
                    start += road.totalLength
                }
                XCTAssertEqual(trail.dots.count, expected.count, level.id)
                for (dot, want) in zip(trail.dots, expected) {
                    XCTAssertEqual(dot.distance, want.distance, accuracy: 1e-9)
                    XCTAssertEqual(hypot(dot.point.x - want.point.x, dot.point.y - want.point.y), 0, accuracy: 1e-9)
                }
                // The line ends where the flat board's does, in its lane.
                XCTAssertEqual(drawings[index].endpoint == nil, trail.endpoint == nil, level.id)
                if let endpoint = trail.endpoint, let edgeID = route.edgeIDs.last, let road = graph.edgesByID[edgeID]?.roadPath {
                    let lane = CGFloat(lanes[index][edgeID] ?? 0) * CGFloat(MultiVanDioramaTrail.laneWidth) * scale
                    let shifted = try XCTUnwrap(MultiVanPreviewDrawing.offsetPoint(on: road, at: road.totalLength, offset: lane, layout: layout))
                    let painted = try XCTUnwrap(layout.point(for: endpoint))
                    XCTAssertEqual(hypot(shifted.x - painted.x, shifted.y - painted.y), 0, accuracy: 1e-6, level.id)
                }
            }
        }
    }

    func testTrimmingFollowsTheVan() {
        let trail = MultiVanDioramaTrail(
            color: .red, leadEdgeID: "a", leadLength: 1,
            dots: stride(from: 0.065, to: 2, by: 0.13).map { .init(point: RoadPoint(x: 0, y: $0), distance: $0) },
            endpoint: RoadPoint(x: 0, y: 2), marker: nil
        )
        func van(_ status: MultiVanVanState.Status, edge: String?, distance: Double) -> MultiVanDioramaFrame.Van {
            .init(id: "v", color: .red, point: RoadPoint(x: 0, y: distance), heading: RoadVector(x: 0, y: 1), status: status,
                  currentEdgeID: edge, distanceAlongEdge: distance, signal: nil, signalIsLit: true, idles: false)
        }
        let first = { (limit: Double) in trail.dots.firstIndex { $0.distance >= limit } }
        XCTAssertEqual(trail.firstVisibleDot(for: nil), first(0.27))
        XCTAssertEqual(trail.firstVisibleDot(for: van(.waiting, edge: nil, distance: 0)), first(0.27))
        XCTAssertEqual(trail.firstVisibleDot(for: van(.driving, edge: "a", distance: 0.5)), first(0.77))
        // A route not yet rebuilt for the van's next road drops its whole lead road.
        XCTAssertEqual(trail.firstVisibleDot(for: van(.driving, edge: "b", distance: 0.1)), first(1.27))
        XCTAssertEqual(trail.firstVisibleDot(for: van(.driving, edge: "a", distance: 1.9)), trail.dots.count)
        for status in [MultiVanVanState.Status.parked, .crashed, .stuck] {
            XCTAssertNil(trail.firstVisibleDot(for: van(status, edge: "a", distance: 1)))
        }
    }

    // MARK: - Motion

    func testMotionSettingDecidesWhetherPiecesAnimate() throws {
        let level = try XCTUnwrap(levels().first { $0.id == "level_002" })
        for reduced in [false, true] {
            let engine = try MultiVanEngine(level: level)
            let scene = MultiVanDioramaScene()
            scene.load(level, graph: engine.runtimeGraph)
            let frame = { MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: reduced) }
            scene.sync(frame())
            let chassis = try XCTUnwrap(scene.vans.values.first?.childNode(withName: MultiVanDioramaPieces.Part.chassis, recursively: true))
            XCTAssertEqual(chassis.action(forKey: "rumble") != nil, !reduced, "a waiting van rumbles unless motion is reduced")

            let node = try XCTUnwrap(MultiVanBoardRules.switchNodes(in: engine.runtimeGraph).first)
            XCTAssertEqual(engine.tapSwitch(nodeID: node.id), .accepted)
            scene.sync(frame())
            let pivot = try XCTUnwrap(scene.dials[node.id]?.childNode(withName: MultiVanDioramaPieces.Part.pivot, recursively: false))
            XCTAssertEqual(pivot.hasActions, !reduced, "the arrow springs round unless motion is reduced")
            // Turning back before the spring settles starts from the last target, not mid-turn.
            XCTAssertEqual(engine.tapSwitch(nodeID: node.id), .accepted)
            scene.sync(frame())
            XCTAssertEqual(pivot.hasActions, !reduced)

            engine.go()
            scene.sync(frame())
            XCTAssertNil(chassis.action(forKey: "rumble"), "a driving van stops rumbling")
        }
    }
}
