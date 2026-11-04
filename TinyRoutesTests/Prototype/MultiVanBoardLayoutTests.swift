import CoreGraphics
import XCTest
#if canImport(UIKit)
import SwiftUI
import UIKit
#endif
@testable import TinyRoutes

final class MultiVanHouseAndBarrierTests: XCTestCase {
    private func engine(vanColor: VanColor, houseColor: VanColor) throws -> MultiVanEngine {
        let graph = RouteGraph(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["road", "blocked"]),
            RouteNode(id: "house", x: 1, y: 1, outgoingEdgeIDs: []),
            RouteNode(id: "dead", x: 2, y: 0, outgoingEdgeIDs: [])
        ], edges: [
            RouteEdge(id: "road", fromNodeID: "start", toNodeID: "house"),
            RouteEdge(id: "blocked", fromNodeID: "start", toNodeID: "dead")
        ])
        let json: [String: Any] = [
            "id": "markers", "name": "Markers",
            "graph": try JSONSerialization.jsonObject(with: JSONEncoder().encode(graph)),
            "vans": [["id": "van", "color": vanColor.rawValue, "startNodeID": "start"]],
            "houses": [["nodeID": "house", "color": houseColor.rawValue]],
            "initialSwitchEdges": [:], "parChanges": 0
        ]
        return try MultiVanEngine(level: JSONDecoder().decode(
            MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json)
        ))
    }

    func testAllColorsShowDeliveryOnlyAfterMatchingArrivalAndClearOnRetry() throws {
        for (color, symbol) in [(VanColor.red, "●"), (.blue, "▲"), (.yellow, "■"), (.green, "★")] {
            XCTAssertEqual(color.symbol, symbol)
            let engine = try engine(vanColor: color, houseColor: color)
            let house = try XCTUnwrap(engine.level.houses.first)
            func delivered() -> Bool {
                MultiVanBoardRules.isDelivered(house, vans: engine.vans, graph: engine.runtimeGraph)
            }
            XCTAssertFalse(delivered())
            engine.go()
            engine.advance(by: 0.25)
            XCTAssertFalse(delivered())
            for _ in 0..<20 { engine.advance(by: 0.25) }
            XCTAssertEqual(engine.outcome, .win)
            XCTAssertTrue(delivered())
            XCTAssertFalse(MultiVanBoardRules.isDelivered(
                MultiVanHouse(nodeID: "dead", color: color), vans: engine.vans, graph: engine.runtimeGraph
            ))
            engine.retry()
            XCTAssertFalse(delivered())
        }
    }

    func testWrongColorParkedArrivalDoesNotShowDelivery() throws {
        let engine = try engine(vanColor: .red, houseColor: .blue)
        engine.go()
        for _ in 0..<20 { engine.advance(by: 0.25) }
        XCTAssertEqual(engine.vans.first?.status, .parked)
        XCTAssertEqual(engine.outcome, .failWrongHouse(vanID: "van", houseNodeID: "house"))
        XCTAssertFalse(MultiVanBoardRules.isDelivered(
            engine.level.houses[0], vans: engine.vans, graph: engine.runtimeGraph
        ))
    }

    func testMarkersUseMV12NodesAndBarrierClosesOnlyNonHouseDeadEnd() throws {
        let engine = try engine(vanColor: .red, houseColor: .red)
        let graph = engine.runtimeGraph
        let barriers = MultiVanBoardRules.barrierNodes(in: graph, houses: engine.level.houses)
        XCTAssertEqual(barriers.map(\.id), ["dead"])
        let node = try XCTUnwrap(barriers.first)
        let angle = MultiVanBoardRules.barrierHeading(at: node, in: graph).radians
        // A road travelling right needs a vertical cap after MV-12's Y projection.
        XCTAssertEqual(angle, .pi / 2, accuracy: 1e-9)
        for size in [CGSize(width: 320, height: 400), CGSize(width: 430, height: 660)] {
            let layout = MultiVanBoardView.boardLayout(level: engine.level, size: size)
            for id in ["house", "dead"] {
                let marker = try XCTUnwrap(graph.nodesByID[id])
                XCTAssertEqual(layout.pointsByNodeID[id], layout.point(for: RoadPoint(x: marker.x, y: marker.y)))
            }
        }
    }
}

final class MultiVanVanHeadingTests: XCTestCase {
    func testHeadingsFollowProjectedRoadTangentsIncludingCurvesAndEdgeJoins() {
        let layout = BoardLayout(pointsByNodeID: [:], coordinateScale: 50, maxY: 6)
        let origin = RoadPoint(x: 0, y: 0)
        let roads = [
            RoadPath.make(from: origin, to: RoadPoint(x: 1, y: 0)),
            RoadPath.make(from: origin, to: RoadPoint(x: -1, y: 0)),
            RoadPath.make(from: origin, to: RoadPoint(x: 0, y: 1)),
            RoadPath.make(from: origin, to: RoadPoint(x: 0, y: -1)),
            RoadPath.make(from: origin, to: RoadPoint(x: 1, y: 1)),
            RoadPath.make(from: origin, to: RoadPoint(x: -1, y: -1), shape: .verticalFirst)
        ]
        for road in roads {
            for fraction in [0.0, 0.25, 0.5, 0.75, 0.999] {
                let distance = road.totalLength * fraction
                let heading = MultiVanVanView.heading(for: road.tangent(atDistance: distance)).radians
                let start = layout.point(for: road.point(atDistance: distance))!
                let next = layout.point(for: road.point(atDistance: distance + 0.00001))!
                let dx = Double(next.x - start.x)
                let dy = Double(next.y - start.y)
                let magnitude = hypot(dx, dy)
                // Rotating screen-up (0, -1) by heading must follow the road.
                XCTAssertEqual(sin(heading), dx / magnitude, accuracy: 0.0001)
                XCTAssertEqual(-cos(heading), dy / magnitude, accuracy: 0.0001)
            }
        }
        let incoming = roads[4]
        let outgoing = RoadPath.make(from: RoadPoint(x: 1, y: 1), to: RoadPoint(x: 1, y: 2))
        XCTAssertEqual(MultiVanVanView.heading(for: incoming.tangent(atDistance: incoming.totalLength)).radians,
                       MultiVanVanView.heading(for: outgoing.tangent(atDistance: 0)).radians, accuracy: 1e-9)
        for vector in [RoadVector(x: 0, y: 0), RoadVector(x: .nan, y: 1),
                       RoadVector(x: 1, y: .infinity)] {
            XCTAssertEqual(MultiVanVanView.heading(for: vector).radians, 0)
        }
    }

    func testFourVansKeepIndependentWaitingDrivingAndParkedHeadings() throws {
        let colors = ["red", "blue", "yellow", "green"]
        let starts = [(0.0, 0.0), (4.0, 6.0), (0.0, 2.0), (4.0, 4.0)]
        let ends = [(0.0, 1.0), (4.0, 5.0), (1.0, 2.0), (3.0, 4.0)]
        let expected = [0.0, Double.pi, Double.pi / 2, -Double.pi / 2]
        let nodes = starts.indices.flatMap { i in
            [RouteNode(id: "s\(i)", x: starts[i].0, y: starts[i].1, outgoingEdgeIDs: ["e\(i)"]),
             RouteNode(id: "h\(i)", x: ends[i].0, y: ends[i].1, outgoingEdgeIDs: [])]
        }
        let edges = starts.indices.map { RouteEdge(id: "e\($0)", fromNodeID: "s\($0)", toNodeID: "h\($0)") }
        let graph = try JSONSerialization.jsonObject(with: JSONEncoder().encode(RouteGraph(nodes: nodes, edges: edges)))
        let json: [String: Any] = [
            "id": "headings", "name": "Headings", "graph": graph,
            "vans": colors.enumerated().map { i, color -> [String: Any] in
                ["id": color, "color": color, "startNodeID": "s\(i)", "departDelay": 0.25]
            },
            "houses": colors.enumerated().map { ["nodeID": "h\($0.offset)", "color": $0.element] },
            "initialSwitchEdges": [:], "parChanges": 0
        ]
        let engine = try MultiVanEngine(level: JSONDecoder().decode(
            MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json)
        ))
        func check() {
            let positions = engine.vans.map(\.position)
            for i in engine.vans.indices {
                let heading = MultiVanVanView.heading(for: engine.vans[i], startNodeID: "s\(i)",
                                                     graph: engine.runtimeGraph).radians
                XCTAssertEqual(heading, expected[i], accuracy: 1e-9)
            }
            XCTAssertEqual(engine.vans.map(\.position), positions, "Rendering must not move vans")
            XCTAssertEqual(Set(positions.map { "\($0.x),\($0.y)" }).count, 4)
        }
        check()
        engine.go()
        XCTAssertTrue(engine.vans.allSatisfy { $0.status == .waiting })
        check()
        engine.advance(by: 0.25)
        engine.advance(by: 0.25)
        XCTAssertTrue(engine.vans.allSatisfy { $0.status == .driving })
        check()
        for _ in 0..<4 { engine.advance(by: 0.25) }
        XCTAssertTrue(engine.vans.allSatisfy { $0.status == .parked })
        check()
        engine.retry()
        check()
    }
}

final class MultiVanTurnSignalTests: XCTestCase {
#if canImport(UIKit)
    @MainActor
    func testTurningVanFlashesItsFrontAndRearLamps() throws {
        func render(lit: Bool) throws -> UIImage {
            let renderer = ImageRenderer(content:
                MultiVanVanView(color: .red, length: 28, status: .driving,
                                reducesExtraAnimations: true,
                                turnSignal: .right, signalIsLit: lit)
                    .padding(12).background(Color(white: 0.93))
            )
            renderer.scale = 3
            return try XCTUnwrap(renderer.uiImage)
        }
        let on = try render(lit: true)
        let off = try render(lit: false)
        for (name, image) in [("Blinker on", on), ("Blinker off", off)] {
            let attachment = XCTAttachment(image: image)
            attachment.name = name
            attachment.lifetime = .keepAlways
            add(attachment)
        }
        // The lamp centers belong to the headlights/taillights, not separate corner dots.
        func pixel(_ image: UIImage, x: Double, y: Double) throws -> [UInt8] {
            let cgImage = try XCTUnwrap(image.cgImage)
            let data = try XCTUnwrap(cgImage.dataProvider?.data)
            let bytes = try XCTUnwrap(CFDataGetBytePtr(data))
            let index = Int(y * 3) * cgImage.bytesPerRow + Int(x * 3) * 4
            return Array(UnsafeBufferPointer(start: bytes + index, count: 3))
        }
        for end in [-1.0, 1.0] {
            let x = 12 + 28 * 0.75 / 2 + 28 * 0.17
            let y = 12 + 28 / 2 + 28 * 0.4 * end
            let change = zip(try pixel(on, x: x, y: y), try pixel(off, x: x, y: y))
                .reduce(0) { $0 + abs(Int($1.0) - Int($1.1)) }
            XCTAssertGreaterThan(change, 60, "Both front and rear lamps must visibly flash")
        }
    }
#endif

    private func engine(
        start: RoadPoint = RoadPoint(x: 0, y: -2), end: RoadPoint,
        junction: Bool = true, merge: Bool = false, reverseRoads: Bool = false
    ) throws -> MultiVanEngine {
        var nodes = [
            RouteNode(id: "start", x: start.x, y: start.y, outgoingEdgeIDs: ["approach"]),
            RouteNode(id: "junction", x: 0, y: 0, outgoingEdgeIDs: ["exit"]),
            RouteNode(id: "house", x: end.x, y: end.y, outgoingEdgeIDs: [])
        ]
        var edges = [
            RouteEdge(id: "approach", fromNodeID: "start", toNodeID: "junction"),
            RouteEdge(id: "exit", fromNodeID: "junction", toNodeID: "house")
        ]
        if junction {
            nodes.append(RouteNode(id: "other", x: -end.x, y: -end.y,
                                   outgoingEdgeIDs: merge ? ["other"] : []))
            edges.append(RouteEdge(id: "other", fromNodeID: merge ? "other" : "junction",
                                   toNodeID: merge ? "junction" : "other"))
            if !merge { nodes[1].outgoingEdgeIDs.append("other") }
        }
        if reverseRoads {
            nodes[1].outgoingEdgeIDs.append("reverseApproach")
            nodes[2].outgoingEdgeIDs.append("reverseExit")
            edges += [RouteEdge(id: "reverseApproach", fromNodeID: "junction", toNodeID: "start"),
                      RouteEdge(id: "reverseExit", fromNodeID: "house", toNodeID: "junction")]
        }
        let graph = RouteGraph(nodes: nodes, edges: edges)
        let json: [String: Any] = [
            "id": "signals", "name": "Signals",
            "graph": try JSONSerialization.jsonObject(with: JSONEncoder().encode(graph)),
            "vans": [["id": "van", "color": "red", "startNodeID": "start"]],
            "houses": [["nodeID": "house", "color": "red"]],
            "initialSwitchEdges": [:], "parChanges": 0, "liveSwitchNodeIDs": ["junction"]
        ]
        var tuning = MultiVanTuning.default
        tuning.vanSpeed = 1
        tuning.liveSwitchLockRadius = 0
        return try MultiVanEngine(level: JSONDecoder().decode(
            MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json)
        ), tuning: tuning)
    }

    private func signal(_ engine: MultiVanEngine) -> MultiVanVanView.TurnSignal? {
        MultiVanVanView.turnSignal(for: engine.vans[0], graph: engine.runtimeGraph)
    }

    func testLevelTwoRedVanSignalsRightBeforeAndThroughItsIntersection() throws {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == "level_002" })
        let engine = try MultiVanEngine(level: level)
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
        engine.go()
        var flashes = 0
        var wasLit = false
        var sawDepartureFlash = false
        var sawDepartureOff = false
        for _ in 0..<150 {
            engine.advance(by: 0.025)
            guard let turn = signal(engine) else { wasLit = false; continue }
            XCTAssertEqual(turn, .right)
            let lit = MultiVanVanView.signalIsLit(for: engine.vans[0], graph: engine.runtimeGraph,
                                                speed: engine.tuning.vanSpeed)
            if lit && !wasLit { flashes += 1 }
            wasLit = lit
            if engine.vans[0].currentEdgeID == "to_house" {
                sawDepartureFlash = sawDepartureFlash || lit
                sawDepartureOff = sawDepartureOff || !lit
            }
        }
        XCTAssertGreaterThanOrEqual(flashes, 2, "The driver should see repeated flashes for level two's turn")
        XCTAssertTrue(sawDepartureFlash)
        XCTAssertTrue(sawDepartureOff, "The lamps must keep blinking through the turn")
        XCTAssertNil(signal(engine), "Cancel after the van clears the intersection")
    }

    func testLeftAndRightSignalsApproachCrossAndClearJunctionFromEveryHeading() throws {
        for direction in [RoadPoint(x: 0, y: 1), RoadPoint(x: 1, y: 0),
                          RoadPoint(x: 0, y: -1), RoadPoint(x: -1, y: 0)] {
            for side in [MultiVanVanView.TurnSignal.left, .right] {
                let sign = side == .left ? 1.0 : -1.0
                let engine = try engine(
                    start: RoadPoint(x: -2 * direction.x, y: -2 * direction.y),
                    end: RoadPoint(x: -2 * direction.y * sign, y: 2 * direction.x * sign)
                )
                XCTAssertNil(signal(engine))
                engine.go()
                engine.advance(by: 0.25)
                XCTAssertNil(signal(engine), "Do not signal far from a junction")
                engine.advance(by: 1.05)
                XCTAssertEqual(signal(engine), side)
                engine.advance(by: 0.75)
                XCTAssertEqual(engine.vans[0].currentEdgeID, "exit")
                XCTAssertEqual(signal(engine), side, "Keep signalling through the turn")
                engine.advance(by: 0.65)
                XCTAssertNil(signal(engine), "Cancel after clearing the junction")
                engine.advance(by: 2)
                XCTAssertEqual(engine.outcome, .win)
                XCTAssertNil(signal(engine))
                engine.retry()
                XCTAssertNil(signal(engine))
            }
        }
    }

    func testBendsStraightCrossingsAndUTurnsDoNotSignal() throws {
        let engines = [
            try engine(end: RoadPoint(x: -2, y: 0), junction: false),
            try engine(end: RoadPoint(x: -2, y: 0), junction: false, reverseRoads: true),
            try engine(end: RoadPoint(x: 0, y: 2)),
            try engine(end: RoadPoint(x: 0, y: -2)),
            // A bend inside an edge is quiet even when that edge leads to a junction.
            try engine(start: RoadPoint(x: -2, y: -2), end: RoadPoint(x: 0, y: 2))
        ]
        for engine in engines {
            engine.go()
            for _ in 0..<600 {
                XCTAssertNil(signal(engine))
                engine.advance(by: 1.0 / 60)
            }
        }
    }

    func testMergeSignalsAndLiveRouteChangesUseTheActualExitAndStopResetsHistory() throws {
        let merge = try engine(end: RoadPoint(x: -2, y: 0), merge: true)
        merge.go()
        merge.advance(by: 1.3)
        XCTAssertEqual(signal(merge), .left)

        let engine = try engine(end: RoadPoint(x: -2, y: 0))
        engine.go()
        engine.advance(by: 1.3)
        XCTAssertEqual(signal(engine), .left)
        XCTAssertEqual(engine.tapSwitch(nodeID: "junction"), .accepted)
        XCTAssertEqual(signal(engine), .right)
        engine.advance(by: 0.75)
        XCTAssertEqual(signal(engine), .right)
        engine.stop()
        XCTAssertNil(signal(engine))
        XCTAssertNil(engine.vans[0].previousEdgeID)
    }
}

final class MultiVanBoardLayoutTests: XCTestCase {
    private let grid = (0...6).flatMap { y in (0...4).map { x in
        RouteNode(id: "\(x),\(y)", x: Double(x), y: Double(y), outgoingEdgeIDs: [])
    } }

    private func level(nodes: [RouteNode]) throws -> MultiVanLevel {
        let graph = String(decoding: try JSONEncoder().encode(RouteGraph(nodes: nodes)), as: UTF8.self)
        return try JSONDecoder().decode(MultiVanLevel.self, from: Data("""
        {"id":"layout", "name":"Layout", "graph":\(graph), "vans":[], "houses":[],
         "initialSwitchEdges":{}, "parChanges":0}
        """.utf8))
    }

    private func checkFit(in rect: CGRect, file: StaticString = #filePath, line: UInt = #line) throws {
        let layout = MultiVanBoardLayout.make(level: try level(nodes: grid), in: rect)
        let scale = try XCTUnwrap(layout.coordinateScale)
        XCTAssertEqual(scale, min(rect.width / 5, rect.height / 7), accuracy: 1e-9, file: file, line: line)
        XCTAssertNil(layout.cameraPlan, file: file, line: line)
        XCTAssertNil(layout.extents, file: file, line: line)
        XCTAssertEqual(layout.pointsByNodeID.count, 35, file: file, line: line)
        // Check every point, including all four corners, and the shared road projection.
        for node in grid {
            let point = try XCTUnwrap(layout.pointsByNodeID[node.id])
            XCTAssertTrue(rect.contains(point), file: file, line: line)
            XCTAssertEqual(point, layout.point(for: RoadPoint(x: node.x, y: node.y)), file: file, line: line)
        }
        let bottomLeft = try XCTUnwrap(layout.pointsByNodeID["0,0"])
        let topRight = try XCTUnwrap(layout.pointsByNodeID["4,6"])
        let center = try XCTUnwrap(layout.pointsByNodeID["2,3"])
        XCTAssertLessThan(topRight.y, bottomLeft.y, file: file, line: line)
        XCTAssertEqual(center.x, rect.midX, accuracy: 1e-9, file: file, line: line)
        XCTAssertEqual(center.y, rect.midY, accuracy: 1e-9, file: file, line: line)
        XCTAssertEqual((bottomLeft.x + topRight.x) / 2, rect.midX, accuracy: 1e-9, file: file, line: line)
        XCTAssertEqual((bottomLeft.y + topRight.y) / 2, rect.midY, accuracy: 1e-9, file: file, line: line)
        for y in 0...6 {
            for x in 0...4 {
                let point = try XCTUnwrap(layout.pointsByNodeID["\(x),\(y)"])
                if x < 4 {
                    let right = try XCTUnwrap(layout.pointsByNodeID["\(x + 1),\(y)"])
                    XCTAssertEqual(right.x - point.x, scale, accuracy: 1e-9, file: file, line: line)
                }
                if y < 6 {
                    let above = try XCTUnwrap(layout.pointsByNodeID["\(x),\(y + 1)"])
                    XCTAssertEqual(point.y - above.y, scale, accuracy: 1e-9, file: file, line: line)
                }
            }
        }
        let margins = [bottomLeft.x - rect.minX, rect.maxX - topRight.x,
                       topRight.y - rect.minY, rect.maxY - bottomLeft.y]
        // The constrained axis has exactly half a unit; the other can have more.
        XCTAssertEqual(try XCTUnwrap(margins.min()), scale / 2, accuracy: 1e-9, file: file, line: line)
        for margin in margins {
            XCTAssertGreaterThanOrEqual(margin + 1e-9, scale / 2, file: file, line: line)
        }
        let fractional = try XCTUnwrap(layout.point(for: RoadPoint(x: 2.25, y: 3.5)))
        XCTAssertEqual(fractional.x, rect.midX + scale * 0.25, accuracy: 1e-9, file: file, line: line)
        XCTAssertEqual(fractional.y, rect.midY - scale * 0.5, accuracy: 1e-9, file: file, line: line)
    }

    func testIPhoneSEAvailableBoardRectangle() throws {
        try checkFit(in: CGRect(x: 0, y: 0, width: 320, height: 400))
    }

    func testIPhoneProMaxAvailableBoardRectangle() throws {
        try checkFit(in: CGRect(x: 0, y: 0, width: 430, height: 660))
    }

    func testNonzeroOrigin() throws {
        try checkFit(in: CGRect(x: 37, y: 83, width: 320, height: 400))
    }

    func testWideRectangle() throws {
        try checkFit(in: CGRect(x: -20, y: 10, width: 700, height: 300))
    }

    func testStableOutputIndependentOfNodeDeclarationOrder() throws {
        let rect = CGRect(x: 37, y: 83, width: 430, height: 660)
        let original = try level(nodes: grid)
        let first = MultiVanBoardLayout.make(level: original, in: rect)
        for nodes in [grid, Array(grid.reversed()), Array(grid.dropFirst()) + [grid[0]]] {
            let next = MultiVanBoardLayout.make(level: try level(nodes: nodes), in: rect)
            XCTAssertEqual(first.pointsByNodeID, next.pointsByNodeID)
            XCTAssertEqual(first.coordinateScale, next.coordinateScale)
        }
        XCTAssertEqual(first.pointsByNodeID, MultiVanBoardLayout.make(level: original, in: rect).pointsByNodeID)
    }

    func testSparseAndEmptyLevelsKeepFullGridProjection() throws {
        let rect = CGRect(x: 0, y: 0, width: 320, height: 400)
        let full = MultiVanBoardLayout.make(level: try level(nodes: grid), in: rect)
        for nodes in [[], [grid[17]]] {
            let sparse = MultiVanBoardLayout.make(level: try level(nodes: nodes), in: rect)
            XCTAssertEqual(sparse.pointsByNodeID.count, nodes.count)
            XCTAssertEqual(sparse.coordinateScale, full.coordinateScale)
            XCTAssertEqual(sparse.point(for: RoadPoint(x: 2, y: 3)), CGPoint(x: rect.midX, y: rect.midY))
            for node in nodes {
                XCTAssertEqual(sparse.pointsByNodeID[node.id], full.pointsByNodeID[node.id])
            }
        }
    }

    func testSwitchOverlaySharesMV12ProjectionAndKeepsFullHitTargetsInsideBoard() throws {
        let level = try level(nodes: grid)
        let hitSize = MultiVanSwitchButton.hitSize
        XCTAssertGreaterThanOrEqual(hitSize, 44)
        for size in [CGSize(width: 320, height: 400), CGSize(width: 430, height: 660),
                     CGSize(width: 180, height: 240), CGSize(width: 700, height: 300)] {
            let rect = CGRect(origin: .zero, size: size)
            let layout = MultiVanBoardView.boardLayout(level: level, size: size)
            let expected = MultiVanBoardLayout.make(
                level: level, in: rect.insetBy(dx: hitSize / 2, dy: hitSize / 2)
            )
            XCTAssertEqual(layout.pointsByNodeID, expected.pointsByNodeID)
            XCTAssertEqual(layout.coordinateScale, expected.coordinateScale)
            for node in grid {
                let point = try XCTUnwrap(layout.pointsByNodeID[node.id])
                XCTAssertEqual(point, layout.point(for: RoadPoint(x: node.x, y: node.y)))
                let hitRect = CGRect(x: point.x - hitSize / 2, y: point.y - hitSize / 2,
                                     width: hitSize, height: hitSize)
                XCTAssertTrue(rect.contains(hitRect), "Hit target clipped at \(node.id) in \(size)")
            }
        }
    }
}

final class MultiVanPreviewDrawingTests: XCTestCase {
    private let layout = BoardLayout(pointsByNodeID: [:], coordinateScale: 40, maxY: 6)

    private func fixture(_ count: Int = 4) throws -> MultiVanEngine {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["a"]),
            RouteNode(id: "switch", x: 1, y: 0, outgoingEdgeIDs: ["b", "c"]),
            RouteNode(id: "end", x: 2, y: 1, outgoingEdgeIDs: []),
            RouteNode(id: "dead", x: 1, y: 2, outgoingEdgeIDs: [])
        ]
        let edges = [RouteEdge(id: "a", fromNodeID: "start", toNodeID: "switch"),
                     RouteEdge(id: "b", fromNodeID: "switch", toNodeID: "end"),
                     RouteEdge(id: "c", fromNodeID: "switch", toNodeID: "dead")]
        let graph = try JSONSerialization.jsonObject(with: JSONEncoder().encode(RouteGraph(nodes: nodes, edges: edges)))
        let vans = ["red", "blue", "yellow", "green"].prefix(count).enumerated().map { index, color in
            ["id": "van\(index)", "color": color, "startNodeID": "start"]
        }
        let json: [String: Any] = ["id": "lanes", "name": "Lanes", "graph": graph, "vans": vans,
                                   "houses": [["nodeID": "end", "color": "red"]],
                                   "initialSwitchEdges": [:], "parChanges": 0]
        return try MultiVanEngine(level: JSONDecoder().decode(MultiVanLevel.self,
                                 from: JSONSerialization.data(withJSONObject: json)))
    }

    func testOneThroughFourLanesAreCenteredAndStableAcrossTwoSharedRoads() throws {
        for count in 1...4 {
            let engine = try fixture(count)
            let routes = engine.previewRoutes
            let lanes = MultiVanPreviewDrawing.laneOffsets(routes: routes)
            let drawings = MultiVanPreviewDrawing.make(routes: routes, vans: engine.level.vans,
                                                       graph: engine.runtimeGraph, layout: layout)
            XCTAssertEqual(drawings.count, count)
            for index in 0..<count {
                let expected = (CGFloat(index) - CGFloat(count - 1) / 2) * 4
                XCTAssertEqual(lanes[index]["a"], expected)
                XCTAssertEqual(lanes[index]["b"], expected)
                XCTAssertEqual(drawings[index].color, engine.level.vans[index].color)
                XCTAssertEqual(drawings[index].ending, routes[index].ending)
            }
            for _ in 0..<5 {
                XCTAssertEqual(lanes, MultiVanPreviewDrawing.laneOffsets(routes: routes))
            }
        }
    }

    func testUnsharedEdgesStayCenteredAndRepeatedEdgesUseOneLane() {
        let routes = [MultiVanPreviewRoute(edgeIDs: ["a", "b", "a"], ending: .loopLimit),
                      MultiVanPreviewRoute(edgeIDs: ["a", "c"], ending: .deadEnd)]
        let lanes = MultiVanPreviewDrawing.laneOffsets(routes: routes)
        XCTAssertEqual(lanes, [["a": -2, "b": 0], ["a": 2, "c": 0]])
    }

    func testCurveOffsetsUseProjectedNormalsAndIndependentSubpaths() throws {
        let engine = try fixture(2)
        let road = try XCTUnwrap(engine.runtimeGraph.edgesByID["b"]?.roadPath)
        for step in 0...100 {
            let distance = road.totalLength * Double(step) / 100
            let base = try XCTUnwrap(layout.point(for: road.point(atDistance: distance)))
            let offset = try XCTUnwrap(MultiVanPreviewDrawing.offsetPoint(on: road, at: distance,
                                                                         offset: 6, layout: layout))
            let tangent = road.tangent(atDistance: distance)
            let dx = offset.x - base.x, dy = offset.y - base.y
            XCTAssertEqual(hypot(dx, dy), 6, accuracy: 1e-8)
            XCTAssertEqual(dx * tangent.x - dy * tangent.y, 0, accuracy: 1e-8)
        }
        let path = MultiVanPreviewDrawing.offsetPath(for: road, offset: 6, layout: layout)
        var points: [CGPoint] = []
        path.forEach { element in
            if case .line(let point) = element { points.append(point) }
        }
        XCTAssertGreaterThan(points.count, 20)
        for (a, b) in zip(points, points.dropFirst()) {
            XCTAssertLessThan(hypot(b.x - a.x, b.y - a.y), 6)
        }
        let drawings = MultiVanPreviewDrawing.make(routes: engine.previewRoutes, vans: engine.level.vans,
                                                   graph: engine.runtimeGraph, layout: layout)
        var moves = 0
        drawings[0].path.forEach { if case .move = $0 { moves += 1 } }
        XCTAssertEqual(moves, 2)
        XCTAssertEqual(MultiVanPreviewDrawing.offsetPath(for: road, offset: 0, layout: layout),
                       RoadPathRenderer.path(for: road, layout: layout))
    }

    func testEndpointUsesFinalGeometryAndLaneAndSwitchUpdatesDrawing() throws {
        let engine = try fixture()
        func verify() throws -> [MultiVanPreviewDrawing] {
            let drawings = MultiVanPreviewDrawing.make(routes: engine.previewRoutes, vans: engine.level.vans,
                                                       graph: engine.runtimeGraph, layout: layout)
            let lanes = MultiVanPreviewDrawing.laneOffsets(routes: engine.previewRoutes)
            for index in drawings.indices {
                let route = engine.previewRoutes[index]
                let edgeID = try XCTUnwrap(route.edgeIDs.last)
                let road = try XCTUnwrap(engine.runtimeGraph.edgesByID[edgeID]?.roadPath)
                XCTAssertEqual(drawings[index].endpoint,
                               MultiVanPreviewDrawing.offsetPoint(on: road, at: road.totalLength,
                                                                  offset: lanes[index][edgeID]!, layout: layout))
                XCTAssertEqual(drawings[index].ending, route.ending)
            }
            return drawings
        }
        let before = try verify()
        XCTAssertEqual(before.map(\.ending), [.matchingHouse, .wrongHouse, .wrongHouse, .wrongHouse])
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
        let after = try verify()
        XCTAssertEqual(after.map(\.ending), Array(repeating: .deadEnd, count: 4))
        XCTAssertNotEqual(before[0].endpoint, after[0].endpoint)
        XCTAssertNotEqual(before[0].path, after[0].path)
        XCTAssertNil(engine.lastFailPoint)
    }

    func testMarkersStackInTwoColumnsWhenRoutesEndTogether() throws {
        let engine = try fixture()
        let routes = engine.previewRoutes
        let markers = MultiVanPreviewMarker.make(routes: routes, vans: engine.level.vans, graph: engine.runtimeGraph)
        XCTAssertEqual(markers.map { $0?.nodeID }, Array(repeating: "end", count: 4))
        XCTAssertEqual(markers.map { $0?.glyph }, ["✓", "✗", "✗", "✗"])
        XCTAssertEqual(markers.map { $0?.stackSlot }, [0, 1, 2, 3])
        XCTAssertEqual(markers.map { $0?.column }, [-1, 1, -1, 1])
        XCTAssertEqual(markers.map { $0?.row }, [0, 0, 1, 1])
        let drawings = MultiVanPreviewDrawing.make(routes: routes, vans: engine.level.vans,
                                                   graph: engine.runtimeGraph, layout: layout)
        XCTAssertEqual(drawings.map(\.marker), markers)

        // A lone end sits unpaired; a van with no line left gets no marker and leaves the stack.
        let alone = try fixture(1)
        let single = try XCTUnwrap(MultiVanPreviewMarker.make(
            routes: alone.previewRoutes, vans: alone.level.vans, graph: alone.runtimeGraph)[0])
        XCTAssertNil(single.stackSlot)
        XCTAssertNil(single.column)
        XCTAssertEqual(single.row, 0)
        let pair = try fixture(2)
        let mixed = MultiVanPreviewMarker.make(
            routes: [MultiVanPreviewRoute(edgeIDs: ["a", "b"], ending: .offRoad), pair.previewRoutes[1]],
            vans: pair.level.vans, graph: pair.runtimeGraph)
        XCTAssertNil(mixed[0])
        XCTAssertEqual(mixed[1]?.nodeID, "end")
        XCTAssertNil(mixed[1]?.stackSlot)
    }

    func testZeroLengthRoadAndTerminalStartAndLoopEndpoint() throws {
        let road = RoadPath.make(from: RoadPoint(x: 1, y: 1), to: RoadPoint(x: 1, y: 1))
        let point = try XCTUnwrap(MultiVanPreviewDrawing.offsetPoint(on: road, at: 0, offset: 6, layout: layout))
        XCTAssertEqual(point, layout.point(for: RoadPoint(x: 1, y: 1)))
        XCTAssertFalse(MultiVanPreviewDrawing.offsetPath(for: road, offset: 6, layout: layout).isEmpty)
        let engine = try fixture(1)
        let start = CGPoint(x: 17, y: 23)
        let startLayout = BoardLayout(pointsByNodeID: ["start": start], coordinateScale: 40)
        let routes = [MultiVanPreviewRoute(edgeIDs: [], ending: .matchingHouse)]
        let drawing = MultiVanPreviewDrawing.make(routes: routes, vans: engine.level.vans,
                                                  graph: engine.runtimeGraph, layout: startLayout)[0]
        XCTAssertEqual(drawing.endpoint, start)
        XCTAssertTrue(drawing.path.isEmpty)
        let loop = MultiVanPreviewDrawing.make(
            routes: [MultiVanPreviewRoute(edgeIDs: ["a", "b", "a"], ending: .loopLimit)],
            vans: engine.level.vans, graph: engine.runtimeGraph, layout: layout)[0]
        XCTAssertEqual(loop.ending, .loopLimit)
        XCTAssertEqual(loop.endpoint, layout.point(for: RoadPoint(x: 1, y: 0)))
    }
}
