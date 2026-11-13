import CoreGraphics
import simd

/// Where everything sits on the 3D level map, without SceneKit: a long island with
/// a road winding up it from level 1 at the near end, and the fixed lens that looks
/// down on it. Map space runs x across the island (0 at its middle) and y along it,
/// from 0 at the near edge to `depth` at the far one. The same maths places the
/// scene's pieces and the SwiftUI tiles over them.
struct TRLevelMapLayout {
    static let width = 6.6
    /// Along the road's length from one level to the next, measured up the island.
    static let step = 1.2
    /// How far the road swings either side of the middle.
    static let amplitude = 1.9
    /// The road swings once for every three levels.
    static let levelsPerSwing = 3.0
    static let nearMargin = 1.25
    static let farMargin = 1.35
    /// Down from the horizon, in radians.
    static let pitch = 0.95
    /// The island's edges stay this far inside the view's sides.
    static let sideMargin = 0.32
    /// Tallest scenery and the soil's lowest point, which the view leaves room for.
    static let sceneryHeight = 1.0
    static let soilBottom = -0.96

    let levelCount: Int
    /// How far this map's road swings either side; the curved 3D map swings gentler.
    var swing: Double = TRLevelMapLayout.amplitude
    /// Island before the first level and past the last; the curved map's run on
    /// out of view, so its road never stops short on screen.
    var margins: (near: Double, far: Double) = (TRLevelMapLayout.nearMargin, TRLevelMapLayout.farMargin)

    var depth: Double {
        margins.near + Double(max(levelCount - 1, 0)) * Self.step + margins.far
    }

    // MARK: - Road

    /// The road's middle where it crosses `y`.
    func roadPoint(atY y: Double) -> RoadPoint {
        let phase = (y - margins.near) / Self.step * (2 * .pi / Self.levelsPerSwing)
        return RoadPoint(x: swing * sin(phase), y: y)
    }

    /// The road's direction of travel up the island at `y`, not normalised.
    func roadHeading(atY y: Double) -> RoadVector {
        let rate = 2 * .pi / Self.levelsPerSwing / Self.step
        let phase = (y - margins.near) * rate
        return RoadVector(x: swing * rate * cos(phase), y: 1)
    }

    /// Level `index`'s stop on the road, 0 for the first level.
    func station(_ index: Int) -> RoadPoint {
        roadPoint(atY: margins.near + Double(index) * Self.step)
    }

    /// The lawn a tile hides, around its stop: a tile stands on the road and
    /// reaches about a unit up the screen, which is away from the lens.
    static let tileHalfWidth = 0.55
    static let tileFront = 0.25
    static let tileBack = 1.1

    /// How much of a box, `minX…maxX` across and `minY…maxY` along the island,
    /// lies under any level's tile.
    func tileOverlap(minX: Double, maxX: Double, minY: Double, maxY: Double) -> Double {
        (0..<levelCount).reduce(0) { total, index in
            let stop = station(index)
            let across = min(maxX, stop.x + Self.tileHalfWidth) - max(minX, stop.x - Self.tileHalfWidth)
            let along = min(maxY, stop.y + Self.tileBack) - max(minY, stop.y - Self.tileFront)
            return total + max(across, 0) * max(along, 0)
        }
    }

    /// Where the van waits for level `index`: the spot on the road near its stop
    /// where the van covers the least of any tile. The road winds close behind
    /// each tile, so this is before the stop for some levels and past it for others.
    func parking(_ index: Int) -> Double {
        let stopY = station(index).y
        var best = (score: Double.infinity, y: stopY)
        for offset in stride(from: -1.0, through: 0.75, by: 0.025) {
            let y = stopY + offset
            guard y > 0.3, y < depth - 0.3 else { continue }
            let x = roadPoint(atY: y).x
            // The van's footprint, and its roof up the screen.
            let covered = tileOverlap(minX: x - 0.33, maxX: x + 0.33, minY: y - 0.33, maxY: y + 0.6)
            // Nearer the stop wins a tie.
            let score = covered + abs(offset) * 0.03
            if score < best.score { best = (score, y) }
        }
        return best.y
    }

    /// The road's middle from `fromY` to `toY`, either way along it, about `spacing`
    /// apart and always including both ends.
    func roadSamples(fromY: Double, toY: Double, spacing: Double = 0.1) -> [RoadPoint] {
        // Steps are taken along the curve, so a steep swing isn't skipped over.
        var points = [roadPoint(atY: fromY)]
        var y = fromY
        let direction: Double = toY >= fromY ? 1 : -1
        while (toY - y) * direction > 1e-9 {
            let heading = roadHeading(atY: y)
            let advance = spacing / hypot(heading.x, heading.y)
            y = direction > 0 ? min(y + advance, toY) : max(y - advance, toY)
            points.append(roadPoint(atY: y))
        }
        return points
    }

    /// The shortest way from `point` to the road's middle, sampled.
    func distanceToRoad(_ point: RoadPoint) -> Double {
        var best = Double.infinity
        // The road is never more than about 1.1 units of y from a point beside it.
        let low = max(0, point.y - 1.6), high = min(depth, point.y + 1.6)
        for sample in roadSamples(fromY: low, toY: high, spacing: 0.06) {
            best = min(best, hypot(sample.x - point.x, sample.y - point.y))
        }
        return best
    }

    // MARK: - World and screen

    /// Map space to world space: the island centred on the origin, its near edge
    /// towards the camera (+z).
    func world(_ point: RoadPoint, height: Double = 0) -> SIMD3<Double> {
        SIMD3(point.x, height, depth / 2 - point.y)
    }

    /// The lens's up direction in the world; it looks along -z, tilted down by `pitch`.
    static let up = SIMD3<Double>(0, cos(pitch), -sin(pitch))
    static let forward = SIMD3<Double>(0, -sin(pitch), -cos(pitch))

    /// The span of the image up the screen, in world units along `up`: from the soil
    /// under the near edge to the tallest tree at the far one.
    private var verticalRange: ClosedRange<Double> {
        let near = SIMD3(0, Self.soilBottom, depth / 2)
        let far = SIMD3(0, Self.sceneryHeight, -depth / 2)
        return simd_dot(near, Self.up) - 0.25 ... simd_dot(far, Self.up) + 0.15
    }

    /// Points per world unit for a view `viewWidth` wide.
    static func scale(viewWidth: CGFloat) -> CGFloat {
        viewWidth / CGFloat(width + sideMargin * 2)
    }

    /// The view's height for a view `viewWidth` wide.
    func viewHeight(viewWidth: CGFloat) -> CGFloat {
        CGFloat(verticalRange.upperBound - verticalRange.lowerBound) * Self.scale(viewWidth: viewWidth)
    }

    /// Where the lens looks, and half the image's height in world units: the
    /// orthographic scale SceneKit takes for a vertical projection.
    var lens: (target: SIMD3<Double>, orthographicScale: Double) {
        let range = verticalRange
        return (Self.up * (range.lowerBound + range.upperBound) / 2, (range.upperBound - range.lowerBound) / 2)
    }

    /// A world point on screen, in a view `viewWidth` wide.
    func viewPoint(_ world: SIMD3<Double>, viewWidth: CGFloat) -> CGPoint {
        let scale = Self.scale(viewWidth: viewWidth)
        return CGPoint(
            x: viewWidth / 2 + CGFloat(world.x) * scale,
            y: CGFloat(verticalRange.upperBound - simd_dot(world, Self.up)) * scale
        )
    }
}

extension TRLevelMapLayout: Equatable {
    static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.levelCount == rhs.levelCount && lhs.swing == rhs.swing && lhs.margins == rhs.margins
    }
}
