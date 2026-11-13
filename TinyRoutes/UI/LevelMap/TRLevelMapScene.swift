import SceneKit
import UIKit

/// The 3D level map: the gameplay table's floating lawn, stretched into a long
/// island with a road winding up it, scenery either side and a red van that drives
/// from level to level. It is seen through a fixed orthographic lens, so a SwiftUI
/// overlay can place the level tiles with `TRLevelMapLayout` alone. Nothing moves
/// but the van, so SceneKit only draws while it drives.
///
/// The van has a scene of its own, drawn in a layer over the tiles: the road runs
/// close behind each tile, and the van would otherwise vanish under one.
@MainActor
final class TRLevelMapScene {
    let scene = SCNScene()
    let cameraNode = SCNNode()
    let vanScene = SCNScene()
    let vanCameraNode = SCNNode()
    private(set) var layout: TRLevelMapLayout?
    private let piecesNode = SCNNode()
    private(set) var van: SCNNode?
    /// The y the van has been sent to, or is parked at.
    private(set) var vanY: Double?

    private static let driveKey = "drive"

    init() {
        // The page shows through around the island.
        scene.background.contents = nil
        scene.lightingEnvironment.contents = Self.skyGround()
        scene.lightingEnvironment.intensity = 0.55
        scene.rootNode.addChildNode(piecesNode)
        for (scene, cameraNode) in [(scene, cameraNode), (vanScene, vanCameraNode)] {
            let lens = SCNCamera()
            lens.usesOrthographicProjection = true
            lens.projectionDirection = .vertical
            lens.zNear = 1
            lens.zFar = 200
            cameraNode.camera = lens
            scene.rootNode.addChildNode(cameraNode)
        }
        vanScene.background.contents = nil
        vanScene.lightingEnvironment.contents = scene.lightingEnvironment.contents
        vanScene.lightingEnvironment.intensity = scene.lightingEnvironment.intensity
    }

    /// Builds the island for `layout`; the same layout keeps what's there.
    func load(_ layout: TRLevelMapLayout) {
        guard layout != self.layout else { return }
        self.layout = layout
        piecesNode.childNodes.forEach { $0.removeFromParentNode() }

        let scenery = TRLevelMapScenery(layout: layout)
        let lawn = MultiVanDioramaScene.paper(texture: TRLevelMapLawn.image(layout: layout, scenery: scenery))
        lawn.diffuse.mipFilter = .linear
        lawn.diffuse.maxAnisotropy = 8
        piecesNode.addChildNode(MultiVanDioramaScene.slab(lawn: lawn, width: TRLevelMapLayout.width, depth: layout.depth))
        piecesNode.addChildNode(sun(for: layout))
        place(scenery, layout: layout)

        self.van?.removeFromParentNode()
        vanScene.rootNode.childNodes.filter { $0.light != nil }.forEach { $0.removeFromParentNode() }
        let van = MultiVanDioramaPieces.van(.red)
        // Larger than on the gameplay table, to read beside the tiles.
        van.simdScale *= 1.35
        vanScene.rootNode.addChildNode(van)
        // The same sun, without shadows: there is no lawn here to fall on.
        let vanSun = sun(for: layout)
        vanSun.light?.castsShadow = false
        vanScene.rootNode.addChildNode(vanSun)
        self.van = van
        vanY = nil

        let lens = layout.lens
        for cameraNode in [cameraNode, vanCameraNode] {
            cameraNode.camera?.orthographicScale = lens.orthographicScale
            cameraNode.simdPosition = SIMD3<Float>(lens.target - TRLevelMapLayout.forward * 40)
            cameraNode.simdLook(at: SIMD3<Float>(lens.target), up: SIMD3(0, 1, 0), localFront: SCNNode.simdLocalFront)
        }
    }

    /// Puts the van at `y` along the road at once, facing up the island.
    func parkVan(atY y: Double) {
        guard let layout, let van else { return }
        van.removeAction(forKey: Self.driveKey)
        van.simdPosition = SIMD3<Float>(layout.world(layout.roadPoint(atY: y)))
        van.simdEulerAngles.y = Float(MultiVanDioramaGeometry.yaw(facing: layout.roadHeading(atY: y)))
        vanY = y
    }

    /// How long the van takes to drive from where it is to `y`.
    func driveDuration(toY y: Double) -> Double {
        guard let layout, let vanY else { return 0 }
        return Self.duration(forLength: Self.length(of: layout.roadSamples(fromY: vanY, toY: y)))
    }

    static func duration(forLength length: Double) -> Double {
        // Unhurried for a hop to the next level, and never long for a jump of many.
        min(max(length / 3.4, 0.55), 1.6)
    }

    /// Drives the van along the road to `y`, easing away and into its stop, and
    /// returns how long that takes.
    @discardableResult
    func driveVan(toY y: Double) -> Double {
        guard let layout, let van, let vanY else { parkVan(atY: y); return 0 }
        let points = layout.roadSamples(fromY: vanY, toY: y, spacing: 0.08)
        let length = Self.length(of: points)
        guard points.count > 1, length > 0.01 else { parkVan(atY: y); return 0 }
        let total = Self.duration(forLength: length)
        var actions: [SCNAction] = []
        var travelled = 0.0, elapsed = 0.0
        for (from, to) in zip(points, points.dropFirst()) {
            let segment = hypot(to.x - from.x, to.y - from.y)
            travelled += segment
            // Smoothstep easing: the time to reach this far along the road.
            let time = total * Self.easedTime(progress: travelled / length)
            let duration = max(time - elapsed, 0.001)
            elapsed = time
            let heading = RoadVector(x: to.x - from.x, y: to.y - from.y)
            let yaw = MultiVanDioramaGeometry.yaw(facing: heading)
            actions.append(.group([
                .move(to: SCNVector3(layout.world(to)), duration: duration),
                .rotateTo(x: 0, y: CGFloat(yaw), z: 0, duration: min(duration * 2, 0.12), usesShortestUnitArc: true),
            ]))
        }
        van.removeAction(forKey: Self.driveKey)
        van.runAction(.sequence(actions), forKey: Self.driveKey)
        self.vanY = y
        return total
    }

    /// The inverse of smoothstep: how far through the drive's time the van is
    /// `progress` of the way along the road.
    static func easedTime(progress: Double) -> Double {
        let p = min(max(progress, 0), 1)
        // smoothstep(t) = p, solved for t.
        return 0.5 - sin(asin(1 - 2 * p) / 3)
    }

    static func length(of points: [RoadPoint]) -> Double {
        zip(points, points.dropFirst()).reduce(0) { $0 + hypot($1.1.x - $1.0.x, $1.1.y - $1.0.y) }
    }

    // MARK: - Building

    /// Cutouts and houses stand where the scenery put them, the cutouts turned to
    /// the lens and each a little off square, houses facing the road.
    private func place(_ scenery: TRLevelMapScenery, layout: TRLevelMapLayout) {
        for item in scenery.items {
            guard let node = MultiVanDioramaPieces.scenery(item.kind, height: item.height) else { continue }
            node.simdPosition = SIMD3<Float>(layout.world(item.point))
            node.simdEulerAngles.y = Float(sin(item.point.x * 12.9 + item.point.y * 78.2) * 0.3)
            piecesNode.addChildNode(node)
        }
        for house in scenery.houses {
            let node = MultiVanDioramaPieces.house(house.color)
            node.simdPosition = SIMD3<Float>(layout.world(house.point))
            node.simdEulerAngles.y = Float(MultiVanDioramaGeometry.yaw(facing: house.facing))
            piecesNode.addChildNode(node)
        }
        for pond in scenery.ponds {
            let node = MultiVanDioramaPieces.pond(pond)
            let centre = layout.world(pond.centre)
            node.simdPosition.x = Float(centre.x)
            node.simdPosition.z = Float(centre.z)
            piecesNode.addChildNode(node)
        }
    }

    /// The gameplay table's warm sun, its shadow box stretched over the island.
    private func sun(for layout: TRLevelMapLayout) -> SCNNode {
        let light = SCNLight()
        light.type = .directional
        light.color = UIColor(dioramaHex: 0xFFF0D6)
        light.intensity = 1250
        light.castsShadow = true
        light.shadowMapSize = CGSize(width: 2048, height: 2048)
        light.shadowMode = .forward
        light.shadowSampleCount = 8
        light.shadowRadius = 2
        light.shadowColor = UIColor(white: 0, alpha: 0.36)
        light.orthographicScale = CGFloat(layout.depth / 2 + 1.5)
        light.zNear = 1
        light.zFar = 40
        let node = SCNNode()
        node.light = light
        node.simdPosition = SIMD3(-5.2, 8.2, 3.6)
        node.simdLook(at: .zero, up: SIMD3(0, 1, 0), localFront: SCNNode.simdLocalFront)
        return node
    }

    /// Sky above and lawn below, as the gameplay table is lit.
    private static func skyGround() -> UIImage {
        let size = CGSize(width: 64, height: 32)
        return UIGraphicsImageRenderer(size: size).image { context in
            let colors = [UIColor(dioramaHex: 0xE6F4FF), UIColor(dioramaHex: 0xC4D6C0), UIColor(dioramaHex: 0xA3B98A)]
                .map(\.cgColor) as CFArray
            let gradient = CGGradient(colorsSpace: nil, colors: colors, locations: [0.35, 0.5, 0.65])!
            context.cgContext.drawLinearGradient(
                gradient, start: .zero, end: CGPoint(x: 0, y: size.height), options: [.drawsBeforeStartLocation, .drawsAfterEndLocation]
            )
        }
    }
}
