import SceneKit
import UIKit

/// The diorama's little effects: a parcel toss, a house squash, paper confetti,
/// cotton-wool puffs, chimney smoke, a camera shake and the failure ring. Timings
/// and sizes come from the HTML prototype. Everything runs as `SCNAction`s or a
/// keyframe animation inside SceneKit, with no per-frame Swift, and every burst
/// removes itself when it ends. `MultiVanDioramaScene` decides when each plays.
@MainActor
enum MultiVanDioramaEffects {
    enum Key {
        static let squash = "squash"
        static let shake = "shake"
        static let hop = "hop"
        static let pulse = "pulse"
        static let smoke = "smoke"
    }

    /// Each burst's node name, so a burst can be found while it plays.
    enum Name {
        static let parcel = "parcel"
        static let confetti = "confetti"
        static let puff = "puff"
    }

    enum Timing {
        /// The parcel's flight from the van's roof to the door.
        static let toss = 0.5
        /// The prototype's `bounce` runs from 1 to 0 at 2.4 a second.
        static let squash = 1 / 2.4
        static let puff = 0.9
        static let confetti = 3.2
        /// The win's shower waits for the last parcel to land.
        static let winConfettiDelay = 0.45
        static let smokeLife = 3.0
        static let smokeInterval = 1.3
        /// A rejected tap shakes the dial for as long as the prototype's.
        static let rejection = 1 / 3.0
    }

    // MARK: - Delivery

    /// A brown-paper parcel thrown in an arc from `start` to `end`, tumbling as it
    /// goes, gone as it lands.
    static func parcel(from start: SIMD3<Float>, to end: SIMD3<Float>) -> SCNNode {
        let node = SCNNode(geometry: parcelGeometry)
        node.name = Name.parcel
        node.simdPosition = start
        let travel = end - start
        // The prototype lifts a straight lerp by sin(πk) × 0.45, so the top of the
        // arc sits 0.45 over the midpoint.
        let rise = travel.y / 2 + 0.45
        let up = SCNAction.moveBy(x: 0, y: CGFloat(rise), z: 0, duration: Timing.toss / 2)
        up.timingMode = .easeOut
        let down = SCNAction.moveBy(x: 0, y: CGFloat(travel.y - rise), z: 0, duration: Timing.toss / 2)
        down.timingMode = .easeIn
        node.runAction(.sequence([
            .group([
                .moveBy(x: CGFloat(travel.x), y: 0, z: CGFloat(travel.z), duration: Timing.toss),
                .sequence([up, down]),
                .rotateBy(x: 2, y: 4, z: 0, duration: Timing.toss),
            ]),
            .removeFromParentNode(),
        ]))
        return node
    }

    private static let parcelGeometry: SCNGeometry = {
        let box = SCNBox(width: 0.1, height: 0.08, length: 0.1, chamferRadius: 0.004)
        let kraft = MultiVanDioramaScene.paper(
            texture: MultiVanDioramaScene.grain(on: UIColor(dioramaHex: 0xC99A63), dots: 2600, seed: 23)
        )
        // SCNBox order: front, right, back, left, top, bottom. The tape is on top.
        let tape = MultiVanDioramaScene.paper(color: UIColor(dioramaHex: 0xE9D9B5))
        box.materials = [kraft, kraft, kraft, kraft, tape, kraft]
        return box
    }()

    /// A house's body squashing as the parcel lands, `delay` seconds from now:
    /// the prototype's bounce, wider and lower, then a little stretch up.
    static func squash(delay: Double) -> CAAnimation {
        let samples = 14
        var values = [NSValue(scnVector3: SCNVector3(1, 1, 1))]
        var times = [0.0]
        for index in 0...samples {
            let bounce = 1 - Double(index) / Double(samples)
            let b = sin(bounce * .pi)
            let wide = 1 + b * 0.08
            let tall = 1 - b * 0.12 + max(0, sin(bounce * 2 * .pi)) * 0.06
            values.append(NSValue(scnVector3: SCNVector3(wide, tall, wide)))
            times.append(delay + Double(index) / Double(samples) * Timing.squash)
        }
        let total = delay + Timing.squash
        let animation = CAKeyframeAnimation(keyPath: "scale")
        animation.values = values
        animation.keyTimes = times.map { NSNumber(value: $0 / total) }
        animation.duration = total
        return animation
    }

    // MARK: - Confetti

    /// Paper confetti thrown up from `origin`, tumbling down to lie flat on the
    /// lawn. Seeded, so a burst looks the same each time it plays.
    static func confetti(
        at origin: SIMD3<Float>, colors: [UIColor], count: Int, spread: Double, delay: Double = 0, seed: UInt32
    ) -> SCNNode {
        var random = MultiVanDioramaRandom(seed: seed)
        let burst = SCNNode()
        burst.name = Name.confetti
        burst.simdPosition = origin
        for index in 0..<count {
            let velocity = SIMD3(
                (random.next() - 0.5) * 2.2 * spread, 1.6 + random.next() * 1.8, (random.next() - 0.5) * 2.2 * spread
            )
            let spin = SIMD3(random.next() * 12, random.next() * 12, random.next() * 12)
            let start = SIMD3(random.next() * 6, random.next() * 6, random.next() * 6)
            let restingTurn = random.next() * 6
            let flight = ConfettiFlight(height: Double(origin.y), velocity: velocity)

            let piece = SCNNode(geometry: confettiGeometry(colors[index % colors.count]))
            piece.simdEulerAngles = SIMD3<Float>(start)
            piece.isHidden = delay > 0
            let across = SCNAction.moveBy(x: CGFloat(flight.landing.x), y: 0, z: CGFloat(flight.landing.y), duration: flight.landingTime)
            // Drag slows the paper sideways as it goes.
            across.timingMode = .easeOut
            let up = SCNAction.moveBy(x: 0, y: CGFloat(flight.apex), z: 0, duration: flight.apexTime)
            up.timingMode = .easeOut
            let down = SCNAction.moveBy(
                x: 0, y: CGFloat(ConfettiFlight.floor - Double(origin.y) - flight.apex), z: 0,
                duration: flight.landingTime - flight.apexTime
            )
            down.timingMode = .easeIn
            piece.runAction(.sequence([
                .wait(duration: delay),
                .unhide(),
                .group([
                    across, .sequence([up, down]),
                    .rotateBy(x: CGFloat(spin.x * flight.landingTime), y: CGFloat(spin.y * flight.landingTime), z: 0, duration: flight.landingTime),
                ]),
                // Down on the lawn, face up.
                .rotateTo(x: -.pi / 2, y: 0, z: CGFloat(restingTurn), duration: 0),
                .wait(duration: max(0, Timing.confetti - flight.landingTime - 0.25)),
                .fadeOut(duration: 0.25),
            ]))
            burst.addChildNode(piece)
        }
        burst.runAction(.sequence([.wait(duration: delay + Timing.confetti), .removeFromParentNode()]))
        return burst
    }

    /// One piece's fall under the prototype's gravity and drag, worked out ahead so
    /// SceneKit can play it as eased moves.
    struct ConfettiFlight {
        /// Pieces come to rest a hair above the lawn.
        static let floor = 0.012
        static let gravity = 6.5
        static let drag = 1.6

        /// Height gained to the top of the arc, and when.
        let apex: Double
        let apexTime: Double
        /// Grid-plane travel by landing: x, then z.
        let landing: SIMD2<Double>
        let landingTime: Double

        init(height: Double, velocity: SIMD3<Double>) {
            // The prototype's own step, at its frame rate.
            let step = 1.0 / 60
            var position = SIMD3(0, height, 0)
            var velocity = velocity
            var time = 0.0, top = height, topTime = 0.0
            while position.y > Self.floor, time < Timing.confetti {
                velocity.y -= Self.gravity * step
                velocity *= 1 - Self.drag * step
                position += velocity * step
                time += step
                if position.y > top { (top, topTime) = (position.y, time) }
            }
            apex = top - height
            apexTime = max(topTime, step)
            landing = SIMD2(position.x, position.z)
            landingTime = max(time, apexTime + step)
        }
    }

    private static func confettiGeometry(_ color: UIColor) -> SCNGeometry {
        if let geometry = confettiPieces[color] { return geometry }
        let plane = SCNPlane(width: 0.05, height: 0.032)
        let material = MultiVanDioramaScene.paper(color: color, roughness: 0.8)
        material.isDoubleSided = true
        plane.materials = [material]
        confettiPieces[color] = plane
        return plane
    }

    private static var confettiPieces: [UIColor: SCNGeometry] = [:]

    static let gold = UIColor(dioramaHex: 0xFFD75E)

    // MARK: - Warming up

    /// A node for each burst piece's geometry: the parcel, every confetti colour,
    /// cotton wool and the failure ring. `SCNView.prepare` compiles and uploads
    /// them before play; otherwise the first delivery builds them mid-run and the
    /// frame stalls.
    static func warmUpNodes() -> [SCNNode] {
        let confetti = (VanColor.allCases.map(\.dioramaBody) + [.white, gold]).map(confettiGeometry)
        return ([parcelGeometry, cottonWool, ringGeometry] + confetti).map { SCNNode(geometry: $0) }
    }

    // MARK: - Puffs and smoke

    /// Cotton-wool balls bursting out from `origin`, swelling and fading.
    static func puff(at origin: SIMD3<Float>, size: Double, count: Int, opacity: Double, seed: UInt32) -> SCNNode {
        var random = MultiVanDioramaRandom(seed: seed)
        let burst = SCNNode()
        burst.name = Name.puff
        burst.simdPosition = origin
        for index in 0..<count {
            let angle = Double(index) * 2.4
            // The prototype eases its speed out over the puff, so it covers half
            // the distance it would at full speed.
            let travel = SIMD3(cos(angle), 0.6 + random.next() * 0.5, sin(angle)) * 0.35 * size * Timing.puff / 2
            let ball = SCNNode(geometry: cottonWool)
            ball.castsShadow = false
            ball.simdScale = SIMD3(repeating: Float(0.04 * size))
            ball.opacity = CGFloat(opacity)
            let move = SCNAction.moveBy(x: CGFloat(travel.x), y: CGFloat(travel.y), z: CGFloat(travel.z), duration: Timing.puff)
            move.timingMode = .easeOut
            let swell = SCNAction.scale(to: CGFloat(0.15 * size), duration: Timing.puff)
            swell.timingMode = .easeOut
            ball.runAction(.group([move, swell, .fadeOut(duration: Timing.puff)]))
            burst.addChildNode(ball)
        }
        burst.runAction(.sequence([.wait(duration: Timing.puff), .removeFromParentNode()]))
        return burst
    }

    /// A chimney's smoke: puffs leave `top` every 1.3 s, drift up and away with the
    /// breeze and thin out. Three puffs take turns, so the column never ends.
    static func smoke(at top: SIMD3<Float>, seed: UInt32) -> SCNNode {
        var random = MultiVanDioramaRandom(seed: seed)
        let column = SCNNode()
        let puffs = Int((Timing.smokeLife / Timing.smokeInterval).rounded(.up))
        let period = Double(puffs) * Timing.smokeInterval
        // Houses don't puff in step.
        let start = random.next() * 2
        for index in 0..<puffs {
            let ball = SCNNode(geometry: cottonWool)
            ball.castsShadow = false
            ball.simdPosition = top
            ball.simdScale = SIMD3(repeating: 0.03)
            ball.opacity = 0
            let drift = (random.next() - 0.3) * 0.12 * Timing.smokeLife
            let rise = SCNAction.group([
                .moveBy(x: CGFloat(drift), y: CGFloat(0.16 * Timing.smokeLife), z: 0, duration: Timing.smokeLife),
                .scale(to: 0.1, duration: Timing.smokeLife),
                .fadeOut(duration: Timing.smokeLife),
            ])
            let reset = SCNAction.group([
                .move(to: SCNVector3(top), duration: 0), .scale(to: 0.03, duration: 0), .fadeOpacity(to: 0.75, duration: 0),
            ])
            ball.runAction(.sequence([
                .wait(duration: start + Double(index) * Timing.smokeInterval),
                .repeatForever(.sequence([reset, rise, .wait(duration: period - Timing.smokeLife)])),
            ]), forKey: Key.smoke)
            column.addChildNode(ball)
        }
        return column
    }

    private static let cottonWool: SCNGeometry = {
        let sphere = SCNSphere(radius: 1)
        sphere.isGeodesic = true
        sphere.segmentCount = 4
        let material = MultiVanDioramaScene.paper(color: .white, roughness: 1)
        sphere.materials = [material]
        return sphere
    }()

    // MARK: - Shakes, hops and pulses

    /// The flat board's shake (`MultiVanCrashEffects.shakeOffset`) along `axis`,
    /// through each of its turning points, peaking at `peak`. Ends where it began.
    static func shake(along axis: SIMD3<Float>, peak: Double, duration: Double) -> SCNAction {
        var offset = 0.0, progress = 0.0
        return .sequence(shakeTurns(peak: peak).map { turn in
            let step = SCNAction.move(by: SCNVector3(axis * Float(turn.offset - offset)), duration: (turn.progress - progress) * duration)
            step.timingMode = .easeInEaseOut
            (offset, progress) = (turn.offset, turn.progress)
            return step
        })
    }

    /// Where the shake turns back, as a share of its time, and the last at rest.
    static func shakeTurns(peak: Double) -> [(progress: Double, offset: Double)] {
        ([1.0, 3, 5, 7, 9, 11].map { $0 / 12 } + [1]).map { progress in
            // The flat board's curve peaks at 4 points.
            (progress, MultiVanCrashEffects.shakeOffset(progress: progress) / 4 * peak)
        }
    }

    /// A van's little hop of pride as it arrives home.
    static func hop() -> SCNAction {
        let up = SCNAction.moveBy(x: 0, y: 0.09, z: 0, duration: 0.12)
        up.timingMode = .easeOut
        let down = SCNAction.moveBy(x: 0, y: -0.09, z: 0, duration: 0.18)
        down.timingMode = .easeIn
        return .sequence([up, down])
    }

    /// A live dial breathing while the vans drive, as the flat board's ring does.
    static func pulse(scale: Float) -> SCNAction {
        let swell = SCNAction.scale(to: CGFloat(scale * 1.06), duration: 0.45)
        swell.timingMode = .easeInEaseOut
        let settle = SCNAction.scale(to: CGFloat(scale), duration: 0.45)
        settle.timingMode = .easeInEaseOut
        return .repeatForever(.sequence([swell, settle]))
    }

    // MARK: - Failure ring

    /// A red ring on the road where the last run went wrong, pulsing like the flat
    /// board's unless motion is reduced.
    static func failureRing(animates: Bool) -> SCNNode {
        let node = SCNNode(geometry: ringGeometry)
        node.simdPosition.y = 0.02
        node.castsShadow = false
        guard animates else {
            node.opacity = 0.55
            return node
        }
        node.opacity = 0.72
        let out = SCNAction.group([.scale(to: 1.28, duration: 0.5), .fadeOpacity(to: 0.28, duration: 0.5)])
        out.timingMode = .easeInEaseOut
        let back = SCNAction.group([.scale(to: 1, duration: 0.5), .fadeOpacity(to: 0.72, duration: 0.5)])
        back.timingMode = .easeInEaseOut
        node.runAction(.repeatForever(.sequence([out, back])), forKey: Key.pulse)
        return node
    }

    private static let ringGeometry: SCNGeometry = {
        // Lies flat on the lawn, about the flat board's 30 pt across.
        let torus = SCNTorus(ringRadius: 0.24, pipeRadius: 0.018)
        torus.ringSegmentCount = 48
        torus.pipeSegmentCount = 8
        let material = SCNMaterial()
        // Unlit, like the badges, so it reads in the sun and in shade.
        material.lightingModel = .constant
        material.diffuse.contents = UIColor(dioramaHex: 0xE5483B)
        torus.materials = [material]
        return torus
    }()
}
