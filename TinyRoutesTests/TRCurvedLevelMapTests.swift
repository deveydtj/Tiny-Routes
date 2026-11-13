import SceneKit
import XCTest
import simd
@testable import TinyRoutes

final class TRCurvedWorldTests: XCTestCase {
    private let world = TRCurvedWorld(curvature: 0.03, originZ: 3)

    func testTheWorldDropsWithTheSquareOfTheDistanceAhead() {
        XCTAssertEqual(world.drop(atZ: 3), 0)
        XCTAssertEqual(world.drop(atZ: 1), 0.12, accuracy: 1e-12)
        XCTAssertEqual(world.drop(atZ: -1), 0.48, accuracy: 1e-12)
        let bent = world.bent(SIMD3(1.5, 0.4, -1))
        XCTAssertEqual(bent.x, 1.5)
        XCTAssertEqual(bent.y, 0.4 - 0.48, accuracy: 1e-12)
        XCTAssertEqual(bent.z, -1)
    }

    func testBentNormalsStayAtRightAnglesToTheBentGround() {
        for z in [2.0, -1, -6] {
            let normal = world.bentNormal(SIMD3(0, 1, 0), atZ: z)
            // The bent ground's slope along z, by finite difference.
            let step = 1e-4
            let tangent = world.bent(SIMD3(0, 0, z + step)) - world.bent(SIMD3(0, 0, z - step))
            XCTAssertEqual(simd_dot(normal, simd_normalize(tangent)), 0, accuracy: 1e-6)
            // Ahead of the lens the ground rolls away, so it faces forwards.
            XCTAssertLessThan(normal.z, 0)
        }
    }

    func testOnlyWhatStandsTallEnoughShowsOverTheCurve() {
        let eye = 6.0
        let horizon = world.originZ - (eye / world.curvature).squareRoot()
        XCTAssertTrue(world.isVisible(height: 0, atZ: horizon + 0.5, eyeHeight: eye))
        XCTAssertFalse(world.isVisible(height: 0, atZ: horizon - 0.5, eyeHeight: eye))
        // The ground falls away ever faster past the horizon; a short thing sinks, a tall one peeks over.
        XCTAssertFalse(world.isVisible(height: 0.3, atZ: horizon - 4, eyeHeight: eye))
        XCTAssertTrue(world.isVisible(height: 3, atZ: horizon - 4, eyeHeight: eye))
    }

    @MainActor
    func testInstallBendsCopiesAndLeavesSharedOriginalsFlat() {
        let material = SCNMaterial()
        material.shaderModifiers = [.fragment: "_output.color *= 1.0;"]
        let geometry = SCNBox(width: 1, height: 1, length: 1, chamferRadius: 0)
        geometry.materials = [material]
        let root = SCNNode()
        let first = SCNNode(geometry: geometry), second = SCNNode(geometry: geometry)
        root.addChildNode(first)
        root.addChildNode(second)

        world.install(on: root)

        XCTAssertNil(material.shaderModifiers?[.geometry])
        XCTAssertTrue(geometry.firstMaterial === material)
        XCTAssertFalse(first.geometry === geometry)
        // What was shared stays shared, so it compiles once.
        XCTAssertTrue(first.geometry === second.geometry)
        let bent = first.geometry?.firstMaterial
        XCTAssertEqual(bent?.shaderModifiers?[.geometry], TRCurvedWorld.shaderModifier)
        XCTAssertNotNil(bent?.shaderModifiers?[.fragment])
        XCTAssertEqual(bent?.value(forKey: "curvedWorldCurvature") as? Float, 0.03)
        XCTAssertEqual(bent?.value(forKey: "curvedWorldOriginZ") as? Float, 3)
    }
}

@MainActor
final class TRCurvedLevelMapLensTests: XCTestCase {
    private let lens = TRCurvedLevelMapLens(levelCount: 12)
    private let sizes = [CGSize(width: 393, height: 520), CGSize(width: 375, height: 420), CGSize(width: 440, height: 640)]

    func testTheHorizonSitsAtItsShareOfEveryView() {
        for size in sizes {
            XCTAssertEqual(TRCurvedLevelMapLens.horizonY(in: size) / size.height, TRCurvedLevelMapLens.horizonShare, accuracy: 0.002, "\(size)")
        }
    }

    func testViewPointsMatchTheSceneKitLens() {
        let map = TRCurvedLevelMapScene()
        let camera = map.cameraNode
        for size in sizes {
            map.aim(in: size)
            let projection = simd_float4x4(camera.camera!.projectionTransform(withViewportSize: size))
            let view = camera.simdWorldTransform.inverse
            for point in [SIMD3<Double>(0, 0, 0), SIMD3(1.2, 0.3, -2.5), SIMD3(-0.8, 0, 1.5)] {
                let clip = projection * view * SIMD4<Float>(SIMD3<Float>(TRCurvedLevelMapLens.curve.bent(point)), 1)
                let ndc = SIMD2(clip.x, clip.y) / clip.w
                let expected = CGPoint(x: CGFloat(ndc.x + 1) / 2 * size.width, y: CGFloat(1 - ndc.y) / 2 * size.height)
                let actual = TRCurvedLevelMapLens.viewPoint(point, in: size)
                XCTAssertEqual(actual?.x ?? .nan, expected.x, accuracy: 0.5, "\(point) in \(size)")
                XCTAssertEqual(actual?.y ?? .nan, expected.y, accuracy: 0.5, "\(point) in \(size)")
            }
        }
    }

    func testEachLevelShowsWhenTheMapRestsOnItAndOnlyTheNextFewAhead() {
        for size in sizes {
            for index in 0..<lens.layout.levelCount {
                let focus = lens.focus(forLevel: index)
                let frame = lens.signFrame(index, focus: focus, in: size)
                XCTAssertNotNil(frame, "level \(index + 1) in \(size)")
                if let frame {
                    XCTAssertTrue(CGRect(origin: .zero, size: size).contains(frame), "level \(index + 1) in \(size)")
                    XCTAssertGreaterThan(frame.minY, TRCurvedLevelMapLens.horizonY(in: size))
                    XCTAssertGreaterThan(frame.width, 44)
                }
                // Signs past the fade have no frame to tap.
                for ahead in stride(from: index + 5, to: lens.layout.levelCount, by: 1) {
                    XCTAssertNil(lens.signFrame(ahead, focus: focus, in: size), "level \(ahead + 1) from \(index + 1)")
                }
            }
        }
    }

    func testTheRoadsSwingStaysInViewAtThePivot() {
        for size in sizes {
            for side in [-1.0, 1] {
                let x = side * (TRCurvedLevelMapLens.swing + TRCurvedLevelMapLens.Sign.width * TRCurvedLevelMapLens.Sign.tileShare / 2)
                let point = TRCurvedLevelMapLens.viewPoint(SIMD3(x, 0, 0), in: size)!
                XCTAssertGreaterThan(point.x, 0, "\(size)")
                XCTAssertLessThan(point.x, size.width, "\(size)")
            }
        }
    }

    func testTheFocusRunsFromTheFirstLevelToTheLast() {
        XCTAssertEqual(lens.focusRange.lowerBound, lens.layout.station(0).y)
        XCTAssertEqual(lens.focusRange.upperBound, lens.layout.station(11).y)
        XCTAssertGreaterThan(TRCurvedLevelMapLens.pointsPerUnit(in: sizes[0]), 10)
    }

    func testTheCurvedMapsSceneryKeepsOffItsGentlerRoad() {
        let scenery = TRLevelMapScenery(layout: lens.layout)
        XCTAssertFalse(scenery.houses.isEmpty)
        for item in scenery.items {
            XCTAssertGreaterThan(lens.layout.distanceToRoad(item.point), TRLevelMapLawn.Measure.curbWidth / 2, "\(item)")
        }
    }

    // MARK: - Scene

    func testTheSceneBendsItsWorldButNotTheGameplayTablesPieces() throws {
        let map = TRCurvedLevelMapScene()
        map.load(lens)
        var bent = 0
        map.scene.rootNode.enumerateHierarchy { node, _ in
            guard node.light == nil, node.camera == nil, let geometry = node.geometry else { return }
            for material in geometry.materials {
                XCTAssertEqual(material.shaderModifiers?[.geometry], TRCurvedWorld.shaderModifier)
                bent += 1
            }
        }
        XCTAssertGreaterThan(bent, 50)
        // The pieces the gameplay table shares stay flat.
        let tree = try XCTUnwrap(MultiVanDioramaPieces.scenery(.tree(.pine), height: 1))
        tree.enumerateHierarchy { node, _ in
            for material in node.geometry?.materials ?? [] {
                XCTAssertNil(material.shaderModifiers?[.geometry])
            }
        }
    }

    func testTheMapFollowsTheVanToALevel() {
        let map = TRCurvedLevelMapScene()
        map.load(lens)
        map.parkVan(atY: lens.layout.parking(0))
        XCTAssertEqual(map.focus, lens.focusRange.lowerBound, accuracy: 1e-5)
        let target = lens.focus(forLevel: 2)
        let duration = map.driveVan(toY: lens.layout.parking(2), focus: target)
        XCTAssertGreaterThan(duration, 0.5)
        XCTAssertEqual(map.vanY ?? .nan, lens.layout.parking(2), accuracy: 1e-9)
        map.setFocus(target)
        XCTAssertEqual(map.focus, target, accuracy: 1e-5)
    }
}
