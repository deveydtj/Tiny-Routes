import SceneKit
import UIKit

/// Node builders for the diorama's toy pieces: papercraft houses, chunky vans, switch
/// dials, roadblocks, and the scenery's cutouts and pond. Each builder returns a piece standing on its own origin with
/// its front towards +z; `MultiVanDioramaScene` places and turns it. Parts that later
/// tasks animate carry the names in `Part`.
///
/// Red and blue bodies print the same grey, so the colour's symbol is what tells
/// pieces apart without colour vision: every house and van shows it from any side
/// the lens can see, in an ink that keeps its contrast on white.
@MainActor
enum MultiVanDioramaPieces {
    enum Part {
        /// A house's walls and roof, which squash on a delivery.
        static let houseBody = "body"
        /// Where a house's smoke rises from.
        static let chimney = "chimney"
        /// A van's body without its wheels, which rumbles while it waits.
        static let chassis = "chassis"
        /// A van's body, wheels and shadow, which skew off the road on a crash.
        static let pose = "pose"
        static let leftLamps = "lamps.left"
        static let rightLamps = "lamps.right"
        /// Turns about +y to point a dial's arrow at its active exit.
        static let pivot = "pivot"
        static let arrow = "arrow"
        static let dialFace = "face"
        /// A scenery cutout, which sways about its foot.
        static let sway = "sway"
    }

    /// Sizes from the HTML prototype, in grid units before each piece's scale.
    enum Measure {
        static let houseScale: Float = 1.28
        static let houseWidth = 0.62
        static let houseDepth = 0.5
        static let wallHeight = 0.34
        static let roofRise = 0.27
        static let chimneyHeight = 0.2
        static let vanScale: Float = 1.15
        static let dialScale: Float = 1.12
        static let dialRadius = 0.27
        static let barrierHeight = 0.3
        /// Cones stand either side of the road, a little past its end.
        static let coneSpacing = 0.27
        static let coneSetback = 0.1
    }

    // MARK: - Houses

    /// A papercraft house: siding walls, a gabled roof in the colour, a chimney and a
    /// front step. The front carries a symbol plaque over the door, and each roof
    /// slope a symbol badge, so a house facing away still shows its symbol.
    static func house(_ color: VanColor) -> SCNNode {
        let width = Measure.houseWidth, depth = Measure.houseDepth, wallHeight = Measure.wallHeight
        let body = SCNNode()
        body.name = Part.houseBody

        let side = paper(texture: Texture.houseSide)
        let plain = paper(color: UIColor(dioramaHex: 0xF3E8D3))
        let walls = SCNBox(width: width, height: wallHeight, length: depth, chamferRadius: 0)
        // SCNBox order: front, right, back, left, top, bottom.
        walls.materials = [paper(texture: Texture.houseFront(color)), side, side, side, plain, plain]
        body.addChildNode(SCNNode(geometry: walls, y: wallHeight / 2))

        let eave = width / 2 + 0.06
        let gable = UIBezierPath()
        gable.move(to: CGPoint(x: -eave, y: 0))
        gable.addLine(to: CGPoint(x: eave, y: 0))
        gable.addLine(to: CGPoint(x: 0, y: Measure.roofRise))
        gable.close()
        let roof = SCNShape(path: gable, extrusionDepth: depth + 0.1)
        let gableEnd = paper(color: UIColor(dioramaHex: 0xF6ECD8))
        roof.materials = [gableEnd, gableEnd, paper(texture: Texture.roof(color))]
        body.addChildNode(SCNNode(geometry: roof, y: wallHeight))

        // A badge on each slope, a hair above it, the symbol's top towards the back
        // so it reads upright on a house that faces the lens.
        let slope = atan2(Measure.roofRise, eave)
        for sign in [-1.0, 1.0] {
            let badge = decal(color, side: 0.3)
            let normal = SIMD3(sign * sin(slope), cos(slope), 0)
            badge.simdPosition = SIMD3<Float>(SIMD3(sign * eave / 2, wallHeight + Measure.roofRise / 2, 0) + normal * 0.004)
            badge.simdOrientation = simd_quatf(angle: Float(-sign * slope), axis: SIMD3(0, 0, 1))
                * simd_quatf(angle: -.pi / 2, axis: SIMD3(1, 0, 0))
            body.addChildNode(badge)
        }

        let chimney = SCNBox(width: 0.08, height: Measure.chimneyHeight, length: 0.08, chamferRadius: 0)
        chimney.materials = [paper(texture: Texture.chimney)]
        let chimneyNode = SCNNode(geometry: chimney, y: wallHeight + 0.2)
        chimneyNode.name = Part.chimney
        chimneyNode.simdPosition.x = Float(width * 0.24)
        chimneyNode.simdPosition.z = -0.08
        body.addChildNode(chimneyNode)

        let step = SCNBox(width: 0.2, height: 0.03, length: 0.08, chamferRadius: 0)
        step.materials = [paper(color: UIColor(dioramaHex: 0xE3D5BB))]
        let stepNode = SCNNode(geometry: step, y: 0.015)
        stepNode.simdPosition.z = Float(depth / 2 + 0.04)
        body.addChildNode(stepNode)

        let house = SCNNode()
        house.addChildNode(body)
        house.simdScale = SIMD3(repeating: Measure.houseScale)
        return house
    }

    // MARK: - Vans

    /// A chunky toy van, nose towards +z: rounded body over a darker skirt, dark
    /// glass, a white roof with the colour's symbol, lamps, and a soft contact shadow.
    static func van(_ color: VanColor) -> SCNNode {
        let chassis = SCNNode()
        chassis.name = Part.chassis
        let body = toy(color.dioramaBody), glass = toy(UIColor(dioramaHex: 0x2C3A55))

        chassis.addChildNode(box(0.27, 0.19, 0.44, chamfer: 0.05, body, at: SIMD3(0, 0.16, 0)))
        chassis.addChildNode(box(0.28, 0.05, 0.45, chamfer: 0.02, toy(color.dioramaDeep), at: SIMD3(0, 0.085, 0)))
        chassis.addChildNode(box(0.24, 0.08, 0.06, chamfer: 0.02, glass, at: SIMD3(0, 0.2, 0.2)))
        chassis.addChildNode(box(0.276, 0.06, 0.12, chamfer: 0, glass, at: SIMD3(0, 0.205, 0.11)))
        chassis.addChildNode(box(0.21, 0.03, 0.3, chamfer: 0.012, toy(UIColor(dioramaHex: 0xFBF7EE)), at: SIMD3(0, 0.26, -0.03)))
        let roofDecal = decal(color, side: 0.19)
        roofDecal.simdPosition = SIMD3(0, 0.277, -0.03)
        // Lying on the roof with the symbol's top towards the nose, as the flat board prints it.
        roofDecal.simdOrientation = simd_quatf(angle: .pi, axis: SIMD3(0, 1, 0)) * simd_quatf(angle: -.pi / 2, axis: SIMD3(1, 0, 0))
        chassis.addChildNode(roofDecal)

        // Each side's lamps have their own materials, so a turn signal lights one side.
        for (name, x) in [(Part.leftLamps, 0.085), (Part.rightLamps, -0.085)] {
            let side = SCNNode()
            side.name = name
            side.addChildNode(box(0.05, 0.03, 0.02, chamfer: 0, toy(.white), at: SIMD3(x, 0.13, 0.222)))
            side.addChildNode(box(0.045, 0.03, 0.02, chamfer: 0, toy(.white), at: SIMD3(x, 0.13, -0.222)))
            chassis.addChildNode(side)
        }
        setLamps(chassis, left: .off, right: .off)

        let pose = SCNNode()
        pose.name = Part.pose
        pose.addChildNode(chassis)
        let tire = SCNCylinder(radius: 0.056, height: 0.045)
        tire.radialSegmentCount = 16
        tire.materials = [toy(UIColor(dioramaHex: 0x2A2933))]
        let hub = SCNCylinder(radius: 0.024, height: 0.05)
        hub.radialSegmentCount = 10
        hub.materials = [toy(UIColor(dioramaHex: 0xE9E4DA))]
        for (x, z) in [(-0.13, 0.14), (0.13, 0.14), (-0.13, -0.14), (0.13, -0.14)] {
            let wheel = SCNNode()
            wheel.addChildNode(SCNNode(geometry: tire))
            wheel.addChildNode(SCNNode(geometry: hub))
            wheel.simdPosition = SIMD3(Float(x), 0.056, Float(z))
            // Cylinders stand on +y; the axle runs along x.
            wheel.simdEulerAngles.z = .pi / 2
            pose.addChildNode(wheel)
        }
        pose.addChildNode(contactShadow(width: 0.46, length: 0.62))
        let van = SCNNode()
        van.addChildNode(pose)
        van.simdScale = SIMD3(repeating: Measure.vanScale)
        return van
    }

    enum Lamp: Equatable {
        case off
        /// An amber turn signal, bright or between flashes.
        case signal(lit: Bool)
    }

    /// Head and tail lamps on each side of a van's chassis; its left is +x.
    static func setLamps(_ chassis: SCNNode, left: Lamp, right: Lamp) {
        for (name, lamp) in [(Part.leftLamps, left), (Part.rightLamps, right)] {
            guard let side = chassis.childNode(withName: name, recursively: false) else { continue }
            for (index, node) in side.childNodes.enumerated() {
                guard let material = node.geometry?.firstMaterial else { continue }
                let isHead = index == 0
                switch lamp {
                case .off:
                    material.diffuse.contents = isHead ? Lamps.head : Lamps.tail
                    material.emission.contents = isHead ? Lamps.headGlow : UIColor.black
                    material.emission.intensity = 0.6
                case .signal(let lit):
                    material.diffuse.contents = Lamps.amber
                    material.emission.contents = Lamps.amber
                    material.emission.intensity = lit ? 1.4 : 0.05
                }
            }
        }
    }

    private enum Lamps {
        static let head = UIColor(dioramaHex: 0xFFF6C8)
        static let headGlow = UIColor(dioramaHex: 0xFFE58A)
        static let tail = UIColor(dioramaHex: 0xD33B30)
        static let amber = UIColor(dioramaHex: 0xFFAB1F)
    }

    // MARK: - Switch dials

    /// A cream dial on a paper base, with a dot at every exit and an arrow on
    /// `Part.pivot`. Angles are the flat board's: screen radians, 0 pointing right
    /// and positive turning clockwise, as `SwitchArrowDirectionResolver` gives them.
    static func dial(optionAngles: [Double], activeAngle: Double, tint: MultiVanSwitchDialView.Tint) -> SCNNode {
        let base = SCNCone(topRadius: Measure.dialRadius, bottomRadius: Measure.dialRadius + 0.025, height: 0.05)
        base.radialSegmentCount = 48
        base.materials = [paper(color: UIColor(dioramaHex: 0xFFFAF0))]
        let face = SCNCylinder(radius: 0.225, height: 0.012)
        face.radialSegmentCount = 48
        face.materials = [paper(color: Dial.face)]

        let dial = SCNNode()
        dial.addChildNode(SCNNode(geometry: base, y: 0.025))
        let faceNode = SCNNode(geometry: face, y: 0.056)
        faceNode.name = Part.dialFace
        dial.addChildNode(faceNode)

        let dot = SCNCylinder(radius: 0.026, height: 0.016)
        dot.radialSegmentCount = 12
        dot.materials = [paper(color: UIColor(dioramaHex: 0xC3B392))]
        for angle in optionAngles {
            let direction = MultiVanDioramaGeometry.worldDirection(screenAngle: angle)
            let node = SCNNode(geometry: dot, y: 0.058)
            node.simdPosition.x = Float(direction.x * 0.235)
            node.simdPosition.z = Float(direction.z * 0.235)
            dial.addChildNode(node)
        }

        let arrow = SCNShape(path: arrowPath(), extrusionDepth: 0.035)
        arrow.chamferRadius = 0.008
        arrow.materials = [paper(color: Dial.arrow)]
        let arrowNode = SCNNode(geometry: arrow)
        arrowNode.name = Part.arrow
        // The path's plane becomes the dial face, its point along +x.
        arrowNode.simdEulerAngles.x = -.pi / 2
        arrowNode.simdPosition.y = 0.0175
        let pivot = SCNNode()
        pivot.name = Part.pivot
        pivot.simdPosition.y = 0.064
        pivot.addChildNode(arrowNode)
        dial.addChildNode(pivot)

        dial.simdScale = SIMD3(repeating: Measure.dialScale)
        setDial(dial, activeAngle: activeAngle, tint: tint)
        return dial
    }

    /// Points a dial at `activeAngle` and tints it like the flat board's knob: an
    /// orange face for a live switch, a grey arrow while it is locked.
    static func setDial(_ dial: SCNNode, activeAngle: Double, tint: MultiVanSwitchDialView.Tint) {
        dial.childNode(withName: Part.pivot, recursively: false)?.simdEulerAngles.y = arrowYaw(activeAngle: activeAngle)
        tintDial(dial, tint)
    }

    /// The pivot's yaw that points the arrow, which lies along +x, at `activeAngle`.
    static func arrowYaw(activeAngle: Double) -> Float {
        Float(MultiVanDioramaGeometry.yaw(screenAngle: activeAngle) - .pi / 2)
    }

    static func tintDial(_ dial: SCNNode, _ tint: MultiVanSwitchDialView.Tint) {
        let face = dial.childNode(withName: Part.dialFace, recursively: false)?.geometry?.firstMaterial
        face?.diffuse.contents = tint == .live ? Dial.liveFace : Dial.face
        let arrow = dial.childNode(withName: Part.arrow, recursively: true)?.geometry?.firstMaterial
        arrow?.diffuse.contents = tint == .locked ? Dial.lockedArrow : Dial.arrow
    }

    private enum Dial {
        static let face = UIColor(dioramaHex: 0xF0E3C8)
        static let liveFace = UIColor(dioramaHex: 0xFF8C29)
        static let arrow = UIColor(dioramaHex: 0x3B3A55)
        static let lockedArrow = UIColor(dioramaHex: 0xAAA395)
    }

    /// Points along +x: a shaft and a broad head, centred on the dial.
    private static func arrowPath() -> UIBezierPath {
        let path = UIBezierPath()
        let points: [(Double, Double)] = [(-0.13, -0.042), (0.03, -0.042), (0.03, -0.1), (0.17, 0), (0.03, 0.1), (0.03, 0.042), (-0.13, 0.042)]
        path.move(to: CGPoint(x: points[0].0, y: points[0].1))
        points.dropFirst().forEach { path.addLine(to: CGPoint(x: $0.0, y: $0.1)) }
        path.close()
        return path
    }

    // MARK: - Roadblocks

    /// A striped barrier cutout between two traffic cones, for a road that runs
    /// towards `roadYaw`. Turned to `roadYaw`, the cones stand across the road and
    /// the cutout, like all the board's cutouts, faces the lens at its resting angle.
    static func roadblock(roadYaw: Double) -> SCNNode {
        let roadblock = SCNNode()
        let barrier = standee(Texture.barrier, height: Measure.barrierHeight)
        barrier.simdEulerAngles.y = Float(MultiVanDioramaCamera.restingYaw - roadYaw)
        roadblock.addChildNode(barrier)
        for side in [-1.0, 1.0] {
            let cone = cone()
            cone.simdPosition = SIMD3(Float(side * Measure.coneSpacing), 0, Float(Measure.coneSetback - MultiVanDioramaGeometry.roadblockSetback))
            roadblock.addChildNode(cone)
        }
        return roadblock
    }

    private static func cone() -> SCNNode {
        let orange = toy(UIColor(dioramaHex: 0xF58A2C))
        let body = SCNCone(topRadius: 0, bottomRadius: 0.05, height: 0.13)
        body.radialSegmentCount = 18
        body.materials = [orange]
        let band = SCNCone(topRadius: 0.031, bottomRadius: 0.037, height: 0.022)
        band.radialSegmentCount = 18
        band.materials = [toy(.white)]
        let cone = SCNNode()
        cone.addChildNode(SCNNode(geometry: body, y: 0.075))
        cone.addChildNode(SCNNode(geometry: band, y: 0.08))
        cone.addChildNode(box(0.11, 0.014, 0.11, chamfer: 0, toy(UIColor(dioramaHex: 0xE0701D)), at: SIMD3(0, 0.007, 0)))
        return cone
    }

    /// A paper cutout rooted at its base: printed front, kraft back.
    static func standee(_ cutout: Cutout, height: Double) -> SCNNode {
        let width = height * Double(cutout.front.size.width / cutout.front.size.height)
        let standee = SCNNode()
        for (image, turn) in [(cutout.front, Float(0)), (cutout.back, .pi)] {
            let plane = SCNPlane(width: width, height: height)
            let material = paper(texture: image, roughness: turn == 0 ? 0.9 : 0.95)
            // Blended rather than cut with a discard: SceneKit's shadow pass follows
            // the texture's alpha only on a blended material, and casts the whole
            // rectangle otherwise.
            material.transparencyMode = .aOne
            plane.materials = [material]
            let face = SCNNode(geometry: plane, y: height / 2)
            face.simdEulerAngles.y = turn
            standee.addChildNode(face)
        }
        return standee
    }

    // MARK: - Scenery

    /// A scenery cutout `height` tall, standing on its foot and facing +z, with the
    /// card itself on `Part.sway`. Nil for a flower bed, which the lawn paints, or
    /// for art missing from the asset catalog. Cutouts of a kind share geometry.
    static func scenery(_ kind: MultiVanDioramaScenery.Kind, height: Double) -> SCNNode? {
        guard let name = Texture.sceneryArtName(kind) else { return nil }
        let template: SCNNode
        if let cached = sceneryTemplates[name] {
            template = cached
        } else {
            guard let cutout = Texture.scenery(named: name) else {
                assertionFailure("Missing scenery art \(name)")
                return nil
            }
            template = standee(cutout, height: 1)
            template.name = Part.sway
            sceneryTemplates[name] = template
        }
        let node = SCNNode()
        node.addChildNode(template.clone())
        node.simdScale = SIMD3(repeating: Float(height))
        return node
    }

    private static var sceneryTemplates: [String: SCNNode] = [:]

    /// The pond's glassy water, lying over the pond the lawn paints and turned with it.
    static func pond(_ pond: MultiVanDioramaScenery.Pond) -> SCNNode {
        // The lawn's bank and water sit just outside this.
        let radiusX = pond.radiusX * 0.95, radiusY = pond.radiusY * 0.95
        let outline = UIBezierPath(ovalIn: CGRect(x: -radiusX, y: -radiusY, width: radiusX * 2, height: radiusY * 2))
        outline.flatness = 0.004
        let water = SCNShape(path: outline, extrusionDepth: 0)
        let material = MultiVanDioramaScene.paper(color: UIColor(dioramaHex: 0x8FD3EF), roughness: 0.08)
        material.metalness.contents = 0.1
        material.transparency = 0.55
        material.writesToDepthBuffer = false
        water.materials = [material]
        let surface = SCNNode(geometry: water)
        // The path's plane becomes the ground, its y away from the lens.
        surface.simdEulerAngles.x = -.pi / 2
        surface.castsShadow = false
        let node = SCNNode()
        node.addChildNode(surface)
        node.simdPosition.y = 0.006
        node.simdEulerAngles.y = Float(pond.angle)
        return node
    }

    // MARK: - Route previews

    /// One dot of a van's preview line, a sticker lying on the road: the van's
    /// colour inside a white rim, which reads on asphalt and grass alike. Dots of
    /// a colour share their geometry.
    static func trailDot(_ color: VanColor) -> SCNNode {
        let node = SCNNode(geometry: trailDotGeometry(color), y: 0.014)
        node.simdEulerAngles.x = -.pi / 2
        node.castsShadow = false
        return node
    }

    private static func trailDotGeometry(_ color: VanColor) -> SCNGeometry {
        if let geometry = trailDots[color] { return geometry }
        // A touch wider than a lane: neighbouring lines' rims overlap rather than leave a gap.
        let side = CGFloat(MultiVanDioramaTrail.laneWidth * 1.1)
        let dot = SCNPlane(width: side, height: side)
        let material = SCNMaterial()
        // Unlit, like the badges, so a line keeps its colour in the shade and
        // through the grade instead of sinking into the asphalt.
        material.lightingModel = .constant
        material.diffuse.contents = trailDotImage(color)
        material.diffuse.mipFilter = .linear
        material.transparencyMode = .aOne
        material.writesToDepthBuffer = false
        dot.materials = [material]
        trailDots[color] = dot
        return dot
    }

    private static func trailDotImage(_ color: VanColor) -> UIImage {
        let side = 64.0
        let format = MultiVanDioramaLawn.textureFormat(opaque: false)
        return UIGraphicsImageRenderer(size: CGSize(width: side, height: side), format: format).image { context in
            let g = context.cgContext
            g.setFillColor(UIColor(dioramaHex: 0xFBF8F1).cgColor)
            g.fillEllipse(in: CGRect(x: 1, y: 1, width: side - 2, height: side - 2))
            g.setFillColor(color.dioramaBody.cgColor)
            let inset = side * 0.11
            g.fillEllipse(in: CGRect(x: inset, y: inset, width: side - inset * 2, height: side - inset * 2))
        }
    }

    private static var trailDots: [VanColor: SCNGeometry] = [:]

    /// A ✓ or ✗ disc that always faces the lens: a preview's ending in the van's ink,
    /// or a delivered house's tick in green.
    static func badge(_ kind: Texture.BadgeKind, side: Double = 0.28) -> SCNNode {
        let node = SCNNode(geometry: badgeGeometry(kind, side: side))
        node.castsShadow = false
        node.constraints = [SCNBillboardConstraint()]
        return node
    }

    /// Shared by every badge of a kind, so a rebuilt trail's badge doesn't upload
    /// its texture again.
    private static func badgeGeometry(_ kind: Texture.BadgeKind, side: Double) -> SCNGeometry {
        let key = BadgeKey(kind: kind, side: side)
        if let geometry = badges[key] { return geometry }
        let plane = SCNPlane(width: side, height: side)
        let material = SCNMaterial()
        // Unlit, like the prototype's sprites, so it reads the same in the sun and in shade.
        material.lightingModel = .constant
        material.diffuse.contents = Texture.badge(kind)
        material.transparencyMode = .aOne
        plane.materials = [material]
        badges[key] = plane
        return plane
    }

    private struct BadgeKey: Hashable {
        let kind: Texture.BadgeKind
        let side: Double
    }

    private static var badges: [BadgeKey: SCNGeometry] = [:]

    // MARK: - Shared parts

    /// The colour's symbol sticker, lying in the plane's face.
    private static func decal(_ color: VanColor, side: Double) -> SCNNode {
        let plane = SCNPlane(width: side, height: side)
        let material = paper(texture: Texture.decal(color), roughness: 0.6)
        material.writesToDepthBuffer = false
        plane.materials = [material]
        let node = SCNNode(geometry: plane)
        node.castsShadow = false
        return node
    }

    /// A soft dark blot on the lawn under a piece, so it sits on the board.
    private static func contactShadow(width: Double, length: Double) -> SCNNode {
        let plane = SCNPlane(width: width, height: length)
        let material = SCNMaterial()
        material.lightingModel = .constant
        material.diffuse.contents = Texture.blob
        material.transparency = 0.8
        material.writesToDepthBuffer = false
        plane.materials = [material]
        let node = SCNNode(geometry: plane, y: 0.006)
        node.simdEulerAngles.x = -.pi / 2
        node.castsShadow = false
        return node
    }

    private static func box(
        _ width: Double, _ height: Double, _ length: Double, chamfer: Double, _ material: SCNMaterial, at position: SIMD3<Double>
    ) -> SCNNode {
        let box = SCNBox(width: width, height: height, length: length, chamferRadius: chamfer)
        box.chamferSegmentCount = 3
        box.materials = [material]
        let node = SCNNode(geometry: box)
        node.simdPosition = SIMD3<Float>(position)
        return node
    }

    private static func paper(color: UIColor = .white, texture: UIImage? = nil, roughness: CGFloat = 0.88) -> SCNMaterial {
        MultiVanDioramaScene.paper(color: color, texture: texture, roughness: roughness)
    }

    /// Glossy moulded plastic.
    private static func toy(_ color: UIColor) -> SCNMaterial {
        MultiVanDioramaScene.paper(color: color, roughness: 0.42)
    }
}

// MARK: - Parcels and signals

extension MultiVanDioramaPieces {
    enum CargoPart {
        /// The parcel on a van's roof, hidden until the van carries its cargo.
        static let roofParcel = "cargo.roof"
        /// The parcel waiting on a pickup's pad, hidden once it is collected.
        static let waitingParcel = "cargo.waiting"
        static let stopLamp = "signal.stop"
        static let goLamp = "signal.go"
        static let bridgeDeck = "signal.deck"
    }

    /// A kraft parcel tied in its owner's colour, the owner's shape on top.
    static func parcel(_ color: VanColor, side: Double = 0.2) -> SCNNode {
        let node = SCNNode()
        let kraft = MultiVanDioramaScene.paper(
            texture: MultiVanDioramaScene.grain(on: UIColor(dioramaHex: 0xC99A63), dots: 2600, seed: 23)
        )
        let height = side * 0.7
        node.addChildNode(box(side, height, side, chamfer: side * 0.05, kraft, at: SIMD3(0, height / 2, 0)))
        let ribbon = toy(color.dioramaBody)
        node.addChildNode(box(side * 1.03, height * 1.03, side * 0.2, chamfer: 0, ribbon, at: SIMD3(0, height / 2, 0)))
        node.addChildNode(box(side * 0.2, height * 1.03, side * 1.03, chamfer: 0, ribbon, at: SIMD3(0, height / 2, 0)))
        let label = decal(color, side: side * 0.72)
        label.simdPosition = SIMD3(0, Float(height * 1.04 + 0.002), 0)
        label.simdEulerAngles.x = -.pi / 2
        node.addChildNode(label)
        return node
    }

    /// A cream pad beside the road with a parcel on it, turned a little so it
    /// reads as set down, not printed.
    static func pickup(_ color: VanColor) -> SCNNode {
        let node = SCNNode()
        let pad = SCNCylinder(radius: 0.19, height: 0.018)
        pad.radialSegmentCount = 28
        pad.materials = [toy(UIColor(dioramaHex: 0xFBF7EE))]
        node.addChildNode(SCNNode(geometry: pad, y: 0.009))
        let rim = SCNTube(innerRadius: 0.19, outerRadius: 0.21, height: 0.02)
        rim.radialSegmentCount = 28
        rim.materials = [toy(color.dioramaDeep)]
        node.addChildNode(SCNNode(geometry: rim, y: 0.01))
        let parcel = parcel(color)
        parcel.name = CargoPart.waitingParcel
        parcel.simdPosition.y = 0.018
        parcel.simdEulerAngles.y = 0.35
        node.addChildNode(parcel)
        node.addChildNode(contactShadow(width: 0.52, length: 0.52))
        return node
    }

    /// Fixes a hidden parcel to the back of a van's roof; `setCarried` shows it.
    static func addRoofParcel(to van: SCNNode, color: VanColor) {
        guard let chassis = van.childNode(withName: Part.chassis, recursively: true) else { return }
        let parcel = parcel(color, side: 0.13)
        parcel.name = CargoPart.roofParcel
        parcel.simdPosition = SIMD3(0, 0.275, -0.12)
        parcel.isHidden = true
        chassis.addChildNode(parcel)
    }

    static func setCarried(_ van: SCNNode, _ carried: Bool) {
        van.childNode(withName: CargoPart.roofParcel, recursively: true)?.isHidden = !carried
    }

    static func setWaiting(_ pickup: SCNNode, _ waiting: Bool) {
        pickup.childNode(withName: CargoPart.waitingParcel, recursively: false)?.isHidden = !waiting
    }

    /// A short post with a lamp head facing back down its road. The head shows a
    /// red square or a green disc: the shape says stop or go without colour.
    static func signalPost(kind: MultiVanSignal.Kind) -> SCNNode {
        let node = SCNNode()
        let post = SCNCylinder(radius: 0.018, height: 0.3)
        post.materials = [toy(UIColor(dioramaHex: 0x3B3A55))]
        node.addChildNode(SCNNode(geometry: post, y: 0.15))
        let dark = toy(UIColor(dioramaHex: 0x2A2933))
        node.addChildNode(box(0.13, 0.13, 0.05, chamfer: 0.012, dark, at: SIMD3(0, 0.36, 0)))
        let stop = box(0.08, 0.08, 0.02, chamfer: 0.004, glowing(UIColor(dioramaHex: 0xEC5B4B)), at: SIMD3(0, 0.36, 0.03))
        stop.name = CargoPart.stopLamp
        node.addChildNode(stop)
        let lens = SCNCylinder(radius: 0.043, height: 0.02)
        lens.radialSegmentCount = 20
        lens.materials = [glowing(UIColor(dioramaHex: 0x4CB862))]
        let go = SCNNode(geometry: lens)
        go.name = CargoPart.goLamp
        go.simdPosition = SIMD3(0, 0.36, 0.03)
        go.simdEulerAngles.x = .pi / 2
        node.addChildNode(go)
        if kind == .drawbridge {
            // A striped arm across the road: down while the bridge is up.
            let arm = box(0.4, 0.03, 0.03, chamfer: 0.006, toy(UIColor(dioramaHex: 0xEC5B4B)), at: SIMD3(0.2, 0, 0))
            let pivot = SCNNode()
            pivot.name = CargoPart.bridgeDeck
            pivot.simdPosition = SIMD3(0, 0.2, 0)
            pivot.addChildNode(arm)
            node.addChildNode(pivot)
        }
        node.addChildNode(contactShadow(width: 0.2, length: 0.2))
        return node
    }

    /// Shows a post's go or stop lamp; a drawbridge's arm lifts clear on go.
    static func setSignal(_ post: SCNNode, isOpen: Bool, animates: Bool) {
        post.childNode(withName: CargoPart.goLamp, recursively: false)?.isHidden = !isOpen
        post.childNode(withName: CargoPart.stopLamp, recursively: false)?.isHidden = isOpen
        guard let arm = post.childNode(withName: CargoPart.bridgeDeck, recursively: false) else { return }
        let angle: CGFloat = isOpen ? .pi / 2.2 : 0
        arm.removeAllActions()
        if animates {
            arm.runAction(.rotateTo(x: 0, y: 0, z: angle, duration: 0.25, usesShortestUnitArc: true))
        } else {
            arm.simdEulerAngles.z = Float(angle)
        }
    }

    /// A lamp that reads in shade as well as in the sun.
    private static func glowing(_ color: UIColor) -> SCNMaterial {
        let material = toy(color)
        material.emission.contents = color
        material.emission.intensity = 0.6
        return material
    }
}

// MARK: - Printed art

extension MultiVanDioramaPieces {
    /// A die-cut piece of card: the art inside a white border, and its plain back,
    /// mirrored as it is seen from behind.
    struct Cutout {
        let front: UIImage
        let back: UIImage

        init(size: CGSize, border: CGFloat = 7, draw: (CGContext, CGSize) -> Void) {
            let renderer = UIGraphicsImageRenderer(size: size, format: MultiVanDioramaLawn.textureFormat(opaque: false))
            self.init(art: renderer.image { draw($0.cgContext, size) }, border: border)
        }

        /// Die-cuts `art`, a picture on a clear ground, one texel per pixel.
        init(art: UIImage, border: CGFloat = 7) {
            let size = CGSize(width: art.size.width * art.scale, height: art.size.height * art.scale)
            let renderer = UIGraphicsImageRenderer(size: size, format: MultiVanDioramaLawn.textureFormat(opaque: false))
            let bounds = CGRect(origin: .zero, size: size)
            let silhouette = renderer.image { context in
                art.draw(in: bounds)
                UIColor.white.setFill()
                context.fill(bounds, blendMode: .sourceIn)
            }
            let front = renderer.image { context in
                for index in 0..<20 {
                    let angle = Double(index) / 20 * 2 * .pi
                    silhouette.draw(at: CGPoint(x: cos(angle) * border, y: sin(angle) * border))
                }
                art.draw(in: bounds)
                MultiVanDioramaLawn.addGrain(context.cgContext, alpha: 0.09, blendMode: .sourceAtop)
            }
            self.front = front
            back = renderer.image { context in
                let g = context.cgContext
                g.translateBy(x: size.width, y: 0)
                g.scaleBy(x: -1, y: 1)
                front.draw(at: .zero)
                UIColor(dioramaHex: 0xE2D2B4).setFill()
                context.fill(bounds, blendMode: .sourceIn)
                MultiVanDioramaLawn.addGrain(g, alpha: 0.12, blendMode: .sourceAtop)
            }
        }
    }

    @MainActor
    enum Texture {
        enum BadgeKind: Hashable {
            case ending(MultiVanPreviewEnding, VanColor)
            case delivered
        }

        static func decal(_ color: VanColor) -> UIImage { decals[color]! }

        static func badge(_ kind: BadgeKind) -> UIImage {
            if let image = badges[kind] { return image }
            let image = makeBadge(kind)
            badges[kind] = image
            return image
        }

        private static var badges: [BadgeKind: UIImage] = [:]

        /// White die-cut disc, an inked disc inside, and a white ✓ or ✗ on it: the
        /// stroke's shape carries the meaning in grayscale, the ink tells vans apart.
        private static func makeBadge(_ kind: BadgeKind) -> UIImage {
            let ink: UIColor, isTick: Bool
            switch kind {
            case let .ending(ending, color):
                ink = color.dioramaInk
                isTick = ending == .matchingHouse
            case .delivered:
                ink = UIColor(dioramaHex: 0x2F8F4E)
                isTick = true
            }
            return image(width: 128, height: 128, opaque: false) { g in
                disc(g, CGPoint(x: 64, y: 64), 60, 0xFFFFFF)
                g.setFillColor(ink.cgColor)
                g.fillEllipse(in: CGRect(x: 14, y: 14, width: 100, height: 100))
                g.setStrokeColor(UIColor.white.cgColor)
                g.setLineWidth(13)
                g.setLineCap(.round)
                g.setLineJoin(.round)
                if isTick {
                    g.addLines(between: [CGPoint(x: 40, y: 66), CGPoint(x: 57, y: 83), CGPoint(x: 88, y: 48)])
                } else {
                    g.addLines(between: [CGPoint(x: 45, y: 45), CGPoint(x: 83, y: 83)])
                    g.addLines(between: [CGPoint(x: 83, y: 45), CGPoint(x: 45, y: 83)])
                }
                g.strokePath()
            }
        }

        static func houseFront(_ color: VanColor) -> UIImage { fronts[color]! }

        /// The asset catalog's art for a scenery cutout; nil for a flower bed.
        static func sceneryArtName(_ kind: MultiVanDioramaScenery.Kind) -> String? {
            switch kind {
            case .tree(.round(let palette)): "Diorama/RoundTree\(palette + 1)"
            case .tree(.pine): "Diorama/PineTree"
            case .bush(let variant): "Diorama/Bush\(variant + 1)"
            case .resident(let variant): "Diorama/Resident\(variant + 1)"
            case .flowers: nil
            }
        }

        static func scenery(named name: String) -> Cutout? {
            if let cutout = sceneryCutouts[name] { return cutout }
            guard let art = UIImage(named: name) else { return nil }
            let cutout = Cutout(art: art)
            sceneryCutouts[name] = cutout
            return cutout
        }

        private static var sceneryCutouts: [String: Cutout] = [:]

        private static let decals = Dictionary(uniqueKeysWithValues: VanColor.allCases.map { ($0, makeDecal($0)) })
        private static let fronts = Dictionary(uniqueKeysWithValues: VanColor.allCases.map { ($0, makeHouseFront($0)) })
        private static let roofs = Dictionary(uniqueKeysWithValues: VanColor.allCases.map {
            ($0, MultiVanDioramaScene.grain(on: $0.dioramaBody, dots: 2600, seed: 5))
        })

        static let houseSide = image(width: 256, height: 240, opaque: true) { g in
            fill(g, 0xF3E8D3, CGRect(x: 0, y: 0, width: 256, height: 240))
            siding(g, width: 256, height: 240)
            window(g, x: 98, y: 80, glass: 0x8CC3E0, mullions: false)
            MultiVanDioramaLawn.addGrain(g, alpha: 0.08)
        }

        static let barrier = Cutout(size: CGSize(width: 300, height: 200)) { g, size in
            let w = size.width, h = size.height
            fill(g, 0x5D5A6E, CGRect(x: w * 0.18, y: h * 0.3, width: 14, height: h * 0.62))
            fill(g, 0x5D5A6E, CGRect(x: w * 0.82 - 14, y: h * 0.3, width: 14, height: h * 0.62))
            g.saveGState()
            g.addPath(CGPath(roundedRect: CGRect(x: w * 0.08, y: h * 0.28, width: w * 0.84, height: h * 0.3), cornerWidth: 10, cornerHeight: 10, transform: nil))
            g.clip()
            fill(g, 0xFFFFFF, CGRect(origin: .zero, size: size))
            g.setFillColor(UIColor(dioramaHex: 0xE8473B).cgColor)
            for x in stride(from: -h, to: w + h, by: 46) {
                g.move(to: CGPoint(x: x, y: h * 0.6))
                g.addLine(to: CGPoint(x: x + 23, y: h * 0.6))
                g.addLine(to: CGPoint(x: x + 23 + h * 0.34, y: h * 0.25))
                g.addLine(to: CGPoint(x: x + h * 0.34, y: h * 0.25))
                g.fillPath()
            }
            g.restoreGState()
            disc(g, CGPoint(x: w * 0.5, y: h * 0.17), 17, 0xF6A623)
            disc(g, CGPoint(x: w * 0.5 - 4, y: h * 0.17 - 5), 7, 0xFFE08A)
        }

        /// The van's contact shadow and the slab's shadow on the floor.
        static let blob = image(width: 128, height: 128, opaque: false) { g in
            let colors = [0.55, 0.22, 0].map { UIColor(red: 20 / 255, green: 30 / 255, blue: 20 / 255, alpha: $0).cgColor } as CFArray
            let gradient = CGGradient(colorsSpace: nil, colors: colors, locations: [0, 0.6, 1])!
            let centre = CGPoint(x: 64, y: 64)
            g.drawRadialGradient(gradient, startCenter: centre, startRadius: 4, endCenter: centre, endRadius: 62, options: [])
        }

        static func roof(_ color: VanColor) -> UIImage { roofs[color]! }

        static let chimney = MultiVanDioramaScene.grain(on: UIColor(dioramaHex: 0xC76A4E), dots: 2600, seed: 5)

        /// The symbol as a sticker: its own shape in ink inside a white die-cut border,
        /// so the outline still gives the shape away where the lens blurs it.
        private static func makeDecal(_ color: VanColor) -> UIImage {
            image(width: 128, height: 128, opaque: false) { g in
                let symbol = color.dioramaSymbolPath(centre: CGPoint(x: 64, y: 66), radius: 46)
                g.addPath(symbol)
                g.setLineJoin(.round)
                g.setLineWidth(20)
                g.setStrokeColor(UIColor.white.cgColor)
                g.strokePath()
                g.addPath(symbol)
                g.setFillColor(color.dioramaInk.cgColor)
                g.fillPath()
            }
        }

        private static func makeHouseFront(_ color: VanColor) -> UIImage {
            image(width: 320, height: 240, opaque: true) { g in
                fill(g, 0xFBF3E3, CGRect(x: 0, y: 0, width: 320, height: 240))
                siding(g, width: 320, height: 240)
                for x in [40.0, 222] {
                    window(g, x: x, y: 70, glass: 0x9FD0EA, mullions: true)
                    g.setFillColor(color.dioramaBody.cgColor)
                    g.fill(CGRect(x: x - 6, y: 140, width: 72, height: 12))
                }
                g.setFillColor(color.dioramaDeep.cgColor)
                g.addPath(CGPath(roundedRect: CGRect(x: 126, y: 112, width: 68, height: 128), cornerWidth: 30, cornerHeight: 30, transform: nil))
                g.fillPath()
                g.setFillColor(UIColor(white: 1, alpha: 0.18).cgColor)
                g.addPath(CGPath(roundedRect: CGRect(x: 136, y: 124, width: 48, height: 50), cornerWidth: 20, cornerHeight: 20, transform: nil))
                g.fillPath()
                disc(g, CGPoint(x: 182, y: 182), 6, 0xFFD867)
                // The plaque over the door: the colour's symbol in white on its ink.
                disc(g, CGPoint(x: 160, y: 54), 42, 0xFFFFFF)
                g.setFillColor(color.dioramaInk.cgColor)
                g.fillEllipse(in: CGRect(x: 160 - 36, y: 54 - 36, width: 72, height: 72))
                g.setFillColor(UIColor.white.cgColor)
                g.addPath(color.dioramaSymbolPath(centre: CGPoint(x: 160, y: 57), radius: 21))
                g.fillPath()
                MultiVanDioramaLawn.addGrain(g, alpha: 0.08)
            }
        }

        private static func siding(_ g: CGContext, width: CGFloat, height: CGFloat) {
            g.setFillColor(UIColor(red: 120 / 255, green: 90 / 255, blue: 60 / 255, alpha: 0.08).cgColor)
            for y in stride(from: 16, to: height, by: 22) {
                g.fill(CGRect(x: 0, y: y, width: width, height: 3))
            }
        }

        private static func window(_ g: CGContext, x: CGFloat, y: CGFloat, glass: Int, mullions: Bool) {
            g.setFillColor(UIColor.white.cgColor)
            g.addPath(CGPath(roundedRect: CGRect(x: x, y: y, width: 60, height: 64), cornerWidth: 8, cornerHeight: 8, transform: nil))
            g.fillPath()
            g.setFillColor(UIColor(dioramaHex: glass).cgColor)
            g.addPath(CGPath(roundedRect: CGRect(x: x + 7, y: y + 7, width: 46, height: 50), cornerWidth: 5, cornerHeight: 5, transform: nil))
            g.fillPath()
            guard mullions else { return }
            g.setFillColor(UIColor.white.cgColor)
            g.fill(CGRect(x: x + 28, y: y + 7, width: 4, height: 50))
            g.fill(CGRect(x: x + 7, y: y + 30, width: 46, height: 4))
        }

        private static func fill(_ g: CGContext, _ hex: Int, _ rect: CGRect) {
            g.setFillColor(UIColor(dioramaHex: hex).cgColor)
            g.fill(rect)
        }

        private static func disc(_ g: CGContext, _ centre: CGPoint, _ radius: CGFloat, _ hex: Int) {
            g.setFillColor(UIColor(dioramaHex: hex).cgColor)
            g.fillEllipse(in: CGRect(x: centre.x - radius, y: centre.y - radius, width: radius * 2, height: radius * 2))
        }

        private static func image(width: CGFloat, height: CGFloat, opaque: Bool, draw: (CGContext) -> Void) -> UIImage {
            UIGraphicsImageRenderer(size: CGSize(width: width, height: height), format: MultiVanDioramaLawn.textureFormat(opaque: opaque))
                .image { draw($0.cgContext) }
        }
    }
}

// MARK: - Colours

extension VanColor {
    var dioramaBody: UIColor {
        switch self {
        case .red: UIColor(dioramaHex: 0xEC5B4B)
        case .blue: UIColor(dioramaHex: 0x4A86E8)
        case .yellow: UIColor(dioramaHex: 0xF6C234)
        case .green: UIColor(dioramaHex: 0x4CB862)
        }
    }

    var dioramaDeep: UIColor {
        switch self {
        case .red: UIColor(dioramaHex: 0xB8392C)
        case .blue: UIColor(dioramaHex: 0x2C5DB5)
        case .yellow: UIColor(dioramaHex: 0xC8921A)
        case .green: UIColor(dioramaHex: 0x2F8742)
        }
    }

    /// What the symbol is printed in. The deep tone, except yellow's, which is too
    /// light to read against white in grayscale; yellow prints in a darker ochre.
    var dioramaInk: UIColor {
        self == .yellow ? UIColor(dioramaHex: 0x8F6208) : dioramaDeep
    }

    /// The colour's shape centred on `c`, as the HTML prototype draws it, y down.
    func dioramaSymbolPath(centre c: CGPoint, radius r: CGFloat) -> CGPath {
        switch self {
        case .red:
            return CGPath(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: r * 2, height: r * 2), transform: nil)
        case .yellow:
            let side = r * 1.65
            return CGPath(
                roundedRect: CGRect(x: c.x - side / 2, y: c.y - side / 2, width: side, height: side),
                cornerWidth: r * 0.18, cornerHeight: r * 0.18, transform: nil
            )
        case .blue:
            let path = CGMutablePath()
            path.addLines(between: [
                CGPoint(x: c.x, y: c.y - r * 1.05), CGPoint(x: c.x + r * 1.08, y: c.y + r * 0.8), CGPoint(x: c.x - r * 1.08, y: c.y + r * 0.8),
            ])
            path.closeSubpath()
            return path
        case .green:
            let path = CGMutablePath()
            path.addLines(between: (0..<10).map { index in
                let angle = -CGFloat.pi / 2 + CGFloat(index) * .pi / 5
                let length = index.isMultiple(of: 2) ? r * 1.1 : r * 0.48
                return CGPoint(x: c.x + cos(angle) * length, y: c.y + sin(angle) * length)
            })
            path.closeSubpath()
            return path
        }
    }
}

private extension SCNNode {
    convenience init(geometry: SCNGeometry, y: Double) {
        self.init(geometry: geometry)
        simdPosition.y = Float(y)
    }
}
