import SceneKit
import SwiftUI

/// The curved 3D level map: the flat level map's island, scenery and van, with each
/// level's tile on a signpost at its stop, seen through a fixed perspective lens and
/// drawn bent over a near horizon by `TRCurvedWorld`. Everything but the lens and
/// the sun rides a treadmill; scrolling slides it under the lens. Nothing moves
/// unless the map scrolls or the van drives, so SceneKit only draws while one does.
@MainActor
final class TRCurvedLevelMapScene {
    /// How a level's sign looks; a sign only redraws when this changes.
    struct SignArt: Equatable {
        let levelNumber: Int
        let state: TRLevelTileState
        let stars: Int
    }

    let scene = SCNScene()
    let cameraNode = SCNNode()
    private let treadmill = SCNNode()
    private(set) var lens: TRCurvedLevelMapLens?
    private(set) var van: SCNNode?
    /// The map y the van has been sent to, or is parked at.
    private(set) var vanY: Double?
    /// Each sign's card, whose material shows the level's tile.
    private var signCards: [SCNNode] = []
    private var signArt: [SignArt?] = []

    private static let driveKey = "drive"
    private static let glideKey = "glide"

    init() {
        // The page's sky shows through above the horizon.
        scene.background.contents = nil
        scene.lightingEnvironment.contents = Self.skyGround()
        scene.lightingEnvironment.intensity = 0.55
        scene.rootNode.addChildNode(treadmill)

        let camera = SCNCamera()
        camera.projectionDirection = .horizontal
        camera.fieldOfView = TRCurvedLevelMapLens.horizontalFieldOfView
        camera.zNear = TRCurvedLevelMapLens.zNear
        camera.zFar = TRCurvedLevelMapLens.zFar
        cameraNode.camera = camera
        cameraNode.simdPosition = SIMD3<Float>(TRCurvedLevelMapLens.eye)
        scene.rootNode.addChildNode(cameraNode)
        scene.rootNode.addChildNode(Self.sun())
    }

    /// Builds the map for `lens`; the same lens keeps what's there.
    func load(_ lens: TRCurvedLevelMapLens) {
        guard lens != self.lens else { return }
        self.lens = lens
        treadmill.childNodes.forEach { $0.removeFromParentNode() }
        let layout = lens.layout

        let scenery = TRLevelMapScenery(layout: layout)
        // Sharper than the flat map's: the lens comes close to the lawn's near end.
        let unit = min(260, 4096 / CGFloat(max(layout.depth, TRLevelMapLayout.width)))
        let lawn = MultiVanDioramaScene.paper(texture: TRLevelMapLawn.image(layout: layout, scenery: scenery, pixelsPerUnit: unit))
        lawn.diffuse.mipFilter = .linear
        lawn.diffuse.maxAnisotropy = 8
        treadmill.addChildNode(Self.ground(lawn: lawn, depth: layout.depth))
        treadmill.addChildNode(Self.apron(depth: layout.depth))
        place(scenery)
        placeApronScenery(depth: layout.depth)

        signCards = (0..<layout.levelCount).map { index in
            let (node, card) = Self.sign()
            node.simdPosition = SIMD3<Float>(TRCurvedLevelMapLens.local(layout.station(index)))
            treadmill.addChildNode(node)
            return card
        }
        signArt = Array(repeating: nil, count: layout.levelCount)

        let van = MultiVanDioramaPieces.van(.red)
        // Larger than on the gameplay table, to read beside the signs.
        van.simdScale *= 1.35
        treadmill.addChildNode(van)
        self.van = van
        vanY = nil

        TRCurvedLevelMapLens.curve.install(on: treadmill)
        setFocus(lens.focusRange.lowerBound)
    }

    /// Redraws the signs whose level has changed since they were last drawn.
    func setSigns(_ art: [SignArt]) {
        for (index, art) in art.enumerated() where signCards.indices.contains(index) && signArt[index] != art {
            signCards[index].geometry?.firstMaterial?.diffuse.contents = Self.signImage(art)
            signArt[index] = art
        }
    }

    /// Tips the lens for a view of `size`, as `TRCurvedLevelMapLens` places things.
    func aim(in size: CGSize) {
        let pitch = TRCurvedLevelMapLens.pose(in: size).pitch
        cameraNode.simdOrientation = simd_quatf(angle: Float(-pitch), axis: SIMD3(1, 0, 0))
    }

    // MARK: - Scrolling

    /// The map y under the pivot, wherever a glide has got to.
    var focus: Double {
        Double(treadmill.simdPosition.z)
    }

    /// Puts map y `focus` under the pivot at once, stopping any glide.
    func setFocus(_ focus: Double) {
        treadmill.removeAction(forKey: Self.glideKey)
        treadmill.simdPosition.z = Float(focus)
    }

    /// Slides map y `focus` under the pivot, easing out of a flick.
    func glide(toFocus focus: Double, duration: Double) {
        treadmill.removeAction(forKey: Self.glideKey)
        let glide = SCNAction.move(to: SCNVector3(0, 0, Float(focus)), duration: duration)
        glide.timingMode = .easeOut
        treadmill.runAction(glide, forKey: Self.glideKey)
    }

    // MARK: - The van

    /// Puts the van at map y `y` along the road at once, facing up it.
    func parkVan(atY y: Double) {
        guard let lens, let van else { return }
        van.removeAction(forKey: Self.driveKey)
        van.simdPosition = SIMD3<Float>(TRCurvedLevelMapLens.local(lens.layout.roadPoint(atY: y)))
        van.simdEulerAngles.y = Float(MultiVanDioramaGeometry.yaw(facing: lens.layout.roadHeading(atY: y)))
        vanY = y
    }

    /// How long the van takes to drive from where it is to `y`.
    func driveDuration(toY y: Double) -> Double {
        guard let lens, let vanY else { return 0 }
        return TRLevelMapScene.duration(forLength: TRLevelMapScene.length(of: lens.layout.roadSamples(fromY: vanY, toY: y)))
    }

    /// Drives the van along the road to `y`, easing away and into its stop, while the
    /// map follows it to `focus`; returns how long that takes.
    @discardableResult
    func driveVan(toY y: Double, focus: Double) -> Double {
        guard let lens, let van, let vanY else { parkVan(atY: y); setFocus(focus); return 0 }
        let points = lens.layout.roadSamples(fromY: vanY, toY: y, spacing: 0.08)
        let length = TRLevelMapScene.length(of: points)
        guard points.count > 1, length > 0.01 else { parkVan(atY: y); setFocus(focus); return 0 }
        let total = TRLevelMapScene.duration(forLength: length)
        var actions: [SCNAction] = []
        var travelled = 0.0, elapsed = 0.0
        for (from, to) in zip(points, points.dropFirst()) {
            travelled += hypot(to.x - from.x, to.y - from.y)
            // Smoothstep easing: the time to reach this far along the road.
            let time = total * TRLevelMapScene.easedTime(progress: travelled / length)
            let duration = max(time - elapsed, 0.001)
            elapsed = time
            let yaw = MultiVanDioramaGeometry.yaw(facing: RoadVector(x: to.x - from.x, y: to.y - from.y))
            actions.append(.group([
                .move(to: SCNVector3(TRCurvedLevelMapLens.local(to)), duration: duration),
                .rotateTo(x: 0, y: CGFloat(yaw), z: 0, duration: min(duration * 2, 0.12), usesShortestUnitArc: true),
            ]))
        }
        van.removeAction(forKey: Self.driveKey)
        van.runAction(.sequence(actions), forKey: Self.driveKey)
        treadmill.removeAction(forKey: Self.glideKey)
        let follow = SCNAction.move(to: SCNVector3(0, 0, Float(focus)), duration: total)
        follow.timingFunction = smoothstep
        treadmill.runAction(follow, forKey: Self.glideKey)
        self.vanY = y
        return total
    }

    // MARK: - Building

    /// The island's lawn over a block of soil, both cut into thin strips along the
    /// road so the bend has vertices to move.
    private static func ground(lawn: SCNMaterial, depth: Double) -> SCNNode {
        let strips = Int((depth / 0.08).rounded(.up))
        let top = SCNPlane(width: TRLevelMapLayout.width, height: depth)
        top.heightSegmentCount = strips
        // SCNPlane puts the image's top at its +y edge, which lies far from the lens.
        top.materials = [lawn]
        let ground = SCNNode()
        let lawnNode = SCNNode(geometry: top)
        lawnNode.simdEulerAngles.x = -.pi / 2
        lawnNode.simdPosition.z = Float(-depth / 2)
        ground.addChildNode(lawnNode)

        let soil = SCNBox(width: TRLevelMapLayout.width - 0.1, height: 0.8, length: depth - 0.1, chamferRadius: 0)
        soil.lengthSegmentCount = strips
        soil.heightSegmentCount = 4
        soil.materials = [MultiVanDioramaScene.paper(
            texture: MultiVanDioramaScene.grain(on: UIColor(dioramaHex: 0xA26E48), dots: 2600, seed: 13),
            tiles: CGSize(width: depth / 2, height: 1)
        )]
        let soilNode = SCNNode(geometry: soil)
        soilNode.simdPosition = SIMD3(0, -0.402, Float(-depth / 2))
        ground.addChildNode(soilNode)
        return ground
    }

    /// Plain grass round the island, out past the horizon on either side and off
    /// both ends, so the world rolls on beyond the map. In strips that meet the
    /// island's edges rather than lying under it.
    private static func apron(depth: Double) -> SCNNode {
        let reach = 30.0, overhang = 12.0
        let grass = MultiVanDioramaScene.paper(
            texture: MultiVanDioramaScene.grain(on: MultiVanDioramaLawn.Palette.lawn, dots: 900, seed: 19),
            tiles: CGSize(width: 1, height: 1)
        )
        grass.diffuse.wrapS = .repeat
        grass.diffuse.wrapT = .repeat
        grass.diffuse.mipFilter = .linear
        // Down to the island's lawn, whose print is darkened by its stripes and grain.
        grass.multiply.contents = UIColor(red: 0.81, green: 0.78, blue: 0.86, alpha: 1)
        let halfWidth = TRLevelMapLayout.width / 2
        let length = depth + overhang * 2
        // x, z of each strip's middle, and its width and length.
        let strips: [(Double, Double, Double, Double)] = [
            (-halfWidth - reach / 2, -depth / 2, reach, length),
            (halfWidth + reach / 2, -depth / 2, reach, length),
            (0, overhang / 2, halfWidth * 2, overhang),
            (0, -depth - overhang / 2, halfWidth * 2, overhang),
        ]
        let apron = SCNNode()
        for (x, z, width, length) in strips {
            let plane = SCNPlane(width: width, height: length)
            plane.heightSegmentCount = Int((length / 0.15).rounded(.up))
            let material = grass.copy() as! SCNMaterial
            // About two units of grain to each tile.
            material.diffuse.contentsTransform = SCNMatrix4MakeScale(Float(width / 2), Float(length / 2), 1)
            plane.materials = [material]
            let node = SCNNode(geometry: plane)
            node.simdEulerAngles.x = -.pi / 2
            node.simdPosition = SIMD3(Float(x), 0, Float(z))
            apron.addChildNode(node)
        }
        return apron
    }

    /// Trees and bushes scattered over the apron, thickest along the island's edges
    /// so the lawn's printed edge hides among them.
    private func placeApronScenery(depth: Double) {
        var random = MultiVanDioramaRandom(seed: 53)
        let halfWidth = TRLevelMapLayout.width / 2
        for index in 0..<Int(depth * 9) {
            let side: Double = index.isMultiple(of: 2) ? 1 : -1
            // Squared, so most stand near the island.
            let out = random.next() * random.next() * 7
            let point = RoadPoint(x: side * (halfWidth + 0.15 + out), y: -6 + random.next() * (depth + 12))
            let kind: MultiVanDioramaScenery.Kind
            let height: Double
            switch random.next() {
            case ..<0.3: kind = .tree(.pine); height = 0.7 + random.next() * 0.4
            case ..<0.75: kind = .tree(.round(Int(random.next() * 3))); height = 0.65 + random.next() * 0.4
            default: kind = .bush(Int(random.next() * 3)); height = 0.18 + random.next() * 0.08
            }
            guard let node = MultiVanDioramaPieces.scenery(kind, height: height) else { continue }
            node.simdPosition = SIMD3<Float>(TRCurvedLevelMapLens.local(point))
            node.simdEulerAngles.y = Float((random.next() - 0.5) * 0.6)
            treadmill.addChildNode(node)
        }
    }

    /// Cutouts and houses stand where the flat map's scenery put them, each cutout a
    /// little off square and every house facing the road.
    private func place(_ scenery: TRLevelMapScenery) {
        for item in scenery.items {
            guard let node = MultiVanDioramaPieces.scenery(item.kind, height: item.height) else { continue }
            node.simdPosition = SIMD3<Float>(TRCurvedLevelMapLens.local(item.point))
            node.simdEulerAngles.y = Float(sin(item.point.x * 12.9 + item.point.y * 78.2) * 0.3)
            treadmill.addChildNode(node)
        }
        for house in scenery.houses {
            let node = MultiVanDioramaPieces.house(house.color)
            node.simdPosition = SIMD3<Float>(TRCurvedLevelMapLens.local(house.point))
            node.simdEulerAngles.y = Float(MultiVanDioramaGeometry.yaw(facing: house.facing))
            treadmill.addChildNode(node)
        }
        for pond in scenery.ponds {
            let node = MultiVanDioramaPieces.pond(pond)
            let centre = TRCurvedLevelMapLens.local(pond.centre)
            node.simdPosition.x = Float(centre.x)
            node.simdPosition.z = Float(centre.z)
            treadmill.addChildNode(node)
        }
    }

    /// A wooden post with a card on top that always faces the lens; returns the post
    /// and the card, for its tile art. The bend gives the card a material of its own.
    private static func sign() -> (SCNNode, SCNNode) {
        let width = TRCurvedLevelMapLens.Sign.width, postHeight = TRCurvedLevelMapLens.Sign.postHeight
        let wood = MultiVanDioramaScene.paper(color: UIColor(dioramaHex: 0x9A6A3F), roughness: 0.8)
        Self.fadesAhead(wood)
        let post = SCNBox(width: 0.06, height: postHeight, length: 0.06, chamferRadius: 0.012)
        post.heightSegmentCount = 3
        post.materials = [wood]
        let sign = SCNNode()
        let postNode = SCNNode(geometry: post)
        postNode.simdPosition.y = Float(postHeight / 2)
        sign.addChildNode(postNode)

        let plane = SCNPlane(width: width, height: width)
        let card = SCNMaterial()
        // Unlit, so the tile reads as it does on the flat map, in sun or in shade.
        card.lightingModel = .constant
        card.transparencyMode = .aOne
        card.isDoubleSided = true
        Self.fadesAhead(card)
        plane.materials = [card]
        let face = SCNNode(geometry: plane)
        // The tile, not the card's margin round it, stands on the post.
        face.simdPosition.y = Float(width * TRCurvedLevelMapLens.Sign.tileShare / 2)
        // A sign fading out ahead would leave its shadow behind.
        postNode.castsShadow = false
        face.castsShadow = false
        let mount = SCNNode()
        mount.simdPosition.y = Float(postHeight)
        // Turned to the lens about its foot, so it stands on the post.
        mount.constraints = [SCNBillboardConstraint()]
        mount.addChildNode(face)
        sign.addChildNode(mount)
        return (sign, face)
    }

    /// Fades a sign out as it nears the horizon: by where its node stands, so the
    /// whole sign fades together, however its card is turned.
    private static let signFade = """
        #pragma arguments
        float signFadeStart;
        float signFadeEnd;
        #pragma transparent
        #pragma body
        float ahead = -scn_node.modelTransform[3].z;
        _output.color *= 1.0 - smoothstep(signFadeStart, signFadeEnd, ahead);
        """

    private static func fadesAhead(_ material: SCNMaterial) {
        material.shaderModifiers = [.fragment: signFade]
        material.setValue(Float(TRCurvedLevelMapLens.Sign.fadeStart), forKey: "signFadeStart")
        material.setValue(Float(TRCurvedLevelMapLens.Sign.fadeEnd), forKey: "signFadeEnd")
    }

    /// The flat map's tile, drawn once with room around it for its glow and badges.
    private static func signImage(_ art: SignArt) -> UIImage? {
        let side = TRLevelTile.size.width / TRCurvedLevelMapLens.Sign.tileShare
        let renderer = ImageRenderer(content:
            TRLevelTile(levelNumber: art.levelNumber, state: art.state, stars: art.stars, action: {})
                .frame(width: side, height: side)
        )
        renderer.scale = 4
        renderer.isOpaque = false
        return renderer.uiImage
    }

    /// The gameplay table's warm sun, fixed to the lens, its shadow box over the
    /// stretch of road in view.
    private static func sun() -> SCNNode {
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
        light.orthographicScale = 6
        light.zNear = 1
        light.zFar = 40
        let node = SCNNode()
        node.light = light
        let middle = SIMD3<Float>(0, 0, -3)
        node.simdPosition = middle + SIMD3(-5.2, 8.2, 3.6)
        node.simdLook(at: middle, up: SIMD3(0, 1, 0), localFront: SCNNode.simdLocalFront)
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

/// The map's follow of a drive, eased as the van's progress is; outside the scene
/// so SceneKit can call it from its render thread.
private let smoothstep: (Float) -> Float = { t in t * t * (3 - 2 * t) }
