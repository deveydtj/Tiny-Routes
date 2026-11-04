import CoreGraphics
import simd

/// Renderer-free maths for the diorama board: where the grid sits in the world and
/// where the camera stands. Nothing here imports SceneKit, so it is unit tested and
/// carries over unchanged if the renderer is swapped.
enum MultiVanDioramaGeometry {
    // The table, in grid units.
    static let slabWidth = 6.6
    static let slabDepth = 8.6
    static let slabCornerRadius = 0.42
    /// Lowest point of the soil strata.
    static let slabBottom = -0.96
    /// Tallest piece on the lawn, so framing leaves room for the back row of houses.
    static let pieceHeight = 0.45
    /// From a house's node to its centre, along the road's arrival direction. Its
    /// front then meets the end of the driveway the lawn paints.
    static let houseSetback = 0.54
    /// A roadblock stands just past the end of its road.
    static let roadblockSetback = 0.06
    /// The top of a switch dial's face, where its button sits.
    static let dialFaceHeight = 0.07

    /// Grid (x 0…4, y 0…6, y up the board) to world (x right, y up, z towards the
    /// camera). Row 0 is nearest the viewer, like the bottom row of the flat board.
    static func world(gridX: Double, gridY: Double, height: Double = 0) -> SIMD3<Double> {
        SIMD3(gridX - 2, height, 3 - gridY)
    }

    /// `point` moved `distance` grid units along `heading`; unmoved for a zero heading.
    static func offset(_ point: RoadPoint, along heading: RoadVector, by distance: Double) -> RoadPoint {
        let length = hypot(heading.x, heading.y)
        guard length.isFinite, length > 1e-9 else { return point }
        return RoadPoint(x: point.x + heading.x / length * distance, y: point.y + heading.y / length * distance)
    }

    /// Yaw about +y that turns a piece's front (+z) to face `heading`, a grid direction.
    static func yaw(facing heading: RoadVector) -> Double {
        atan2(heading.x, -heading.y)
    }

    /// The same for a flat-board screen angle: 0 points right, positive turns
    /// clockwise, as `SwitchArrowDirectionResolver` measures switch exits.
    static func yaw(screenAngle: Double) -> Double {
        .pi / 2 - screenAngle
    }

    /// A flat-board screen angle as a unit vector across the lawn.
    static func worldDirection(screenAngle: Double) -> SIMD3<Double> {
        SIMD3(cos(screenAngle), 0, sin(screenAngle))
    }

    /// Where a switch's button aims: the middle of its dial's face.
    static func switchPoint(_ node: RuntimeRouteNode) -> SIMD3<Double> {
        world(gridX: node.x, gridY: node.y, height: dialFaceHeight)
    }

    /// The slab's corners at piece height and at its base. The camera frames these.
    static let fitPoints: [SIMD3<Double>] = {
        var points: [SIMD3<Double>] = []
        for x in [-slabWidth / 2, slabWidth / 2] {
            for z in [-slabDepth / 2, slabDepth / 2] {
                points.append(SIMD3(x, pieceHeight, z))
                points.append(SIMD3(x, slabBottom, z))
            }
        }
        return points
    }()
}

/// A long lens looking down at the table from a balcony, orbiting `target`.
/// `pan` slides camera and target together along the image plane, which is how the
/// slab is centred in its view without a lens shift.
struct MultiVanDioramaCamera: Equatable {
    static let restingYaw = -0.24
    static let restingPitch = 0.80
    static let verticalFieldOfView = 30.0
    /// Where the board is sharpest.
    static let focusPoint = SIMD3<Double>(0, 0, 0.2)
    /// Points between the slab and the view's edges.
    static let frameInset = 10.0

    var yaw = restingYaw
    var pitch = restingPitch
    var distance = 20.0
    var pan = SIMD2<Double>.zero
    let orbitTarget = SIMD3<Double>(0, -0.15, 0.1)

    private var orbitOffset: SIMD3<Double> {
        SIMD3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
    }

    /// Unit vectors for the camera's view, matching SceneKit's `look(at:)` with world up +y.
    var basis: (forward: SIMD3<Double>, right: SIMD3<Double>, up: SIMD3<Double>) {
        let forward = simd_normalize(-orbitOffset)
        let right = simd_normalize(simd_cross(forward, SIMD3(0, 1, 0)))
        return (forward, right, simd_cross(right, forward))
    }

    private var panOffset: SIMD3<Double> {
        let basis = basis
        return basis.right * pan.x + basis.up * pan.y
    }

    var position: SIMD3<Double> { orbitTarget + orbitOffset + panOffset }
    var lookTarget: SIMD3<Double> { orbitTarget + panOffset }

    /// Distance from the lens to the plane through `focusPoint`, along the view axis.
    var focusDistance: Double {
        simd_dot(Self.focusPoint - position, basis.forward)
    }

    /// Normalised device coordinates: x and y run −1…1 across the view, y up.
    /// Nil for a point at or behind the lens.
    func project(_ point: SIMD3<Double>, aspect: Double) -> SIMD2<Double>? {
        let basis = basis
        let offset = point - position
        let depth = simd_dot(offset, basis.forward)
        guard depth > 0, aspect > 0 else { return nil }
        let halfHeight = tan(Self.verticalFieldOfView * .pi / 360) * depth
        return SIMD2(simd_dot(offset, basis.right) / (halfHeight * aspect), simd_dot(offset, basis.up) / halfHeight)
    }

    /// Where `point` lands in a view of `size`, in points from its top-left corner,
    /// as SceneKit's `projectPoint` puts it. Nil for a point at or behind the lens.
    func viewPoint(for point: SIMD3<Double>, in size: CGSize) -> CGPoint? {
        let width = Double(size.width), height = Double(size.height)
        guard height > 0, let ndc = project(point, aspect: width / height) else { return nil }
        return CGPoint(x: (ndc.x + 1) / 2 * width, y: (1 - ndc.y) / 2 * height)
    }

    /// This camera turned to `orbit` and moved in by its zoom, towards its zoom
    /// centre. At no zoom it keeps its distance and pan.
    func orbited(_ orbit: MultiVanDioramaOrbit) -> Self {
        var camera = self
        camera.yaw = orbit.yaw
        camera.pitch = orbit.pitch
        guard orbit.zoom != 1 || orbit.zoomCentre != .zero else { return camera }
        let halfHeight = tan(Self.verticalFieldOfView * .pi / 360) * distance
        camera.distance = distance / orbit.zoom
        camera.pan += orbit.zoomCentre * halfHeight
        return camera
    }

    /// Points along the top and bottom of the view that floating controls cover.
    /// The camera frames the slab in the open band between them.
    struct Covered: Equatable {
        var top = 0.0
        var bottom = 0.0

        /// The smallest share of the view the open band keeps. Taller overlays,
        /// as in a landscape phone, are shrunk in proportion so the table never
        /// shrinks to a sliver; the overlays then cover some of its edge.
        static let minimumOpenShare = 0.5

        func fitted(toHeight height: Double) -> Self {
            let top = max(0, top), bottom = max(0, bottom)
            let allowed = height * (1 - Self.minimumOpenShare)
            guard top + bottom > allowed, top + bottom > 0 else { return Self(top: top, bottom: bottom) }
            let scale = allowed / (top + bottom)
            return Self(top: top * scale, bottom: bottom * scale)
        }
    }

    /// A camera at the resting angle, fitting the slab into a view of `size`,
    /// clear of `covered`.
    static func framed(in size: CGSize, inset: Double = frameInset, covered: Covered = Covered()) -> Self {
        var camera = Self()
        camera.frame(MultiVanDioramaGeometry.fitPoints, in: size, inset: inset, covered: covered)
        return camera
    }

    /// Moves the camera in or out until `points` just fit inside `size` less `inset`
    /// points on every side and the `covered` strips, centring them in what is left
    /// at the resting angle. Leaves the camera as it was for an empty size.
    mutating func frame(_ points: [SIMD3<Double>], in size: CGSize, inset: Double, covered: Covered = Covered()) {
        let width = Double(size.width), height = Double(size.height)
        let covered = covered.fitted(toHeight: height)
        let open = height - covered.top - covered.bottom
        guard width > 2 * inset, open > 2 * inset, !points.isEmpty else { return }
        let aspect = width / height
        // The open band's middle and half-extents, in normalised device coordinates.
        let target = SIMD2(0, (covered.bottom - covered.top) / height)
        let limit = SIMD2(1 - 2 * inset / width, (open - 2 * inset) / height)
        yaw = Self.restingYaw
        pitch = Self.restingPitch
        pan = .zero
        // Fit, re-centre, and fit again; three re-centrings settle well inside a pixel.
        // The last pass only fits, so the result always fits.
        for pass in 0..<4 {
            var near = 2.0, far = 120.0
            for _ in 0..<30 {
                distance = (near + far) / 2
                let fits = points.allSatisfy { point in
                    guard let p = project(point, aspect: aspect) else { return false }
                    return abs(p.x - target.x) <= limit.x && abs(p.y - target.y) <= limit.y
                }
                if fits { far = distance } else { near = distance }
            }
            distance = far
            guard pass < 3 else { break }
            let projected = points.compactMap { project($0, aspect: aspect) }
            let lower = projected.reduce(SIMD2(repeating: Double.infinity)) { simd_min($0, $1) }
            let upper = projected.reduce(SIMD2(repeating: -Double.infinity)) { simd_max($0, $1) }
            let centre = (lower + upper) / 2 - target
            let halfHeight = tan(Self.verticalFieldOfView * .pi / 360) * distance
            pan += SIMD2(centre.x * halfHeight * aspect, centre.y * halfHeight)
        }
    }
}

/// Which way the player has turned the table and how close they have leant in. A
/// drag orbits the camera around the board, within limits that keep the lawn in
/// view; a pinch zooms towards the fingers; a double tap straightens it.
struct MultiVanDioramaOrbit: Equatable {
    /// Radians per point of drag, and the limits, from the HTML prototype.
    static let yawPerPoint = 0.006
    static let pitchPerPoint = 0.004
    static let yawRange = -0.85...0.85
    static let pitchRange = 0.45...1.30
    static let resting = Self(yaw: MultiVanDioramaCamera.restingYaw, pitch: MultiVanDioramaCamera.restingPitch)

    static let zoomRange = 1.0...3.0

    var yaw: Double
    var pitch: Double
    /// How many times closer than the framed camera.
    var zoom = 1.0
    /// The middle of the zoomed view, in the framed view's half-heights from its
    /// centre (x right, y up). It stays where the zoomed view fits inside the
    /// framed one, so zooming never shows more than the framed view does.
    var zoomCentre = SIMD2<Double>.zero

    /// Turned by a drag of `translation` points from here: sideways swings round
    /// the table, downwards looks from higher up.
    func dragged(by translation: CGSize) -> Self {
        var orbit = self
        orbit.yaw = (yaw - Double(translation.width) * Self.yawPerPoint).clamped(to: Self.yawRange)
        orbit.pitch = (pitch + Double(translation.height) * Self.pitchPerPoint).clamped(to: Self.pitchRange)
        return orbit
    }

    /// Zoomed by a pinch of `magnification` from here, keeping the spot under
    /// `anchor` where it is. `anchor` is where the fingers started, as fractions of
    /// a view of `size` from its top-left corner.
    func pinched(by magnification: CGFloat, anchor: CGPoint, in size: CGSize) -> Self {
        let width = Double(size.width), height = Double(size.height)
        guard width > 0, height > 0, magnification.isFinite, magnification > 0 else { return self }
        let aspect = width / height
        let finger = SIMD2((2 * Double(anchor.x) - 1) * aspect, 1 - 2 * Double(anchor.y))
        let spot = zoomCentre + finger / zoom
        var orbit = self
        orbit.zoom = (zoom * Double(magnification)).clamped(to: Self.zoomRange)
        let reach = 1 - 1 / orbit.zoom
        let centre = spot - finger / orbit.zoom
        orbit.zoomCentre = SIMD2(
            centre.x.clamped(to: -reach * aspect...reach * aspect),
            centre.y.clamped(to: -reach...reach)
        )
        return orbit
    }
}

private extension Double {
    func clamped(to range: ClosedRange<Double>) -> Double {
        min(max(self, range.lowerBound), range.upperBound)
    }
}

/// Mulberry32, as in the HTML prototype, so a seed gives the same layout in both.
struct MultiVanDioramaRandom {
    private var state: UInt32

    init(seed: UInt32) { state = seed }

    /// A value in 0..<1.
    mutating func next() -> Double {
        state &+= 0x6D2B79F5
        var t = (state ^ (state >> 15)) &* (1 | state)
        t = (t &+ ((t ^ (t >> 7)) &* (61 | t))) ^ t
        return Double(t ^ (t >> 14)) / 4_294_967_296
    }
}
