import CoreGraphics
import Foundation

/// The village level map's world, after the "B2 · Village level picker" design: a
/// road snakes away up a tilted lawn with a house by it for each level, on
/// alternating sides. World units are the design's points at its 390 pt width; x
/// runs across the board and y along the road, away from the viewer. The camera is
/// the y at the board's near lip, and the van parks a little way ahead of it.
struct TRVillageRoad {
    /// Road between one house and the next.
    static let spacing = 80.0
    /// How far the road swings either side of the middle, at its least and most;
    /// each bend picks its own.
    static let swingRange = 78.0...94.0
    static let centerX = 195.0
    /// How far ahead of the camera the van parks.
    static let vanLead = 170.0
    static let levelsPerChapter = 10
    /// The y step the road's outline is sampled at.
    static let sampleStep = 4.0

    let levelCount: Int
    /// The furthest level the van can drive to, from 1.
    let currentLevel: Int
    /// The road's length from y = -20 to each whole y after it.
    private let arc: [Double]

    init(levelCount: Int, currentLevel: Int) {
        self.levelCount = max(levelCount, 1)
        self.currentLevel = min(max(currentLevel, 1), self.levelCount)
        // Far enough past the last house for the camera's whole view.
        let top = Double(self.levelCount) * Self.spacing + 900
        var arc = [0.0]
        arc.reserveCapacity(Int(top) + 21)
        var previous = Self.roadX(-20)
        var y = -19.0
        while y <= top {
            let x = Self.roadX(y)
            arc.append(arc[arc.count - 1] + ((x - previous) * (x - previous) + 1).squareRoot())
            previous = x
            y += 1
        }
        self.arc = arc
    }

    // MARK: - The road

    static func roadX(_ y: Double) -> Double {
        let (swing, _) = swing(atY: y)
        return centerX - swing * cos(.pi * y / spacing)
    }

    static func roadSlope(_ y: Double) -> Double {
        let (swing, change) = swing(atY: y)
        let angle = Double.pi * y / spacing
        return swing * .pi / spacing * sin(angle) - change * cos(angle)
    }

    /// How wide the road swings at `y`, easing from one bend's swing to the
    /// next's, and how fast that's changing. The road still crosses the middle
    /// halfway between bends.
    private static func swing(atY y: Double) -> (swing: Double, change: Double) {
        let along = y / spacing
        let band = Int(along.rounded(.down))
        let f = along - Double(band)
        let from = bendSwing(band), to = bendSwing(band + 1)
        let eased = f * f * (3 - 2 * f)
        return (from + (to - from) * eased, (to - from) * 6 * f * (1 - f) / spacing)
    }

    private static func bendSwing(_ band: Int) -> Double {
        swingRange.lowerBound + (swingRange.upperBound - swingRange.lowerBound) * noise(band, 1)
    }

    /// Level 0 is the depot the road starts from; even levels sit on the left,
    /// each nudged a little in from the edge or along the road.
    static func houseX(_ level: Int) -> Double {
        let nudge = 10 * noise(level, 3) - 3
        return level.isMultiple(of: 2) ? 50 + nudge : 340 - nudge
    }

    static func houseY(_ level: Int) -> Double { Double(level) * spacing + 4 + 6 * (noise(level, 4) - 0.5) }

    /// Which of the roof colours `level`'s house has.
    static func roofIndex(_ level: Int, of count: Int) -> Int { Int(noise(level, 5) * Double(count)) % count }

    /// How big `level`'s house is against the usual.
    static func houseScale(_ level: Int) -> Double { 0.94 + 0.12 * noise(level, 6) }

    /// A number in 0..<1 that's always the same for the same pair, but looks
    /// random from one pair to the next.
    static func noise(_ a: Int, _ b: Int) -> Double {
        var h = UInt64(bitPattern: Int64(a)) &* 0x9E37_79B9_7F4A_7C15 ^ UInt64(bitPattern: Int64(b)) &* 0xC2B2_AE3D_27D4_EB4F
        h ^= h >> 31
        h &*= 0xBF58_476D_1CE4_E5B9
        h ^= h >> 29
        return Double(h >> 11) / Double(1 << 53)
    }

    /// A point `offset` across the road from its middle at `y`, square to it.
    static func roadPoint(_ y: Double, offset: Double) -> (x: Double, y: Double) {
        let slope = roadSlope(y)
        let length = (1 + slope * slope).squareRoot()
        return (roadX(y) + offset / length, y - offset * slope / length)
    }

    func arcLength(atY y: Double) -> Double {
        let f = y + 20
        let i = min(max(Int(f.rounded(.down)), 0), arc.count - 2)
        let t = min(max(f - Double(i), 0), 1)
        return arc[i] + (arc[i + 1] - arc[i]) * t
    }

    func y(atArcLength s: Double) -> Double {
        var lo = 0, hi = arc.count - 1
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if arc[mid] <= s { lo = mid } else { hi = mid }
        }
        return Double(lo) + (s - arc[lo]) / max(1e-6, arc[hi] - arc[lo]) - 20
    }

    // MARK: - The camera

    /// The camera that parks the van at `level`'s house.
    func camera(forLevel level: Int) -> Double { Double(level) * Self.spacing - Self.vanLead }

    /// From the first level to the furthest one open.
    var cameraRange: ClosedRange<Double> { camera(forLevel: 1)...camera(forLevel: currentLevel) }

    /// The van rides with the camera but never past the furthest level open.
    func vanY(camera: Double) -> Double {
        min(max(camera + Self.vanLead, 0), Double(currentLevel) * Self.spacing)
    }

    /// The level whose house the van is nearest.
    func selectedLevel(camera: Double) -> Int {
        min(max(Int((vanY(camera: camera) / Self.spacing).rounded()), 1), currentLevel)
    }

    /// The furthest a finger can pull the camera past either end.
    static let stretchLimit = 110.0

    /// Where the camera shows for a finger that has dragged it to `raw`: there,
    /// inside the road's ends; past them, giving way more and more the further
    /// it goes. Worked out afresh from `raw` each time, so turning back past an
    /// end retraces the same way, with no jump.
    func rubberBanded(_ raw: Double) -> Double {
        let range = cameraRange
        if raw > range.upperBound { return range.upperBound + Self.stretch(raw - range.upperBound) }
        if raw < range.lowerBound { return range.lowerBound - Self.stretch(range.lowerBound - raw) }
        return raw
    }

    /// Where a finger would have dragged the camera to show it at `camera`.
    func unbanded(_ camera: Double) -> Double {
        let range = cameraRange
        if camera > range.upperBound { return range.upperBound + Self.unstretch(camera - range.upperBound) }
        if camera < range.lowerBound { return range.lowerBound - Self.unstretch(range.lowerBound - camera) }
        return camera
    }

    /// How far the camera moves for each unit the finger drags it, at `raw`.
    func give(at raw: Double) -> Double {
        let range = cameraRange
        let over = max(raw - range.upperBound, range.lowerBound - raw)
        guard over > 0 else { return 1 }
        let limit = Self.stretchLimit
        return 0.5 * limit * limit / ((limit + 0.5 * over) * (limit + 0.5 * over))
    }

    /// Half the finger's pull at first, closing in on the limit.
    private static func stretch(_ over: Double) -> Double {
        stretchLimit * 0.5 * over / (stretchLimit + 0.5 * over)
    }

    private static func unstretch(_ shown: Double) -> Double {
        let shown = min(shown, stretchLimit * 0.999)
        return 2 * shown * stretchLimit / (stretchLimit - shown)
    }

    /// Where a let-go camera comes to rest: back inside the road's ends, else at
    /// the house nearest where its `velocity` (units a second) would carry it.
    func restingCamera(from camera: Double, velocity: Double) -> Double {
        let range = cameraRange
        if camera > range.upperBound { return range.upperBound }
        if camera < range.lowerBound { return range.lowerBound }
        let ahead = camera + min(max(velocity, -3000), 3000) * 0.26
        let level = min(max(Int(((ahead + Self.vanLead) / Self.spacing).rounded()), 1), currentLevel)
        return self.camera(forLevel: level)
    }

    // MARK: - Chapters

    var chapterCount: Int { (levelCount + Self.levelsPerChapter - 1) / Self.levelsPerChapter }

    static func chapter(ofLevel level: Int) -> Int { (max(level, 1) - 1) / levelsPerChapter + 1 }
    static func firstLevel(ofChapter chapter: Int) -> Int { (chapter - 1) * levelsPerChapter + 1 }

    static let chapterNames = ["Willow Bend", "Maple Lane", "Harbor Hill", "Pinecrest", "Lantern Square"]

    static func chapterName(_ chapter: Int) -> String {
        chapterNames.indices.contains(chapter - 1) ? chapterNames[chapter - 1] : "Chapter \(chapter)"
    }
}

/// Projects the village onto the screen: the near lip of the board at `lip`, its
/// far edge at the board's top, where things are `farScale` of their full size,
/// shrinking on towards a horizon above. Across, the design's 390 pt scale to the
/// page's width.
struct TRVillageLens {
    static let depth = 1170.0
    static let farScale = 0.6

    let scaleX: Double
    let lip: Double
    let horizon: Double

    init(width: Double, boardTop: Double, lip: Double) {
        scaleX = width / 390
        self.lip = lip
        horizon = lip - (lip - boardTop) / (1 - Self.farScale)
    }

    struct Projection {
        let point: CGPoint
        /// Size against size at the lip.
        let scale: Double
        /// How far ahead of the camera.
        let depth: Double
    }

    func project(x: Double, y: Double, camera: Double) -> Projection {
        let d = max(-Self.depth * 0.6, y - camera)
        let s = Self.depth / (Self.depth + d)
        let cx = TRVillageRoad.centerX
        return Projection(
            point: CGPoint(x: (cx + (x - cx) * s) * scaleX, y: horizon + (lip - horizon) * s),
            scale: s,
            depth: d
        )
    }

    /// How many screen points the ground under `screenY` moves for a world unit.
    func pointsPerUnit(atScreenY screenY: Double) -> Double {
        let s = min(max((screenY - horizon) / (lip - horizon), 0.64), 1)
        return (lip - horizon) * s * s / Self.depth
    }
}

// MARK: - Scenery

/// Something standing on the lawn.
struct TRVillageProp: Equatable {
    enum Kind: Equatable {
        case tree, pine, bush, flowers, rock, pond
    }

    let kind: Kind
    let x: Double
    let y: Double
    /// Its size against the piece's usual.
    let scale: Double
    /// Picks its colour, and sets it swaying out of step with its neighbours.
    let seed: Double

    /// Roughly how far it reaches across, for keeping things apart.
    var reach: Double {
        let base: Double = switch kind {
        case .tree: 16
        case .pine: 14
        case .bush: 13
        case .flowers: 10
        case .rock: 8
        case .pond: 34
        }
        return base * scale
    }
}

extension TRVillageRoad {
    /// The scenery scattered over band `band`'s stretch of lawn, from its house
    /// to the next: a few trees, bushes, flowers and rocks, now and then a pond,
    /// kept off the road and clear of the houses and signs. The same every time.
    func props(inBand band: Int) -> [TRVillageProp] {
        guard band >= 0 else { return [] }
        let base = Double(band) * Self.spacing
        let wanted = 3 + Int(Self.noise(band, 10) * 3)
        var props: [TRVillageProp] = []
        for attempt in 0..<16 where props.count < wanted {
            let roll = Self.noise(band, 100 + attempt * 7)
            let kind: TRVillageProp.Kind = switch roll {
            case ..<0.32: .tree
            case ..<0.5: .pine
            case ..<0.64: .bush
            case ..<0.84: .flowers
            case ..<0.92: .rock
            default: .pond
            }
            if kind == .pond, props.contains(where: { $0.kind == .pond }) { continue }
            let range: (Double, Double) = switch kind {
            case .tree, .pine: (0.7, 1.0)
            case .bush: (0.8, 1.15)
            case .flowers: (0.9, 1.3)
            case .rock: (0.7, 1.2)
            case .pond: (0.75, 1.0)
            }
            let prop = TRVillageProp(
                kind: kind,
                x: 34 + 322 * Self.noise(band, 101 + attempt * 7),
                y: base + 6 + 68 * Self.noise(band, 102 + attempt * 7),
                scale: range.0 + (range.1 - range.0) * Self.noise(band, 103 + attempt * 7),
                seed: Self.noise(band, 104 + attempt * 7)
            )
            if fits(prop, band: band, among: props) { props.append(prop) }
        }
        return props
    }

    private func fits(_ prop: TRVillageProp, band: Int, among others: [TRVillageProp]) -> Bool {
        let reach = prop.reach
        // On the lawn, a pond well in from the edge.
        let inset = prop.kind == .pond ? reach + 20 : 34
        guard prop.x >= inset, prop.x <= 390 - inset else { return false }
        // Off the road and its curb, checked along the stretch it covers.
        let clearance = reach + 13
        for dy in [-reach * 0.5, 0, reach * 0.5] {
            let x = Self.roadPoint(prop.y + dy, offset: 0).x
            if abs(prop.x - x) < clearance { return false }
        }
        // Not standing in front of a house, nor right behind it; a pond, lying
        // flat, further off behind.
        let behind = prop.kind == .pond ? 40.0 : 16
        for level in max(band - 1, 0)...(band + 1) where level <= levelCount {
            let dx = prop.x - Self.houseX(level), dy = prop.y - Self.houseY(level)
            if abs(dx) < 30 + reach, dy > -46 - reach * 0.5, dy < behind { return false }
        }
        // Clear of the signposts at this bend and the next.
        for sign in [band, band + 1] where hasSign(atBand: sign) {
            let dy = prop.y - (Double(sign) * Self.spacing + 2)
            if abs(prop.x - Self.centerX) < 18 + reach, dy > -40, dy < 24 { return false }
        }
        // And of each other.
        return others.allSatisfy { other in
            let gap = reach + other.reach
            let dx = (prop.x - other.x) / gap, dy = (prop.y - other.y) / (gap * 0.8)
            return dx * dx + dy * dy >= 1
        }
    }

    /// The signpost at a band's bend: the next chapter's name, or "Soon" past
    /// the last house.
    func signLabel(atBand band: Int) -> String? {
        if band > 0, band % Self.levelsPerChapter == 0, band < levelCount {
            return "Ch \(band / Self.levelsPerChapter + 1)"
        }
        return band == levelCount + 1 ? "Soon" : nil
    }

    private func hasSign(atBand band: Int) -> Bool { signLabel(atBand: band) != nil }
}
