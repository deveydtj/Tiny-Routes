import CoreGraphics
import simd

/// Where things sit on the curved 3D level map, without SceneKit. The map is the
/// flat level map's island and road, gentler in its swing, on a treadmill that
/// slides under a fixed perspective lens: `focus` is the map y under the pivot, the
/// world origin. Map space runs x across and y up the road; the treadmill's own
/// space keeps x and runs the road towards -z, and the world is the treadmill
/// moved `focus` towards the lens. The same maths places the scene's pieces, finds
/// the signs under a tap and scrolls the map under a drag.
struct TRCurvedLevelMapLens: Equatable {
    /// Up from the ground and behind the pivot. The lens tips down as far as puts
    /// the horizon `horizonShare` of the way down the view, whatever its shape.
    static let eyeHeight = 6.0
    static let eyeBack = 3.0
    /// Across the view, so every phone sees the road's whole swing.
    static let horizontalFieldOfView = 32.0
    static let horizonShare = 0.1
    static let zNear = 0.1
    static let zFar = 60.0
    static let curve = TRCurvedWorld(curvature: 0.03, originZ: eyeBack)
    /// Gentler than the flat map's, to stay in view of the perspective lens.
    static let swing = 1.15
    /// Past the foot of the view before level 1, and on towards the horizon after
    /// the last level.
    static let margins = (near: 4.0, far: 6.0)

    /// A level's sign: a card on a post, standing at its stop.
    enum Sign {
        /// The square card, which leaves room round the tile for its glow and badges.
        static let width = 1.0
        /// How much of the card's width the tile fills.
        static let tileShare = 0.58
        static let postHeight = 0.34
        /// Signs fade out between these distances ahead of the pivot, so only the
        /// next few levels stand on the road ahead rather than a crowd on the horizon.
        static let fadeStart = 3.6
        static let fadeEnd = 4.8
    }

    let layout: TRLevelMapLayout

    init(levelCount: Int) {
        layout = TRLevelMapLayout(levelCount: levelCount, swing: Self.swing, margins: Self.margins)
    }

    static let eye = SIMD3<Double>(0, eyeHeight, eyeBack)

    /// The lens's axes in the world: it looks along `forward`, with `right` and `up`
    /// across and up the screen.
    struct Pose {
        /// Down from level, in radians.
        let pitch: Double
        var forward: SIMD3<Double> { SIMD3(0, -sin(pitch), -cos(pitch)) }
        var up: SIMD3<Double> { SIMD3(0, cos(pitch), -sin(pitch)) }
        let right = SIMD3<Double>(1, 0, 0)
    }

    /// How the lens tips for a view of `size`. The sight line that grazes the curve
    /// dips atan(2·√(c·h)) below level; the lens tips that far, and on by the angle
    /// from its axis to `horizonShare` of the way down the view.
    static func pose(in size: CGSize) -> Pose {
        let horizon = atan(2 * (curve.curvature * eyeHeight).squareRoot())
        return Pose(pitch: horizon + atan((1 - 2 * horizonShare) * tangents(in: size).y))
    }

    // MARK: - Map, treadmill and world

    /// Map space to the treadmill's own space.
    static func local(_ point: RoadPoint, height: Double = 0) -> SIMD3<Double> {
        SIMD3(point.x, height, -point.y)
    }

    /// Map space to the world while map y `focus` sits under the pivot.
    static func world(_ point: RoadPoint, height: Double = 0, focus: Double) -> SIMD3<Double> {
        SIMD3(point.x, height, focus - point.y)
    }

    /// The map y under the pivot while level `index` is shown: its sign.
    func focus(forLevel index: Int) -> Double {
        layout.station(index).y
    }

    /// How far the map scrolls: from the first level's sign to the last's.
    var focusRange: ClosedRange<Double> {
        focus(forLevel: 0)...focus(forLevel: max(layout.levelCount - 1, 0))
    }

    // MARK: - Screen

    /// Half the view's width over the depth, and half its height.
    static func tangents(in size: CGSize) -> (x: Double, y: Double) {
        let x = tan(horizontalFieldOfView * .pi / 360)
        return (x, x * Double(size.height / max(size.width, 1)))
    }

    /// A drawn world point on screen in a view of `size`; nil when it's behind the lens.
    static func viewPoint(drawn point: SIMD3<Double>, in size: CGSize) -> CGPoint? {
        let offset = point - eye
        let pose = pose(in: size)
        let depth = simd_dot(offset, pose.forward)
        guard depth > zNear else { return nil }
        let tangents = tangents(in: size)
        let x = simd_dot(offset, pose.right) / (depth * tangents.x)
        let y = simd_dot(offset, pose.up) / (depth * tangents.y)
        return CGPoint(x: (x + 1) / 2 * size.width, y: (1 - y) / 2 * size.height)
    }

    /// A flat world point on screen, bent as the shader bends it.
    static func viewPoint(_ point: SIMD3<Double>, in size: CGSize) -> CGPoint? {
        viewPoint(drawn: curve.bent(point), in: size)
    }

    /// Where the ground meets the sky across the view: the highest the bent ground
    /// reaches up the screen.
    static func horizonY(in size: CGSize) -> CGFloat {
        let distance = (eyeHeight / curve.curvature).squareRoot()
        // The sight line just grazes the ground there.
        return viewPoint(SIMD3(0, 0, curve.originZ - distance), in: size)?.y ?? 0
    }

    /// Level `index`'s tile on screen while the map shows `focus`, with a little room
    /// round it for a fingertip, or nil when the sign is behind the lens, off the
    /// view, faded out ahead, or sunk behind the curve.
    func signFrame(_ index: Int, focus: Double, in size: CGSize) -> CGRect? {
        let foot = Self.world(layout.station(index), focus: focus)
        let card = Sign.width
        guard -foot.z < (Sign.fadeStart + Sign.fadeEnd) / 2,
              Self.curve.isVisible(height: Sign.postHeight + card * Sign.tileShare, atZ: foot.z, eyeHeight: Self.eyeHeight) else { return nil }
        let half = card * Sign.tileShare / 2
        // The tile stands on the post; the card's margin hangs round it.
        let pose = Self.pose(in: size)
        let centre = foot + SIMD3(0, Sign.postHeight, 0) + pose.up * half
        let reach = half * 1.2
        // The card faces the lens, so its corners lie along the lens's own axes.
        let corners = [(-1.0, -1.0), (1, -1), (-1, 1), (1, 1)].compactMap { across, along in
            Self.viewPoint(centre + pose.right * (across * reach) + pose.up * (along * reach), in: size)
        }
        guard corners.count == 4 else { return nil }
        let xs = corners.map(\.x), ys = corners.map(\.y)
        let frame = CGRect(x: xs.min()!, y: ys.min()!, width: xs.max()! - xs.min()!, height: ys.max()! - ys.min()!)
        return frame.intersects(CGRect(origin: .zero, size: size)) ? frame : nil
    }

    /// How far the ground under the pivot moves on screen for a unit of focus, so a
    /// drag keeps the road under the finger there.
    static func pointsPerUnit(in size: CGSize) -> CGFloat {
        guard let near = viewPoint(SIMD3(0, 0, 0.05), in: size), let far = viewPoint(SIMD3(0, 0, -0.05), in: size) else { return 1 }
        return max((near.y - far.y) / 0.1, 1)
    }
}
