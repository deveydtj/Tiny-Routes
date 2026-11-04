import SceneKit
import UIKit

/// The diorama's SceneKit scene: a floating slab of lawn under a warm sun, seen
/// through a long lens with shallow focus. Built once per board; `load` swaps the
/// level's pieces and `setCamera` follows the board's framing and orbit. Only this
/// file and `MultiVanDioramaSceneView` know about SceneKit.
@MainActor
final class MultiVanDioramaScene {
    /// Tuned in the iOS 18.5 simulator against the HTML prototype; check on a device.
    enum Look {
        /// Shallow enough to blur the table's far rim, open enough that row 0 and
        /// row 6 stay readable on level 12, for a board framed in `referenceSize`.
        static let fStop = 0.012
        static let referenceSize = CGSize(width: 360, height: 460)
        static let saturation: CGFloat = 1.12
        static let vignetting: CGFloat = 0.2
        static let sunIntensity: CGFloat = 1500
        static let skyIntensity: CGFloat = 0.5
        /// Badges float above the roof of a house, or above the lawn elsewhere.
        static let houseBadgeHeight = 0.95
        static let badgeHeight = 0.5
        /// Badges sharing an end stack in columns across the lens and rows upwards.
        static let badgeColumn = 0.16
        static let badgeRow = 0.3
    }

    let scene = SCNScene()
    /// The lens. Its rig holds the board's framing and orbit, so a crash can shake
    /// the lens without moving where the switch buttons think it is.
    let cameraNode = SCNNode()
    private let cameraRig = SCNNode()
    private let piecesNode = SCNNode()
    /// The slab's top face; each level paints its own roads onto it.
    let lawn: SCNMaterial
    private(set) var camera = MultiVanDioramaCamera()
    private(set) var levelID: String?
    /// The level's pieces by house node, van, switch node and barrier node. Sync
    /// and feedback find their pieces here.
    private(set) var houses: [String: SCNNode] = [:]
    private(set) var vans: [String: SCNNode] = [:]
    private(set) var dials: [String: SCNNode] = [:]
    private(set) var roadblocks: [String: SCNNode] = [:]
    /// Each house's ✓, shown once its van is home.
    private(set) var deliveredBadges: [String: SCNNode] = [:]
    /// The level's scenery, and a node for each standing piece of it in its order.
    private(set) var scenery: MultiVanDioramaScenery?
    private(set) var sceneryNodes: [SCNNode] = []
    private(set) var pondNode: SCNNode?
    /// Trees' and residents' cards, with where each starts its sway.
    private var swayingCards: [(card: SCNNode, phase: Double)] = []
    /// Whether they sway; nil until the first sync.
    private var sceneryAnimates: Bool?
    /// Preview lines, one per van in authored order, rebuilt when the routes change.
    private(set) var trails: [MultiVanDioramaTrail] = []
    private(set) var trailNodes: [SCNNode] = []
    private(set) var markerNodes: [SCNNode?] = []
    private var level: MultiVanLevel?
    private var routes: [MultiVanPreviewRoute]?
    private var firstVisibleDots: [Int?] = []
    /// The yaw each dial's arrow is turning to, unwrapped so turns take the short way.
    private var dialYaws: [String: Float] = [:]
    private var dialTints: [String: MultiVanSwitchDialView.Tint] = [:]
    private var vanLooks: [String: VanLook] = [:]
    private let trailsNode = SCNNode()
    /// Bursts in flight: parcels, confetti and puffs. Each removes itself.
    let effectsNode = SCNNode()
    /// Each house's chimney smoke, there only while motion is on.
    private(set) var smokeColumns: [String: SCNNode] = [:]
    private var chimneyTops: [String: SIMD3<Float>] = [:]
    private(set) var failureRing: SCNNode?
    private var failPoint: RoadPoint?
    /// Where each dial stands, for a shake to return to.
    private var dialHomes: [String: SIMD3<Float>] = [:]
    private var dialPulses: [String: Bool] = [:]
    /// The tokens the last cues held; nil until a board's first cues.
    private var playedCues: Set<UUID>?
    /// Seeds each burst, so bursts differ but a run plays the same every time.
    private var burstCount: UInt32 = 0
    /// Clouds drifting in the sky around and below the slab.
    private(set) var clouds: [SCNNode] = []

    init() {
        lawn = Self.lawnMaterial()
        scene.background.contents = Self.backdrop()
        scene.lightingEnvironment.contents = Self.skyGround()
        scene.lightingEnvironment.intensity = Look.skyIntensity
        scene.rootNode.addChildNode(Self.sun())
        scene.rootNode.addChildNode(Self.slab(lawn: lawn))
        scene.rootNode.addChildNode(Self.floorShadow())
        clouds = Self.clouds()
        clouds.forEach(scene.rootNode.addChildNode)
        scene.rootNode.addChildNode(piecesNode)
        scene.rootNode.addChildNode(trailsNode)
        scene.rootNode.addChildNode(effectsNode)
        cameraNode.camera = Self.lens()
        cameraRig.addChildNode(cameraNode)
        scene.rootNode.addChildNode(cameraRig)
        applyCamera()
    }

    /// Rebuilds the level's lawn and pieces when the level changes; a retry keeps
    /// them. `graph` is the engine's, so dials start on its active exits.
    func load(_ level: MultiVanLevel, graph: RuntimeRouteGraph) {
        guard level.id != levelID else { return }
        levelID = level.id
        self.level = level
        let scenery = MultiVanDioramaScenery(level: level, graph: graph)
        self.scenery = scenery
        lawn.diffuse.contents = MultiVanDioramaLawn.image(for: level, graph: graph, scenery: scenery)
        piecesNode.childNodes.forEach { $0.removeFromParentNode() }
        houses = [:]
        vans = [:]
        dials = [:]
        roadblocks = [:]
        deliveredBadges = [:]
        dialYaws = [:]
        dialTints = [:]
        vanLooks = [:]
        dialHomes = [:]
        dialPulses = [:]
        smokeColumns = [:]
        chimneyTops = [:]
        failureRing = nil
        failPoint = nil
        effectsNode.childNodes.forEach { $0.removeFromParentNode() }
        placePieces(level, graph: graph)
        placeScenery(scenery)
        setTrails([], routes: nil)
    }

    /// Cutouts turn to the lens at its resting angle, each a little off square so a
    /// grove doesn't read as a row of cards.
    private func placeScenery(_ scenery: MultiVanDioramaScenery) {
        sceneryNodes = []
        swayingCards = []
        sceneryAnimates = nil
        for item in scenery.items {
            guard let node = MultiVanDioramaPieces.scenery(item.kind, height: item.height) else { continue }
            let x = item.point.x, y = item.point.y
            let turn: Double, phase: Double?
            switch item.kind {
            case .tree: (turn, phase) = (sin(x * 12.9 + y * 78.2) * 0.35, x * 3 + y)
            case .bush: (turn, phase) = (sin(x * 4.1) * 0.3, nil)
            case .resident: (turn, phase) = (0, x * 5)
            case .flowers: continue
            }
            if let phase, let card = node.childNode(withName: MultiVanDioramaPieces.Part.sway, recursively: false) {
                swayingCards.append((card, phase))
            }
            node.simdPosition = SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: x, gridY: y))
            node.simdEulerAngles.y = Float(MultiVanDioramaCamera.restingYaw + turn)
            piecesNode.addChildNode(node)
            sceneryNodes.append(node)
        }
        pondNode = scenery.pond.map { pond in
            let node = MultiVanDioramaPieces.pond(pond)
            let centre = MultiVanDioramaGeometry.world(gridX: pond.centre.x, gridY: pond.centre.y)
            node.simdPosition.x = Float(centre.x)
            node.simdPosition.z = Float(centre.z)
            piecesNode.addChildNode(node)
            return node
        }
    }

    /// Each piece stands on the mark the lawn paints for it.
    private func placePieces(_ level: MultiVanLevel, graph: RuntimeRouteGraph) {
        let features = MultiVanDioramaLawn.Features(level: level, graph: graph)
        let place = { (node: SCNNode, point: RoadPoint, yaw: Double) in
            node.simdPosition = SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: point.x, gridY: point.y))
            node.simdEulerAngles.y = Float(yaw)
            self.piecesNode.addChildNode(node)
        }
        for house in features.houses {
            let node = MultiVanDioramaPieces.house(house.color)
            // The front faces back down the road that arrives at the door.
            let heading = house.marking.heading
            place(node, house.centre, MultiVanDioramaGeometry.yaw(facing: RoadVector(x: -heading.x, y: -heading.y)))
            houses[house.marking.nodeID] = node
            if let chimney = node.childNode(withName: MultiVanDioramaPieces.Part.chimney, recursively: true) {
                chimneyTops[house.marking.nodeID] = chimney.simdConvertPosition(SIMD3(0, Float(MultiVanDioramaPieces.Measure.chimneyHeight / 2), 0), to: nil)
            }
            // Over the roof, where the preview's ✓ stood before the van arrived.
            let badge = MultiVanDioramaPieces.badge(.delivered)
            badge.simdPosition = node.simdPosition + SIMD3(0, Float(Look.houseBadgeHeight), 0)
            badge.isHidden = true
            piecesNode.addChildNode(badge)
            deliveredBadges[house.marking.nodeID] = badge
        }
        let depots = Dictionary(uniqueKeysWithValues: features.depots.map { ($0.nodeID, $0) })
        for van in level.vans {
            guard let depot = depots[van.startNodeID] else { continue }
            let node = MultiVanDioramaPieces.van(van.color)
            place(node, depot.point, MultiVanDioramaGeometry.yaw(facing: depot.heading))
            vans[van.id] = node
        }
        for node in MultiVanBoardRules.switchNodes(in: graph) {
            let exits = node.outgoingEdgeIDs.compactMap { graph.edgesByID[$0] }
            guard let active = node.activeOutgoingEdgeID.flatMap({ graph.edgesByID[$0] }) else { continue }
            let angle = { SwitchArrowDirectionResolver.directionAngle(for: $0, from: node, in: graph) }
            let dial = MultiVanDioramaPieces.dial(
                optionAngles: exits.map(angle), activeAngle: angle(active),
                tint: level.liveSwitchNodeIDs.contains(node.id) ? .live : .ready
            )
            place(dial, RoadPoint(x: node.x, y: node.y), 0)
            dials[node.id] = dial
            dialHomes[node.id] = dial.simdPosition
            dialYaws[node.id] = MultiVanDioramaPieces.arrowYaw(activeAngle: angle(active))
        }
        for barrier in features.barriers {
            let roadYaw = MultiVanDioramaGeometry.yaw(facing: barrier.heading)
            let node = MultiVanDioramaPieces.roadblock(roadYaw: roadYaw)
            let point = MultiVanDioramaGeometry.offset(barrier.point, along: barrier.heading, by: MultiVanDioramaGeometry.roadblockSetback)
            place(node, point, roadYaw)
            roadblocks[barrier.nodeID] = node
        }
    }

    // MARK: - Sync

    /// Puts every piece where the engine has it this frame. Called from SwiftUI's
    /// update on the main actor; SceneKit only animates what this sets.
    func sync(_ frame: MultiVanDioramaFrame) {
        guard let level else { return }
        if frame.animates != sceneryAnimates {
            sceneryAnimates = frame.animates
            setSway(frame.animates)
            setDrift(frame.animates)
            setSmoke(frame.animates)
            if !frame.animates { stopEffects() }
            // The ring's pulse follows the setting too.
            setFailureRing(at: frame.failPoint, animates: frame.animates)
        }
        if frame.failPoint != failPoint {
            setFailureRing(at: frame.failPoint, animates: frame.animates)
        }
        if frame.routes != routes {
            setTrails(MultiVanDioramaTrail.make(routes: frame.routes, vans: level.vans, graph: frame.graph), routes: frame.routes)
        }
        for (index, van) in frame.vans.enumerated() {
            if let node = vans[van.id] { syncVan(node, van, index: index, animates: frame.animates) }
        }
        for dial in frame.dials {
            if let node = dials[dial.nodeID] { syncDial(node, dial, animates: frame.animates) }
        }
        for (nodeID, badge) in deliveredBadges {
            badge.isHidden = !frame.deliveredHouseNodeIDs.contains(nodeID)
        }
        for (index, trail) in trails.enumerated() {
            let first = trail.firstVisibleDot(for: index < frame.vans.count ? frame.vans[index] : nil)
            guard first != firstVisibleDots[index] else { continue }
            firstVisibleDots[index] = first
            for (dotIndex, dot) in trailNodes[index].childNodes.enumerated() {
                dot.isHidden = first.map { dotIndex < $0 } ?? true
            }
            markerNodes[index]?.isHidden = first == nil
        }
    }

    /// What a van shows beyond its place on the road; changes only on a status or signal change.
    private struct VanLook: Equatable {
        var status: MultiVanVanState.Status
        var idles: Bool
        var signal: MultiVanDioramaFrame.Van.Signal?
        var signalIsLit: Bool
    }

    private static let rumbleKey = "rumble"
    private static let poseKey = "pose"

    private func syncVan(_ node: SCNNode, _ van: MultiVanDioramaFrame.Van, index: Int, animates: Bool) {
        node.simdPosition = SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: van.point.x, gridY: van.point.y))
        let length = hypot(van.heading.x, van.heading.y)
        if length.isFinite, length > 1e-9 {
            node.simdEulerAngles.y = Float(MultiVanDioramaGeometry.yaw(facing: van.heading))
        }
        guard let pose = node.childNode(withName: MultiVanDioramaPieces.Part.pose, recursively: false),
              let chassis = pose.childNode(withName: MultiVanDioramaPieces.Part.chassis, recursively: false) else { return }
        if van.status == .driving, animates {
            // A light bounce over the road surface, tied to the distance driven.
            chassis.simdPosition.y = Float(abs(sin(van.distanceAlongEdge * 30)) * 0.006)
        }

        let look = VanLook(status: van.status, idles: van.idles, signal: van.signal, signalIsLit: van.signalIsLit)
        let previous = vanLooks[van.id]
        guard look != previous else { return }
        vanLooks[van.id] = look

        let lamp = { (side: MultiVanDioramaFrame.Van.Signal) -> MultiVanDioramaPieces.Lamp in
            van.signal == side || van.signal == .hazard ? .signal(lit: van.signalIsLit) : .off
        }
        MultiVanDioramaPieces.setLamps(chassis, left: lamp(.left), right: lamp(.right))

        guard look.status != previous?.status || look.idles != previous?.idles else { return }
        chassis.removeAction(forKey: Self.rumbleKey)
        chassis.simdPosition.y = 0
        chassis.simdEulerAngles = SIMD3(van.status == .driving ? -0.02 : 0, 0, 0)
        if van.idles {
            chassis.runAction(Self.rumble(phase: index), forKey: Self.rumbleKey)
        }

        // Crashed vans skew off the road and tip; a van at a dead end skews a little.
        // Neighbours in authored order skew opposite ways, so a pair splays apart.
        let side: Float = index.isMultiple(of: 2) ? 1 : -1
        let target: SIMD3<Float>
        switch van.status {
        case .crashed: target = SIMD3(0, 0.6 * side, 0.3 * side)
        case .stuck: target = SIMD3(0, 0.25 * side, 0)
        case .waiting, .driving, .parked: target = .zero
        }
        pose.removeAction(forKey: Self.poseKey)
        if animates, van.status == .crashed {
            // The flat board spins a crashed van once round; this one spins as it skews.
            let spin = SCNAction.rotateTo(
                x: CGFloat(target.x), y: CGFloat(target.y + 2 * .pi * side), z: CGFloat(target.z), duration: 0.44, usesShortestUnitArc: false
            )
            spin.timingMode = .easeOut
            pose.runAction(spin, forKey: Self.poseKey)
        } else if animates, target != .zero {
            pose.runAction(
                .rotateTo(x: CGFloat(target.x), y: CGFloat(target.y), z: CGFloat(target.z), duration: 0.3, usesShortestUnitArc: true),
                forKey: Self.poseKey
            )
        } else {
            pose.simdEulerAngles = target
        }
    }

    /// The idle shiver of an engine ticking over, offset per van so they don't beat together.
    private static func rumble(phase: Int) -> SCNAction {
        let up = SCNAction.moveBy(x: 0, y: 0.003, z: 0, duration: 0.045)
        let down = SCNAction.moveBy(x: 0, y: -0.003, z: 0, duration: 0.045)
        let roll = SCNAction.sequence([.rotateBy(x: 0, y: 0, z: 0.012, duration: 0.7), .rotateBy(x: 0, y: 0, z: -0.024, duration: 1.4), .rotateBy(x: 0, y: 0, z: 0.012, duration: 0.7)])
        let shiver = SCNAction.repeatForever(.sequence([up, down]))
        return .sequence([.wait(duration: Double(phase) * 0.11), .group([shiver, .repeatForever(roll)])])
    }

    private static let swayKey = "sway"

    /// Trees and residents rock gently in the breeze; still under reduced motion.
    private func setSway(_ animates: Bool) {
        for (card, phase) in swayingCards {
            card.removeAction(forKey: Self.swayKey)
            guard animates else {
                card.simdEulerAngles.z = 0
                continue
            }
            let (start, action) = Self.sway(phase: phase)
            card.simdEulerAngles.z = start
            card.runAction(action, forKey: Self.swayKey)
        }
    }

    /// The prototype's `sin(1.3 t + phase) × 0.035` as eased swings between its
    /// extremes, entered at `phase`. Returns the starting angle and the action.
    private static func sway(phase: Double) -> (Float, SCNAction) {
        let amplitude = 0.035, swing = Double.pi / 1.3
        let start = amplitude * sin(phase)
        let target = cos(phase) >= 0 ? amplitude : -amplitude
        let swingTo = { (angle: Double, duration: Double, timing: SCNActionTimingMode) -> SCNAction in
            let action = SCNAction.rotateTo(x: 0, y: 0, z: CGFloat(angle), duration: duration, usesShortestUnitArc: false)
            action.timingMode = timing
            return action
        }
        let first = swingTo(target, swing * abs(target - start) / (2 * amplitude), .easeOut)
        let loop = SCNAction.repeatForever(.sequence([swingTo(-target, swing, .easeInEaseOut), swingTo(target, swing, .easeInEaseOut)]))
        return (Float(start), .sequence([first, loop]))
    }

    private func syncDial(_ node: SCNNode, _ dial: MultiVanDioramaFrame.Dial, animates: Bool) {
        if dialTints[dial.nodeID] != dial.tint {
            dialTints[dial.nodeID] = dial.tint
            MultiVanDioramaPieces.tintDial(node, dial.tint)
        }
        let pulses = dial.pulses && animates
        if dialPulses[dial.nodeID] != pulses {
            dialPulses[dial.nodeID] = pulses
            node.removeAction(forKey: MultiVanDioramaEffects.Key.pulse)
            node.simdScale = SIMD3(repeating: MultiVanDioramaPieces.Measure.dialScale)
            if pulses {
                node.runAction(MultiVanDioramaEffects.pulse(scale: MultiVanDioramaPieces.Measure.dialScale), forKey: MultiVanDioramaEffects.Key.pulse)
            }
        }
        guard let pivot = node.childNode(withName: MultiVanDioramaPieces.Part.pivot, recursively: false) else { return }
        let current = dialYaws[dial.nodeID] ?? pivot.simdEulerAngles.y
        // Yaw turns the other way from the flat board's clockwise screen angle.
        let delta = -Float(MultiVanSwitchDialView.shortestTurn(from: -Double(current), to: -Double(MultiVanDioramaPieces.arrowYaw(activeAngle: dial.activeAngle))))
        guard abs(delta) > 0.001 else { return }
        let target = current + delta
        dialYaws[dial.nodeID] = target
        pivot.removeAllActions()
        guard animates else {
            pivot.simdEulerAngles.y = target
            return
        }
        // As on the flat board: the arrow arrives fast, then springs in its notch.
        pivot.simdEulerAngles.y = current
        let duration = 0.1 + 0.06 * Double(abs(delta)) / (.pi / 2)
        let turn = SCNAction.rotateBy(x: 0, y: CGFloat(delta), z: 0, duration: duration)
        turn.timingMode = .easeIn
        let direction: CGFloat = delta < 0 ? -1 : 1
        let wobble = [11.0, -17, 9, -4, 1].map { degrees in
            SCNAction.rotateBy(x: 0, y: direction * CGFloat(degrees) * .pi / 180, z: 0, duration: 0.075)
        }
        pivot.runAction(.sequence([turn] + wobble))
    }

    // MARK: - Feedback

    /// Plays each cue the last call didn't hold. Called after `sync`, from the same
    /// SwiftUI update; with motion off it only notes the tokens, so turning motion
    /// back on never replays them.
    func play(_ cues: MultiVanDioramaCues, animates: Bool) {
        let tokens = cues.tokens
        defer { playedCues = tokens }
        guard animates, let played = playedCues else { return }
        let isNew = { (token: UUID) in !played.contains(token) }
        for delivery in cues.deliveries where isNew(delivery.token) {
            playDelivery(delivery)
        }
        for (vanID, token) in cues.departures where isNew(token) {
            guard let van = vans[vanID] else { continue }
            // Exhaust from the back of the van as it pulls away.
            let back = van.simdConvertPosition(SIMD3(0, 0.07, -0.23), to: nil)
            effectsNode.addChildNode(MultiVanDioramaEffects.puff(at: back, size: 0.6, count: 3, opacity: 0.8, seed: nextSeed()))
        }
        for (vanID, token) in cues.arrivals where isNew(token) {
            guard let pose = vans[vanID]?.childNode(withName: MultiVanDioramaPieces.Part.pose, recursively: false) else { continue }
            pose.removeAction(forKey: MultiVanDioramaEffects.Key.hop)
            pose.simdPosition = .zero
            pose.runAction(MultiVanDioramaEffects.hop(), forKey: MultiVanDioramaEffects.Key.hop)
        }
        for (nodeID, token) in cues.rejections where isNew(token) {
            guard let dial = dials[nodeID], let home = dialHomes[nodeID] else { continue }
            dial.removeAction(forKey: MultiVanDioramaEffects.Key.shake)
            dial.simdPosition = home
            let across = SIMD3<Float>(camera.basis.right)
            dial.runAction(
                MultiVanDioramaEffects.shake(along: across, peak: 0.03, duration: MultiVanDioramaEffects.Timing.rejection),
                forKey: MultiVanDioramaEffects.Key.shake
            )
        }
        if let impact = cues.impact, isNew(impact.token) {
            let point = SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: impact.point.x, gridY: impact.point.y, height: 0.15))
            effectsNode.addChildNode(MultiVanDioramaEffects.puff(at: point, size: 2.2, count: 10, opacity: 0.95, seed: nextSeed()))
            // Across the lens, as the flat board shakes sideways.
            cameraNode.removeAction(forKey: MultiVanDioramaEffects.Key.shake)
            cameraNode.simdPosition = .zero
            cameraNode.runAction(
                MultiVanDioramaEffects.shake(along: SIMD3(1, 0, 0), peak: 0.06, duration: MultiVanCrashEffects.shakeDuration),
                forKey: MultiVanDioramaEffects.Key.shake
            )
        }
        if let confetti = cues.confetti, isNew(confetti) {
            let colors = VanColor.allCases.map(\.dioramaBody) + [.white]
            effectsNode.addChildNode(MultiVanDioramaEffects.confetti(
                at: SIMD3(0, 1.4, 0), colors: colors, count: 90, spread: 2.2,
                delay: MultiVanDioramaEffects.Timing.winConfettiDelay, seed: nextSeed()
            ))
        }
    }

    /// The van tosses a parcel to the door; as it lands the house squashes and a
    /// little confetti pops.
    private func playDelivery(_ delivery: MultiVanDioramaCues.Delivery) {
        guard let house = houses[delivery.houseNodeID],
              let body = house.childNode(withName: MultiVanDioramaPieces.Part.houseBody, recursively: false) else { return }
        let door = house.simdConvertPosition(SIMD3(0, 0.08, Float(MultiVanDioramaPieces.Measure.houseDepth / 2 + 0.05)), to: nil)
        let start = delivery.vanID.flatMap { vans[$0] }.map { $0.simdWorldPosition + SIMD3(0, 0.3, 0) } ?? door + SIMD3(0, 0.3, 0)
        effectsNode.addChildNode(MultiVanDioramaEffects.parcel(from: start, to: door))
        body.removeAnimation(forKey: MultiVanDioramaEffects.Key.squash)
        body.addAnimation(MultiVanDioramaEffects.squash(delay: MultiVanDioramaEffects.Timing.toss), forKey: MultiVanDioramaEffects.Key.squash)
        effectsNode.addChildNode(MultiVanDioramaEffects.confetti(
            at: SIMD3(door.x, 0.45, door.z), colors: [delivery.color.dioramaBody, .white, MultiVanDioramaEffects.gold],
            count: 26, spread: 0.7, delay: MultiVanDioramaEffects.Timing.toss, seed: nextSeed()
        ))
    }

    private func nextSeed() -> UInt32 {
        burstCount &+= 1
        return burstCount &* 2_654_435_761
    }

    /// Motion turned off: everything in flight stops where it would come to rest.
    private func stopEffects() {
        effectsNode.childNodes.forEach { $0.removeFromParentNode() }
        for house in houses.values {
            house.childNode(withName: MultiVanDioramaPieces.Part.houseBody, recursively: false)?
                .removeAnimation(forKey: MultiVanDioramaEffects.Key.squash)
        }
        for van in vans.values {
            guard let pose = van.childNode(withName: MultiVanDioramaPieces.Part.pose, recursively: false) else { continue }
            pose.removeAction(forKey: MultiVanDioramaEffects.Key.hop)
            pose.simdPosition = .zero
        }
        for (nodeID, home) in dialHomes {
            dials[nodeID]?.removeAction(forKey: MultiVanDioramaEffects.Key.shake)
            dials[nodeID]?.simdPosition = home
        }
        cameraNode.removeAction(forKey: MultiVanDioramaEffects.Key.shake)
        cameraNode.simdPosition = .zero
    }

    /// Chimneys smoke only while motion is on.
    private func setSmoke(_ animates: Bool) {
        smokeColumns.values.forEach { $0.removeFromParentNode() }
        smokeColumns = [:]
        guard animates else { return }
        for (index, (nodeID, top)) in chimneyTops.sorted(by: { $0.key < $1.key }).enumerated() {
            let column = MultiVanDioramaEffects.smoke(at: top, seed: UInt32(index + 1) &* 7919)
            piecesNode.addChildNode(column)
            smokeColumns[nodeID] = column
        }
    }

    private func setFailureRing(at point: RoadPoint?, animates: Bool) {
        failPoint = point
        failureRing?.removeFromParentNode()
        failureRing = point.map { point in
            let ring = MultiVanDioramaEffects.failureRing(animates: animates)
            ring.simdPosition += SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: point.x, gridY: point.y))
            piecesNode.addChildNode(ring)
            return ring
        }
    }

    private func setTrails(_ trails: [MultiVanDioramaTrail], routes: [MultiVanPreviewRoute]?) {
        self.trails = trails
        self.routes = routes
        trailsNode.childNodes.forEach { $0.removeFromParentNode() }
        // Nothing is synced yet, so the first sync shows or hides every dot.
        firstVisibleDots = [Int?](repeating: -1, count: trails.count)
        let right = SIMD3<Float>(MultiVanDioramaCamera().basis.right)
        trailNodes = trails.map { trail in
            let node = SCNNode()
            for dot in trail.dots {
                let piece = MultiVanDioramaPieces.trailDot(trail.color)
                piece.simdPosition += SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: dot.point.x, gridY: dot.point.y))
                node.addChildNode(piece)
            }
            trailsNode.addChildNode(node)
            return node
        }
        markerNodes = trails.map { trail in
            guard let marker = trail.marker, let endpoint = trail.endpoint else { return nil }
            let badge = MultiVanDioramaPieces.badge(.ending(marker.ending, trail.color))
            var base = SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: endpoint.x, gridY: endpoint.y, height: Look.badgeHeight))
            if let house = houses[marker.nodeID] {
                base = house.simdPosition + SIMD3(0, Float(Look.houseBadgeHeight), 0)
            }
            let column = Float(marker.column ?? 0) * Float(Look.badgeColumn)
            badge.simdPosition = base + right * column + SIMD3(0, Float(marker.row) * Float(Look.badgeRow), 0)
            trailsNode.addChildNode(badge)
            return badge
        }
    }

    /// Moves the lens to where the board's switch buttons assume it is.
    func setCamera(_ camera: MultiVanDioramaCamera) {
        guard camera != self.camera else { return }
        self.camera = camera
        applyCamera()
    }

    private func applyCamera() {
        cameraRig.simdPosition = SIMD3<Float>(camera.position)
        // Plain `look(at:)` takes up from the node's current pose, so each orbit
        // would add roll; world up keeps the horizon level, as the camera model does.
        cameraRig.simdLook(at: SIMD3<Float>(camera.lookTarget), up: SIMD3(0, 1, 0), localFront: SCNNode.simdLocalFront)
        cameraNode.camera?.focusDistance = CGFloat(camera.focusDistance)
        cameraNode.camera?.fStop = CGFloat(Self.fStop(focusDistance: camera.focusDistance))
    }

    /// Blur measured against the pieces grows as the camera comes closer, which it
    /// does on wider boards. Stopping down in proportion keeps every board shape
    /// as soft, and as readable, as the reference board.
    static func fStop(focusDistance: Double) -> Double {
        Look.fStop * referenceFocusDistance / max(focusDistance, 1)
    }

    private static let referenceFocusDistance = MultiVanDioramaCamera.framed(in: Look.referenceSize).focusDistance

    // MARK: - Camera and light

    private static func lens() -> SCNCamera {
        let lens = SCNCamera()
        lens.projectionDirection = .vertical
        lens.fieldOfView = CGFloat(MultiVanDioramaCamera.verticalFieldOfView)
        lens.zNear = 0.5
        lens.zFar = 200
        lens.wantsDepthOfField = true
        lens.apertureBladeCount = 6
        lens.focalBlurSampleCount = 16
        // HDR runs the tone map and grade; a fixed exposure keeps the table steady.
        lens.wantsHDR = true
        lens.wantsExposureAdaptation = false
        lens.exposureOffset = -0.3
        lens.saturation = Look.saturation
        lens.vignettingIntensity = Look.vignetting
        lens.vignettingPower = 1
        lens.bloomIntensity = 0
        return lens
    }

    private static func sun() -> SCNNode {
        let light = SCNLight()
        light.type = .directional
        light.color = UIColor(dioramaHex: 0xFFF0D6)
        light.intensity = Look.sunIntensity
        light.castsShadow = true
        light.shadowMapSize = CGSize(width: 2048, height: 2048)
        light.shadowMode = .forward
        light.shadowSampleCount = 8
        light.shadowRadius = 2
        light.shadowColor = UIColor(white: 0, alpha: 0.42)
        light.orthographicScale = 7
        light.zNear = 1
        light.zFar = 30
        let node = SCNNode()
        node.light = light
        node.simdPosition = SIMD3(-5.2, 8.2, 3.6)
        node.simdLook(at: .zero)
        return node
    }

    /// The studio sky behind the table. The lens looks 31°–61° below the horizon,
    /// so the blue-to-cream sweep sits in that band of this equirectangular image.
    private static func backdrop() -> UIImage {
        let size = CGSize(width: 8, height: 512)
        return UIGraphicsImageRenderer(size: size).image { context in
            let colors = [UIColor(dioramaHex: 0xBFE1F2), UIColor(dioramaHex: 0xE4F3F6), UIColor(dioramaHex: 0xFBF1E3)]
                .map(\.cgColor) as CFArray
            let gradient = CGGradient(colorsSpace: nil, colors: colors, locations: [0.64, 0.75, 0.86])!
            context.cgContext.drawLinearGradient(
                gradient, start: .zero, end: CGPoint(x: 0, y: size.height), options: [.drawsBeforeStartLocation, .drawsAfterEndLocation]
            )
        }
    }

    /// An equirectangular sky over a lawn-green ground: SceneKit's stand-in for a
    /// hemisphere light, lighting tops blue-white and undersides green.
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

    // MARK: - Clouds

    /// Where each cloud floats and how wide it is. The lens looks down on the slab,
    /// so clouds sit below its rim, and behind it where they peek over the far edge.
    private static let cloudLayout: [(position: SIMD3<Float>, width: Float)] = [
        (SIMD3(-5.4, -2.6, 2.4), 2.6),
        (SIMD3(4.9, -3.1, 1.2), 2.2),
        (SIMD3(-0.8, -3.6, 6.4), 3.0),
        (SIMD3(5.6, -1.4, -4.2), 2.4),
        (SIMD3(-5.8, -1.8, -3.6), 2.0),
        (SIMD3(1.6, -1.2, -7.4), 3.2),
        (SIMD3(-3.2, -0.9, -8.2), 2.2),
    ]

    private static let cloudDriftKey = "drift"

    /// Puffy paper clouds: a few squashed balls on a flat base, one node each.
    private static func clouds() -> [SCNNode] {
        var random = MultiVanDioramaRandom(seed: 29)
        let puff = SCNSphere(radius: 1)
        puff.isGeodesic = true
        puff.segmentCount = 8
        let material = paper(color: UIColor(dioramaHex: 0xFFFCF6), roughness: 1)
        // The sky lights them more than the sun does, so their shade stays soft.
        material.emission.contents = UIColor(dioramaHex: 0xF2F4F8)
        material.emission.intensity = 0.35
        puff.materials = [material]
        return cloudLayout.map { layout in
            let body = SCNNode()
            let count = 4 + Int(random.next() * 3)
            for index in 0..<count {
                let along = count > 1 ? Double(index) / Double(count - 1) - 0.5 : 0
                // Bigger puffs in the middle, smaller at the ends.
                let size = (0.55 - abs(along) * 0.5) * (0.8 + random.next() * 0.4)
                let ball = SCNNode(geometry: puff)
                ball.simdScale = SIMD3<Float>(Float(size), Float(size * 0.78), Float(size * 0.8))
                ball.simdPosition = SIMD3<Float>(
                    Float(along * 0.95), Float(size * 0.35 + random.next() * 0.08), Float((random.next() - 0.5) * 0.25)
                )
                body.addChildNode(ball)
            }
            let cloud = body.flattenedClone()
            cloud.simdScale = SIMD3(repeating: layout.width / 1.6)
            cloud.simdPosition = layout.position
            cloud.simdEulerAngles.y = Float(MultiVanDioramaCamera.restingYaw + (random.next() - 0.5) * 0.6)
            cloud.castsShadow = false
            return cloud
        }
    }

    /// Clouds drift to and fro while motion is on, and settle home when it's off.
    private func setDrift(_ animates: Bool) {
        for (index, (cloud, layout)) in zip(clouds, Self.cloudLayout).enumerated() {
            cloud.removeAction(forKey: Self.cloudDriftKey)
            cloud.simdPosition = layout.position
            guard animates else { continue }
            let reach = 0.35 + Double(index % 3) * 0.12
            let duration = 9 + Double(index % 4) * 2.5
            let out = SCNAction.moveBy(x: CGFloat(reach), y: 0, z: 0, duration: duration)
            out.timingMode = .easeInEaseOut
            let back = out.reversed()
            let loop = SCNAction.repeatForever(.sequence(index.isMultiple(of: 2) ? [out, back] : [back, out]))
            cloud.runAction(loop, forKey: Self.cloudDriftKey)
        }
    }

    // MARK: - The slab

    /// A die-cut slice of lawn on two soil strata, each stepped in slightly.
    private static func slab(lawn: SCNMaterial) -> SCNNode {
        let slab = SCNNode()
        // The sides wrap the whole rim once.
        let rimTiles = CGSize(width: 14, height: 1)
        let grassSide = paper(texture: grain(on: UIColor(dioramaHex: 0x7DB457), dots: 2600, seed: 11), tiles: rimTiles)
        let soil = paper(texture: grain(on: UIColor(dioramaHex: 0xA26E48), dots: 2600, seed: 13), tiles: rimTiles)
        let deepSoil = paper(texture: grain(on: UIColor(dioramaHex: 0x7B5339), dots: 2600, seed: 17), tiles: rimTiles)
        let grass = slabLayer(inset: 0, bottom: -0.16, height: 0.16, top: lawn, sides: grassSide)
        grass.name = lawnNodeName
        slab.addChildNode(grass)
        slab.addChildNode(slabLayer(inset: 0.05, bottom: -0.6, height: 0.44, top: soil, sides: soil))
        slab.addChildNode(slabLayer(inset: 0.11, bottom: MultiVanDioramaGeometry.slabBottom, height: 0.36, top: deepSoil, sides: deepSoil))
        slab.addChildNode(pebbles())
        return slab
    }

    private static func slabLayer(inset: Double, bottom: Double, height: Double, top: SCNMaterial, sides: SCNMaterial) -> SCNNode {
        let width = MultiVanDioramaGeometry.slabWidth - inset * 2
        let depth = MultiVanDioramaGeometry.slabDepth - inset * 2
        let path = UIBezierPath(
            roundedRect: CGRect(x: -width / 2, y: -depth / 2, width: width, height: depth),
            cornerRadius: MultiVanDioramaGeometry.slabCornerRadius - inset * 0.5
        )
        // Flatness is in path units, and a grid unit is one point: keep the corners round.
        path.flatness = 0.004
        let shape = SCNShape(path: path, extrusionDepth: height)
        shape.materials = [top, sides, sides]
        let node = SCNNode(geometry: shape)
        // The path's plane becomes the ground; its front face becomes the top.
        node.eulerAngles.x = -.pi / 2
        node.simdPosition.y = Float(bottom + height / 2)
        return node
    }

    /// Pebbles pressed into the soil walls, flattened into one node.
    private static func pebbles() -> SCNNode {
        var random = MultiVanDioramaRandom(seed: 3)
        let shapes = [0xC9B8A2, 0x9C8B78, 0xE0D3BF].map { hex in
            let sphere = SCNSphere(radius: 1)
            sphere.segmentCount = 5
            sphere.materials = [paper(color: UIColor(dioramaHex: hex))]
            return sphere
        }
        let halfWidth = MultiVanDioramaGeometry.slabWidth / 2
        let halfDepth = MultiVanDioramaGeometry.slabDepth / 2
        let group = SCNNode()
        for index in 0..<46 {
            let side = Int(random.next() * 4)
            let along = random.next() - 0.5
            let inset = 0.03 + random.next() * 0.06
            let y = -0.25 - random.next() * 0.62
            let node = SCNNode(geometry: shapes[index % 3])
            let size = 0.035 + random.next() * 0.05
            node.simdScale = SIMD3<Float>(Float(size * 1.3), Float(size), Float(size))
            switch side {
            case 0: node.simdPosition = SIMD3<Float>(SIMD3(along * (MultiVanDioramaGeometry.slabWidth - 1), y, halfDepth - inset))
            case 1: node.simdPosition = SIMD3<Float>(SIMD3(along * (MultiVanDioramaGeometry.slabWidth - 1), y, -halfDepth + inset))
            case 2: node.simdPosition = SIMD3<Float>(SIMD3(halfWidth - inset, y, along * (MultiVanDioramaGeometry.slabDepth - 1)))
            default: node.simdPosition = SIMD3<Float>(SIMD3(-halfWidth + inset, y, along * (MultiVanDioramaGeometry.slabDepth - 1)))
            }
            node.simdEulerAngles = SIMD3<Float>(Float(random.next() * 3), Float(random.next() * 3), Float(random.next() * 3))
            group.addChildNode(node)
        }
        return group.flattenedClone()
    }

    /// The soft shadow the slab casts on the floor far below it.
    private static func floorShadow() -> SCNNode {
        let plane = SCNPlane(width: MultiVanDioramaGeometry.slabWidth * 1.5, height: MultiVanDioramaGeometry.slabDepth * 1.35)
        let material = SCNMaterial()
        material.lightingModel = .constant
        material.diffuse.contents = MultiVanDioramaPieces.Texture.blob
        material.transparency = 0.55
        material.writesToDepthBuffer = false
        plane.materials = [material]
        let node = SCNNode(geometry: plane)
        node.eulerAngles.x = -.pi / 2
        node.simdPosition = SIMD3(0.5, -2.2, -0.4)
        node.castsShadow = false
        return node
    }

    static let lawnNodeName = "lawn"

    /// SCNShape maps its front face's bounding box onto the texture, far edge at the
    /// top, which is how `MultiVanDioramaLawn` paints it. Plain grass until a level loads.
    private static func lawnMaterial() -> SCNMaterial {
        let lawn = paper(color: MultiVanDioramaLawn.Palette.lawn)
        // The lens sees the lawn at a grazing angle; mipmaps keep road edges clean.
        lawn.diffuse.mipFilter = .linear
        lawn.diffuse.maxAnisotropy = 8
        return lawn
    }

    // MARK: - Materials

    static func paper(
        color: UIColor = .white, texture: UIImage? = nil, tiles: CGSize? = nil, roughness: CGFloat = 0.88
    ) -> SCNMaterial {
        let material = SCNMaterial()
        material.lightingModel = .physicallyBased
        material.diffuse.contents = texture ?? color
        if let tiles {
            material.diffuse.wrapS = .repeat
            material.diffuse.wrapT = .repeat
            material.diffuse.contentsTransform = SCNMatrix4MakeScale(Float(tiles.width), Float(tiles.height), 1)
        }
        material.roughness.contents = roughness
        material.metalness.contents = 0
        return material
    }

    /// A colour flecked with darker grain, like printed card.
    static func grain(on color: UIColor, dots: Int, seed: UInt32) -> UIImage {
        var random = MultiVanDioramaRandom(seed: seed)
        let side = 256.0
        return UIGraphicsImageRenderer(size: CGSize(width: side, height: side)).image { context in
            let g = context.cgContext
            color.setFill()
            g.fill(CGRect(x: 0, y: 0, width: side, height: side))
            for _ in 0..<dots {
                g.setFillColor(UIColor(white: 0, alpha: 0.03 + random.next() * 0.07).cgColor)
                let radius = 0.6 + random.next() * 2.2
                g.fillEllipse(in: CGRect(x: random.next() * side - radius, y: random.next() * side - radius, width: radius * 2, height: radius * 2))
            }
            for _ in 0..<18 {
                g.setFillColor(UIColor(white: 0, alpha: 0.05).cgColor)
                g.fill(CGRect(x: 0, y: random.next() * side, width: side, height: 1 + random.next() * 3))
            }
        }
    }
}

extension UIColor {
    convenience init(dioramaHex hex: Int) {
        self.init(
            red: CGFloat((hex >> 16) & 0xFF) / 255,
            green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255,
            alpha: 1
        )
    }
}
