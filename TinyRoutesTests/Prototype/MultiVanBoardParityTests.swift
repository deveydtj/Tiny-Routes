import SwiftUI
import XCTest
@testable import TinyRoutes

/// Both boards offer the same switches, reached the same way. The flat board puts
/// each button at its layout point and the diorama at its projected dial; the
/// buttons themselves are shared.
@MainActor
final class MultiVanBoardParityTests: XCTestCase {
    /// A small phone, a large phone and a landscape iPad's board.
    private static let sizes = [CGSize(width: 343, height: 330), CGSize(width: 361, height: 520), CGSize(width: 700, height: 360)]

    private enum Board: CaseIterable {
        case flat, diorama
    }

    func testBothBoardsListTheSameSwitchesWithTheSameWords() throws {
        for level in try levels() {
            let engine = try MultiVanEngine(level: level)
            for phase in ["plan", "run"] {
                if phase == "run" {
                    engine.go()
                    engine.advance(by: 0.5)
                }
                let expected = MultiVanSwitchControl.controls(engine: engine, graph: engine.runtimeGraph)
                for size in Self.sizes {
                    for board in Board.allCases {
                        let placements = placements(board, engine: engine, size: size)
                        let label = "\(level.id) \(phase) \(board) \(size)"
                        XCTAssertEqual(placements.map(\.id), expected.map(\.nodeID), label)
                        XCTAssertEqual(placements.map(\.control.accessibilityLabel), expected.map(\.accessibilityLabel), label)
                        XCTAssertEqual(placements.map(\.control.accessibilityValue), expected.map(\.accessibilityValue), label)
                        XCTAssertEqual(placements.map(\.control.appearance.accessibilityHint), expected.map(\.appearance.accessibilityHint), label)
                    }
                }
            }
        }
    }

    /// At rest every switch's whole square is on the board, and any tap within
    /// 22 points of a switch reaches it, on both boards and every board size.
    func testEveryTapWithinHalfATargetReachesItsSwitch() throws {
        for level in try levels() {
            let engine = try MultiVanEngine(level: level)
            for size in Self.sizes {
                for board in Board.allCases {
                    let placements = placements(board, engine: engine, size: size)
                    let half = MultiVanSwitchButton.hitSize / 2
                    for placement in placements {
                        let label = "\(level.id) \(board) \(size) \(placement.id)"
                        let square = CGRect(x: placement.point.x - half, y: placement.point.y - half, width: half * 2, height: half * 2)
                        XCTAssertTrue(CGRect(origin: .zero, size: size).contains(square), label)
                        for tap in Self.taps(around: placement.point, radius: half - 0.5) {
                            XCTAssertEqual(MultiVanSwitchPlacement.target(at: tap, in: placements), placement.id, "\(label) tap \(tap)")
                        }
                    }
                }
            }
        }
    }

    /// Wherever the table is turned, a tap reaches the nearest switch whose square
    /// holds it, and nothing off the board.
    func testTapsReachTheNearestSwitchAtEveryOrbit() throws {
        let size = Self.sizes[0]
        let bounds = CGRect(origin: .zero, size: size)
        let rest = MultiVanDioramaOrbit.resting
        let orbits = [rest, rest.dragged(by: CGSize(width: 300, height: -300)), rest.dragged(by: CGSize(width: -300, height: 300)),
                      rest.dragged(by: CGSize(width: -300, height: -300)), rest.dragged(by: CGSize(width: 300, height: 300))]
        for level in try levels() {
            let engine = try MultiVanEngine(level: level)
            let controls = MultiVanSwitchControl.controls(engine: engine, graph: engine.runtimeGraph)
            for orbit in orbits {
                let camera = MultiVanDioramaCamera.framed(in: size).orbited(orbit)
                let placements = MultiVanDioramaBoardView.switchPlacements(
                    controls: controls, graph: engine.runtimeGraph, camera: camera, size: size
                )
                XCTAssertEqual(placements.count, controls.count, "\(level.id) \(orbit)")
                let half = MultiVanSwitchButton.hitSize / 2
                for placement in placements {
                    for dx in stride(from: -half + 1, to: half, by: 4) {
                        for dy in stride(from: -half + 1, to: half, by: 4) {
                            let tap = CGPoint(x: placement.point.x + dx, y: placement.point.y + dy)
                            let target = MultiVanSwitchPlacement.target(at: tap, in: placements)
                            guard bounds.contains(tap) else {
                                XCTAssertNil(target, "\(level.id) \(orbit) \(tap)")
                                continue
                            }
                            let nearest = placements
                                .filter { max(abs($0.point.x - tap.x), abs($0.point.y - tap.y)) < half }
                                .min { distance($0.point, tap) < distance($1.point, tap) }
                            XCTAssertEqual(target, nearest?.id, "\(level.id) \(orbit) \(placement.id) tap \(tap)")
                        }
                    }
                }
            }
        }
    }

    /// The same taps on both boards, in planning and mid-run, get the same answers
    /// from the engine and leave the same routes set.
    func testTapsOnBothBoardsHaveTheSameResults() throws {
        let size = Self.sizes[1]
        for level in try levels() {
            let engines = try Board.allCases.map { _ in try MultiVanEngine(level: level) }
            func tapEverySwitch(_ phase: String) {
                let ids = MultiVanSwitchControl.controls(engine: engines[0], graph: engines[0].runtimeGraph).map(\.nodeID)
                for id in ids {
                    var results: [MultiVanTapResult] = []
                    for (board, engine) in zip(Board.allCases, engines) {
                        let placements = placements(board, engine: engine, size: size)
                        let target = placements.first { $0.id == id }.flatMap { MultiVanSwitchPlacement.target(at: $0.point, in: placements) }
                        XCTAssertEqual(target, id, "\(level.id) \(phase) \(board)")
                        results.append(engine.tapSwitch(nodeID: target ?? ""))
                    }
                    XCTAssertEqual(results[0], results[1], "\(level.id) \(phase) \(id)")
                    XCTAssertEqual(routes(engines[0]), routes(engines[1]), "\(level.id) \(phase) \(id)")
                }
            }
            tapEverySwitch("plan")
            for engine in engines {
                engine.go()
                engine.advance(by: 0.6)
            }
            tapEverySwitch("run")
        }
    }

    /// VoiceOver finds every switch on both boards by its label and activates it,
    /// and hears the same houses, vans and roadblocks around them.
    func testVoiceOverReadsAndActivatesEverySwitchOnBothBoards() throws {
        try Self.enableAccessibility()
        let scene = try XCTUnwrap(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let window = UIWindow(windowScene: scene)
        window.frame = CGRect(origin: .zero, size: CGSize(width: 393, height: 852))
        defer {
            window.isHidden = true
            window.rootViewController = nil
        }
        for level in try levels() {
            var pieces: [Board: [String]] = [:]
            for board in Board.allCases {
                let engine = try MultiVanEngine(level: level)
                let host = UIHostingController(rootView: Self.view(board, engine: engine).frame(width: 361, height: 520))
                window.rootViewController = host
                window.makeKeyAndVisible()
                settle()
                let controls = MultiVanSwitchControl.controls(engine: engine, graph: engine.runtimeGraph)
                let label = "\(level.id) \(board)"
                let switches = Self.accessibilityElements(in: host.view).filter { ($0.accessibilityLabel ?? "").hasPrefix("Switch at") }
                XCTAssertEqual(Set(switches.compactMap(\.accessibilityLabel)), Set(controls.map(\.accessibilityLabel)), label)
                XCTAssertEqual(switches.count, controls.count, label)
                pieces[board] = Self.accessibilityElements(in: host.view)
                    .filter { !($0.accessibilityLabel ?? "").hasPrefix("Switch at") }
                    .map { "\($0.accessibilityLabel ?? "-"): \($0.accessibilityValue ?? "")" }
                    .sorted()
                for control in controls {
                    // Elements are rebuilt as the board redraws, so look each one up afresh.
                    let element = Self.accessibilityElements(in: host.view).first { $0.accessibilityLabel == control.accessibilityLabel }
                    let before = engine.runtimeGraph.nodesByID[control.nodeID]?.activeOutgoingEdgeID
                    XCTAssertEqual(element?.accessibilityValue, control.accessibilityValue, label)
                    XCTAssertTrue(element?.accessibilityTraits.contains(.button) ?? false, "\(label) \(control.nodeID)")
                    // VoiceOver outlines the switch's own target, not the board.
                    XCTAssertEqual(element?.accessibilityFrame.width ?? 0, MultiVanSwitchButton.hitSize, accuracy: 0.5, "\(label) \(control.nodeID)")
                    XCTAssertEqual(element?.accessibilityFrame.height ?? 0, MultiVanSwitchButton.hitSize, accuracy: 0.5, "\(label) \(control.nodeID)")
                    XCTAssertTrue(element?.accessibilityActivate() ?? false, "\(label) \(control.nodeID)")
                    settle()
                    XCTAssertNotEqual(engine.runtimeGraph.nodesByID[control.nodeID]?.activeOutgoingEdgeID, before, "\(label) \(control.nodeID)")
                }
            }
            XCTAssertFalse(pieces[.flat, default: []].isEmpty, level.id)
            XCTAssertEqual(pieces[.flat], pieces[.diorama], level.id)
        }
    }

    // MARK: - Helpers

    /// SwiftUI only builds its accessibility tree for a running assistive client.
    /// Test-only: switch app accessibility on as VoiceOver would.
    private static func enableAccessibility() throws {
        let library = try XCTUnwrap(dlopen("/usr/lib/libAccessibility.dylib", RTLD_NOW))
        let symbol = try XCTUnwrap(dlsym(library, "_AXSApplicationAccessibilitySetEnabled"))
        typealias SetEnabled = @convention(c) (Bool) -> Void
        unsafeBitCast(symbol, to: SetEnabled.self)(true)
    }

    private func levels() throws -> [MultiVanLevel] {
        let levels = try MultiVanLevelRepository().loadAllLevels()
        XCTAssertEqual(levels.count, 19)
        return levels
    }

    private func placements(_ board: Board, engine: MultiVanEngine, size: CGSize) -> [MultiVanSwitchPlacement] {
        let controls = MultiVanSwitchControl.controls(engine: engine, graph: engine.runtimeGraph)
        switch board {
        case .flat:
            return MultiVanBoardView.switchPlacements(
                controls: controls, layout: MultiVanBoardView.boardLayout(level: engine.level, size: size), size: size
            )
        case .diorama:
            return MultiVanDioramaBoardView.switchPlacements(
                controls: controls, graph: engine.runtimeGraph, camera: .framed(in: size), size: size
            )
        }
    }

    @ViewBuilder
    private static func view(_ board: Board, engine: MultiVanEngine) -> some View {
        switch board {
        case .flat: MultiVanBoardView(engine: engine)
        case .diorama: MultiVanDioramaBoardView(engine: engine)
        }
    }

    private func routes(_ engine: MultiVanEngine) -> [String: String?] {
        Dictionary(uniqueKeysWithValues: MultiVanBoardRules.switchNodes(in: engine.runtimeGraph).map { ($0.id, $0.activeOutgoingEdgeID) })
    }

    /// The centre and points around a circle of `radius`.
    private static func taps(around point: CGPoint, radius: CGFloat) -> [CGPoint] {
        [point] + (0..<24).flatMap { step -> [CGPoint] in
            let angle = Double(step) * .pi / 12
            return [radius, radius / 2].map { r in CGPoint(x: point.x + r * cos(angle), y: point.y + r * sin(angle)) }
        }
    }

    private func distance(_ a: CGPoint, _ b: CGPoint) -> CGFloat {
        hypot(a.x - b.x, a.y - b.y)
    }

    private func settle() {
        RunLoop.main.run(until: Date().addingTimeInterval(0.2))
    }

    /// Every element an assistive technology would reach, walking views and
    /// SwiftUI's accessibility containers.
    private static func accessibilityElements(in root: NSObject) -> [NSObject] {
        var found: [NSObject] = []
        func visit(_ object: NSObject) {
            if object.isAccessibilityElement {
                found.append(object)
                return
            }
            if let elements = object.accessibilityElements as? [NSObject] {
                elements.forEach(visit)
            } else {
                let count = object.accessibilityElementCount()
                if count != NSNotFound {
                    (0..<count).compactMap { object.accessibilityElement(at: $0) as? NSObject }.forEach(visit)
                }
            }
            (object as? UIView)?.subviews.forEach(visit)
        }
        visit(root)
        return found
    }
}
