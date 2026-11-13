import SwiftUI

/// The level select page as a little village, after the "B2 · Village level picker"
/// design: a road snakes away up a tilted lawn with a house by it for each level,
/// numbered plaques over them, a teal banner up top naming the chapter, and a
/// button below to play the house the van is parked at.
///
/// Dragging drives the van along the road, which settles at the nearest house when
/// let go; tapping a plaque drives to that house, and tapping the van's own house
/// plays it. Coming back after unlocking a level, the van drives on to the new one.
struct TRVillageLevelMapView: View {
    let levels: [MultiVanLevel]
    let progressService: ProgressService
    let coinTotal: Int
    let onLevelSelected: (String) -> Void
    let onSettingsTapped: () -> Void
    let onCoinsTapped: () -> Void

    var body: some View {
        // Read once here, so dragging the map doesn't reread the save file.
        let snapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)
        let houses = levels.enumerated().map { index, level in
            TRVillageHouse(levelID: level.id, state: snapshot.tileState(at: index, levelID: level.id), stars: snapshot.stars(for: level.id))
        }
        if !houses.isEmpty {
            TRVillagePage(
                houses: houses,
                currentLevel: min(snapshot.firstIncompleteIndex, houses.count - 1) + 1,
                coinTotal: coinTotal,
                onLevelSelected: onLevelSelected,
                onSettingsTapped: onSettingsTapped,
                onCoinsTapped: onCoinsTapped
            )
        }
    }
}

struct TRVillageHouse: Equatable {
    let levelID: String
    let state: TRLevelTileState
    let stars: Int
}

private struct TRVillagePage: View {
    let houses: [TRVillageHouse]
    let currentLevel: Int
    let coinTotal: Int
    let onLevelSelected: (String) -> Void
    let onSettingsTapped: () -> Void
    let onCoinsTapped: () -> Void

    /// The ground follows the finger: pulling down draws the road in and drives
    /// the van on, like scrolling. Make this -1 for the design's finger-up drive.
    private static let dragDirection = 1.0
    private static let vanLevelKey = "levelMap.vanLevelID"

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @State private var power = MultiVanPowerMonitor()
    @State private var motion: TRVillageMotion
    /// The level the van was last parked at, so it can drive on from there.
    @State private var startLevel: Int
    @State private var isMoving = false
    @State private var lastDragY: CGFloat?
    /// Where the finger has dragged the camera to, before it gives way past an end.
    @State private var dragCamera = 0.0
    @State private var settle: Task<Void, Never>?
    /// The level the van last drove to, shared with the other maps.
    @AppStorage(Self.vanLevelKey) private var vanLevelID = ""

    init(
        houses: [TRVillageHouse],
        currentLevel: Int,
        coinTotal: Int,
        onLevelSelected: @escaping (String) -> Void,
        onSettingsTapped: @escaping () -> Void,
        onCoinsTapped: @escaping () -> Void
    ) {
        self.houses = houses
        self.currentLevel = currentLevel
        self.coinTotal = coinTotal
        self.onLevelSelected = onLevelSelected
        self.onSettingsTapped = onSettingsTapped
        self.onCoinsTapped = onCoinsTapped
        let road = TRVillageRoad(levelCount: houses.count, currentLevel: currentLevel)
        let lastID = UserDefaults.standard.string(forKey: Self.vanLevelKey)
        let last = houses.firstIndex { $0.levelID == lastID && $0.state != .locked }.map { $0 + 1 }
        let start = min(last ?? currentLevel, road.currentLevel)
        _startLevel = State(initialValue: start)
        _motion = State(initialValue: TRVillageMotion(camera: road.camera(forLevel: start)))
    }

    private var road: TRVillageRoad { TRVillageRoad(levelCount: houses.count, currentLevel: currentLevel) }

    private var totalStars: Int { houses.reduce(0) { $0 + $1.stars } }

    /// Whether the village keeps up its smoke, swaying trees and drifting clouds
    /// while the van is parked: not with Reduce Motion, in Low Power Mode or
    /// while the app is away.
    private var isIdling: Bool { !reduceMotion && !power.isLowPowerModeEnabled && scenePhase == .active }

    var body: some View {
        let road = road
        GeometryReader { geometry in
            let size = geometry.size
            let board = TRVillageBoard(width: size.width, height: size.height)
            let lens = TRVillageLens(width: size.width, boardTop: board.top, lip: board.lip)
            // Full rate while the van moves; a gentler rate for the village idling.
            TimelineView(.animation(minimumInterval: isMoving ? nil : 1.0 / 30, paused: !isMoving && !isIdling)) { timeline in
                let time = timeline.date.timeIntervalSinceReferenceDate
                // The village's own motion, held still under Reduce Motion.
                let ambient = reduceMotion ? 0.5 : time.truncatingRemainder(dividingBy: 3600)
                let camera = motion.camera(at: time)
                let selected = road.selectedLevel(camera: camera)
                ZStack(alignment: .topLeading) {
                    Canvas { context, _ in TRVillageArt.drawBackdrop(context, board: board, time: ambient) }
                        .accessibilityHidden(true)

                    TRVillageWorld(
                        road: road, lens: lens, board: board, houses: houses,
                        camera: camera, selected: selected, motion: motion, time: time, ambient: ambient,
                        onPlaqueTapped: { level in tapPlaque(level, selected: selected) }
                    )

                    Canvas { context, _ in TRVillageArt.drawLowClouds(context, board: board, time: ambient) }
                        .allowsHitTesting(false)
                        .accessibilityHidden(true)

                    // Leaves, birds and the like: only while the village is idling, as
                    // frozen mid-air they'd look stuck.
                    if isIdling {
                        Canvas { context, _ in TRVillageArt.drawAir(context, board: board, camera: camera, time: ambient) }
                            .allowsHitTesting(false)
                            .accessibilityHidden(true)
                    }

                    MultiVanHUDBanner()
                        .frame(width: size.width, height: geometry.safeAreaInsets.top + TRVillageBoard.bannerEdge + 14)
                        .offset(y: -geometry.safeAreaInsets.top)

                    header(chapter: TRVillageRoad.chapter(ofLevel: selected), chapterCount: road.chapterCount)
                        .padding(.horizontal, 16)
                        .padding(.top, 4)
                        .frame(width: size.width)

                    chapterSwitcher(selected: selected)
                        .frame(width: size.width)
                        .position(x: size.width / 2, y: board.lip + 66)

                    playButton(level: selected)
                        .position(x: size.width / 2, y: board.lip + 113)
                }
            }
            .contentShape(Rectangle())
            .gesture(drag(road: road, lens: lens))
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Level map")
        .accessibilityScrollAction { edge in
            let selected = road.selectedLevel(camera: motion.target)
            drive(to: selected + (edge == .top || edge == .leading ? 1 : -1))
        }
        .task { await driveOn() }
        .task { await power.monitor() }
        .onDisappear { settle?.cancel() }
    }

    // MARK: - Chrome

    private func header(chapter: Int, chapterCount: Int) -> some View {
        HStack(spacing: 8) {
            VStack(alignment: .leading, spacing: 1) {
                Text("Chapter \(chapter) of \(chapterCount)".uppercased())
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .tracking(1)
                    .foregroundStyle(TRVillagePalette.mint)
                Text(TRVillageRoad.chapterName(chapter))
                    .font(.system(size: 25, weight: .bold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.cream)
                    .shadow(color: TRVillagePalette.ink.opacity(0.55), radius: 0, x: 0, y: 2)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            }
            .accessibilityElement(children: .combine)
            .accessibilityAddTraits(.isHeader)

            Spacer(minLength: 4)

            HStack(spacing: 6) {
                TRVillagePill {
                    Image(systemName: "star.fill").foregroundStyle(TRVillagePalette.gold)
                    Text("\(totalStars)")
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(Text(totalStars == 1 ? "1 star" : "\(totalStars) stars"))

                Button(action: onCoinsTapped) {
                    TRVillagePill {
                        TRVillageCoin()
                        Text(coinTotal.formatted())
                    }
                }
                .buttonStyle(TRVillagePressStyle())
                .accessibilityLabel(Text("\(coinTotal) coins"))
                .accessibilityHint("Opens the shop")

                Button(action: onSettingsTapped) {
                    Image(systemName: "gearshape")
                        .font(.system(size: 19, weight: .semibold))
                        .foregroundStyle(TRVillagePalette.navy)
                        .frame(width: 44, height: 44)
                }
                .buttonStyle(.multiVanHUDCircle)
                .accessibilityLabel("Settings")
            }
        }
    }

    private func chapterSwitcher(selected: Int) -> some View {
        let chapter = TRVillageRoad.chapter(ofLevel: selected)
        let reached = TRVillageRoad.chapter(ofLevel: currentLevel)
        let canGoBack = chapter > 1
        let canGoOn = TRVillageRoad.firstLevel(ofChapter: chapter + 1) <= currentLevel
        return HStack(spacing: 14) {
            chapterArrow("chevron.left", label: "Previous chapter", isEnabled: canGoBack) {
                drive(to: TRVillageRoad.firstLevel(ofChapter: chapter - 1))
            }
            HStack(spacing: 7) {
                ForEach(1...road.chapterCount, id: \.self) { index in
                    Capsule()
                        .fill(index == chapter ? TRVillagePalette.teal : (index <= reached ? Color(hex: 0x6BB361) : Color(hex: 0xB8D3DA)))
                        .frame(width: index == chapter ? 22 : 8, height: 8)
                }
            }
            .animation(.easeOut(duration: 0.2), value: chapter)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(Text("Chapter \(chapter) of \(road.chapterCount)"))
            chapterArrow("chevron.right", label: "Next chapter", isEnabled: canGoOn) {
                drive(to: TRVillageRoad.firstLevel(ofChapter: chapter + 1))
            }
        }
    }

    private func chapterArrow(_ symbol: String, label: String, isEnabled: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(TRVillagePalette.teal)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(TRVillagePressStyle())
        .disabled(!isEnabled)
        .opacity(isEnabled ? 1 : 0.35)
        .accessibilityLabel(label)
    }

    /// Plays the house the van is parked at: a new delivery, or a replay.
    private func playButton(level: Int) -> some View {
        let isNew = houses[level - 1].state != .completed
        return Button { play(level) } label: {
            HStack(spacing: 10) {
                Image(systemName: isNew ? "shippingbox" : "arrow.counterclockwise")
                    .font(.system(size: 18, weight: .semibold))
                Text(isNew ? "Deliver to No. \(level)" : "Replay No. \(level)")
                    .font(.system(size: 18, weight: .semibold, design: .rounded))
                    .monospacedDigit()
            }
            .padding(.horizontal, 30)
            .frame(height: 50)
        }
        .buttonStyle(MultiVanHUDButtonStyle(isProminent: true, tint: TRVillagePalette.blue))
    }

    // MARK: - Driving

    private func drag(road: TRVillageRoad, lens: TRVillageLens) -> some Gesture {
        DragGesture(minimumDistance: 6)
            .onChanged { value in
                let now = Date.timeIntervalSinceReferenceDate
                if lastDragY == nil {
                    // Catch a drive, or a bounce back from an end, where it has got to.
                    settle?.cancel()
                    let shown = motion.camera(at: now)
                    motion.hold(at: shown)
                    dragCamera = road.unbanded(shown)
                    isMoving = true
                }
                let dy = value.translation.height - (lastDragY ?? 0)
                lastDragY = value.translation.height
                dragCamera += Self.dragDirection * dy / lens.pointsPerUnit(atScreenY: value.location.y)
                motion.hold(at: road.rubberBanded(dragCamera))
            }
            .onEnded { value in
                lastDragY = nil
                let now = Date.timeIntervalSinceReferenceDate
                let camera = motion.camera(at: now)
                // Past an end the camera moves slower than the finger; so, then, does its let-go.
                let velocity = Self.dragDirection * value.velocity.height / lens.pointsPerUnit(atScreenY: value.location.y) * road.give(at: dragCamera)
                let target = road.restingCamera(from: camera, velocity: velocity)
                if reduceMotion {
                    motion.ease(to: target, at: now, duration: 0.2)
                    run(for: 0.2)
                } else {
                    motion.spring(to: target, velocity: min(max(velocity, -3000), 3000), at: now)
                    run(for: TRVillageMotion.springDuration)
                }
            }
    }

    /// Drives the van along the road to `level`'s house.
    private func drive(to level: Int) {
        let road = road
        let level = min(max(level, 1), road.currentLevel)
        let now = Date.timeIntervalSinceReferenceDate
        let target = road.camera(forLevel: level)
        let distance = abs(target - motion.camera(at: now)) / TRVillageRoad.spacing
        let duration = reduceMotion ? 0 : min(1.7, 0.45 + distance * 0.12)
        motion.ease(to: target, at: now, duration: duration)
        run(for: duration)
    }

    /// Draws frames for `duration`, then stops once the van has come to rest.
    private func run(for duration: TimeInterval) {
        settle?.cancel()
        guard duration > 0 else {
            motion.hold(at: motion.target)
            isMoving = false
            motion.park()
            return
        }
        isMoving = true
        settle = Task {
            do { try await Task.sleep(for: .seconds(duration + 0.05)) } catch { return }
            // However far the frames got, the van ends at its stop.
            motion.hold(at: motion.target)
            motion.park()
            isMoving = false
        }
    }

    private func tapPlaque(_ level: Int, selected: Int) {
        guard houses[level - 1].state != .locked else { return }
        if level == selected, !isMoving {
            play(level)
        } else {
            drive(to: level)
        }
    }

    private func play(_ level: Int) {
        let levelID = houses[level - 1].levelID
        vanLevelID = levelID
        onLevelSelected(levelID)
    }

    /// Back from a level that opened a new one, the van drives on to it.
    private func driveOn() async {
        let current = road.currentLevel
        vanLevelID = houses[current - 1].levelID
        guard startLevel < current else { return }
        startLevel = current
        // A beat after the page appears.
        do { try await Task.sleep(for: .seconds(0.6)) } catch { return }
        drive(to: current)
    }
}

// MARK: - The world

/// The road, lawn, houses and van, clipped to the board, with the level plaques
/// floating over them.
private struct TRVillageWorld: View {
    let road: TRVillageRoad
    let lens: TRVillageLens
    let board: TRVillageBoard
    let houses: [TRVillageHouse]
    let camera: Double
    let selected: Int
    let motion: TRVillageMotion
    let time: TimeInterval
    /// The clock the village's smoke, trees and van idle by.
    let ambient: Double
    let onPlaqueTapped: (Int) -> Void

    private typealias Road = TRVillageRoad

    var body: some View {
        let van = vanPose()
        ZStack(alignment: .topLeading) {
            Canvas { context, _ in draw(context, van: van) }
                .clipShape(TRVillageBoardShape(board: board))
                .allowsHitTesting(false)
                .accessibilityHidden(true)

            ForEach(plaques(), id: \.level) { plaque in
                Button { onPlaqueTapped(plaque.level) } label: {
                    TRVillagePlaque(level: plaque.level, house: houses[plaque.level - 1], isSelected: plaque.level == selected, time: ambient)
                }
                .buttonStyle(TRVillagePressStyle())
                .disabled(houses[plaque.level - 1].state == .locked)
                .opacity(plaque.opacity)
                .allowsHitTesting(plaque.opacity > 0.5)
                .accessibilityHidden(plaque.opacity < 0.05)
                .accessibilityLabel(Text("Level \(plaque.level)"))
                .accessibilityValue(Text(TRLevelTile.accessibilityValue(state: houses[plaque.level - 1].state, stars: houses[plaque.level - 1].stars)))
                .position(plaque.center)
            }

            TRVillageDriveChip(isReversing: van.isReversing)
                .opacity(van.chip)
                .position(van.chipCenter)
                .allowsHitTesting(false)
                .accessibilityHidden(true)
        }
    }

    // MARK: Layout

    private struct Plaque {
        let level: Int
        let center: CGPoint
        let opacity: Double
    }

    private var visibleBands: ClosedRange<Int> {
        let low = max(0, Int(((camera - 120) / Road.spacing).rounded(.down)))
        let high = max(low, Int(((camera + 860) / Road.spacing).rounded(.up)))
        return low...high
    }

    /// Nearer plaques last, to stand in front.
    private func plaques() -> [Plaque] {
        let bands = visibleBands
        let first = max(1, bands.lowerBound), last = min(houses.count, bands.upperBound)
        guard first <= last else { return [] }
        return (first...last).reversed().map { level in
            let p = lens.project(x: Road.houseX(level), y: Road.houseY(level), camera: camera)
            let size: Double = houses[level - 1].state == .current ? 54 : 44
            let top = p.point.y - 44 * p.scale * lens.scaleX - 8 - size
            let opacity = clamp((p.depth + 10) / 30) * clamp((640 - p.depth) / 120) * clamp((top - TRVillageBoard.bannerEdge) / 20)
            return Plaque(level: level, center: CGPoint(x: p.point.x, y: top + size / 2), opacity: opacity)
        }
    }

    private struct VanPose {
        let y: Double
        let rotation: Double
        let flip: Double
        let spin: Double
        let speed: Double
        let isReversing: Bool
        /// How much of the Drive chip and exhaust shows.
        let chip: Double
        let chipCenter: CGPoint
    }

    private func vanPose() -> VanPose {
        let y = road.vanY(camera: camera)
        motion.noteVan(atY: y, time: time)
        let here = lens.project(x: Road.roadX(y), y: y, camera: camera)
        let ahead = lens.project(x: Road.roadX(y + 1), y: y + 1, camera: camera)
        let dx = ahead.point.x - here.point.x, dy = ahead.point.y - here.point.y
        let facing: Double = dx >= 0 ? 1 : -1
        let ratio = min(1, abs(dx) / max(0.001, abs(dy) * 1.4))
        let rotation = min(max(atan2(dy, abs(dx)) * 180 / .pi, -22), 22) * facing
        let speed = motion.vanSpeed
        let scale = here.scale * 0.95 * lens.scaleX
        return VanPose(
            y: y,
            rotation: rotation,
            flip: facing * (0.42 + 0.58 * ratio),
            spin: (road.arcLength(atY: y) * 14).truncatingRemainder(dividingBy: 360),
            speed: speed,
            isReversing: motion.isReversing,
            chip: motion.chip,
            chipCenter: CGPoint(x: here.point.x, y: here.point.y - 26 * scale - 19)
        )
    }

    private func fade(_ depth: Double) -> Double { clamp((depth + 50) / 40) * clamp((800 - depth) / 140) }

    // MARK: Drawing

    private func draw(_ context: GraphicsContext, van: VanPose) {
        let near = max(-6, camera - 90), far = camera + 830
        drawLawnFlecks(context, near: near, far: far)
        context.fill(roadBand(near, far, halfWidth: 11), with: .color(Color(hex: 0xEFE6D2)))
        context.fill(roadBand(near, far, halfWidth: 7.5), with: .color(Color(hex: 0x626779)))
        // The centre line is painted only as far as the van has been.
        let painted = centreLine(max(0, near), min(far, Double(road.currentLevel) * Road.spacing))
        context.fill(painted, with: .color(.white.opacity(0.8)))

        // Far to near, so nearer things stand in front; the van among them, so
        // trees can pass in front of it.
        for (_, x, y, kind) in pieces(vanY: van.y).sorted(by: { $0.key > $1.key }) {
            draw(context, kind, x: x, y: y, van: van)
        }

        // Haze over the far edge.
        let haze = Color(red: 214 / 255, green: 236 / 255, blue: 206 / 255)
        context.fill(
            Path(CGRect(x: 0, y: board.aboveY(140), width: 390 * board.scaleX, height: 120)),
            with: .linearGradient(
                Gradient(colors: [haze.opacity(0.95), haze.opacity(0)]),
                startPoint: CGPoint(x: 0, y: board.aboveY(140)),
                endPoint: CGPoint(x: 0, y: board.aboveY(260))
            )
        )
    }

    private enum Piece {
        /// Level 0 is the depot.
        case house(Int)
        case sign(String)
        case prop(TRVillageProp)
        case van
    }

    /// What stands along the stretch of road in view, keyed by how far along it.
    private func pieces(vanY: Double) -> [(key: Double, x: Double, y: Double, kind: Piece)] {
        var pieces: [(key: Double, x: Double, y: Double, kind: Piece)] = []
        for band in visibleBands {
            let y = Double(band) * Road.spacing
            if band <= houses.count {
                let houseY = Road.houseY(band)
                pieces.append((houseY, Road.houseX(band), houseY, .house(band)))
            }
            // Past the last house, the road runs on to levels still to come.
            if let label = road.signLabel(atBand: band) {
                pieces.append((y + 2, Road.centerX, y + 2, .sign(label)))
            }
            for prop in road.props(inBand: band) {
                // Ponds lie flat, under whatever stands about them.
                pieces.append((prop.y + (prop.kind == .pond ? 12 : 0), prop.x, prop.y, .prop(prop)))
            }
        }
        pieces.append((vanY - 0.5, Road.roadX(vanY), vanY - 0.5, .van))
        return pieces
    }

    private func draw(_ context: GraphicsContext, _ kind: Piece, x: Double, y: Double, van: VanPose) {
        switch kind {
        case let .house(level):
            // Each house a little out of step with its neighbours.
            let time = ambient + Double(level) * 0.83
            piece(context, x: x, y: y, scale: level == 0 ? 1.1 : Road.houseScale(level), anchor: TRVillageArt.houseAnchor) { context in
                // Only the depot smokes: on the others a plaque would hide it.
                guard level > 0 else {
                    return TRVillageArt.drawHouse(context, roof: TRVillagePalette.teal, smoke: true, parcel: false, flag: true, wind: TRVillageArt.breeze(at: ambient, x: x), time: time)
                }
                let house = houses[level - 1]
                if house.state == .locked {
                    TRVillageArt.drawEmptyHouse(context)
                } else {
                    TRVillageArt.drawHouse(context, roof: TRVillagePalette.roofs[Road.roofIndex(level, of: TRVillagePalette.roofs.count)], smoke: false, parcel: house.state == .current, flag: false, time: time)
                }
            }
        case let .sign(label):
            piece(context, x: x, y: y, scale: 1, anchor: TRVillageArt.signAnchor) { TRVillageArt.drawSign($0, label: label) }
        case let .prop(prop):
            draw(context, prop)
        case .van:
            drawVan(context, van)
        }
    }

    private func draw(_ context: GraphicsContext, _ prop: TRVillageProp) {
        let green = TRVillagePalette.greens[Int(prop.seed * 4) % 4]
        // Leaning with the breeze, and tossing more the harder it blows.
        let wind = TRVillageArt.breeze(at: ambient, x: prop.x)
        let swing = 4 * wind + sin(ambient * 1.6 + prop.seed * 20) * (1 + 2.4 * wind)
        switch prop.kind {
        case .tree:
            piece(context, x: prop.x, y: prop.y, scale: prop.scale, anchor: TRVillageArt.treeAnchor, rotation: .degrees(swing)) {
                TRVillageArt.drawTree($0, color: green)
            }
        case .pine:
            piece(context, x: prop.x, y: prop.y, scale: prop.scale, anchor: TRVillageArt.treeAnchor, rotation: .degrees(swing * 0.6)) {
                TRVillageArt.drawPine($0, color: green)
            }
        case .bush:
            piece(context, x: prop.x, y: prop.y, scale: prop.scale, anchor: TRVillageArt.bushAnchor) {
                TRVillageArt.drawBush($0, color: green)
            }
        case .flowers:
            let nod = Angle.degrees(5 * wind + sin(ambient * 2 + prop.seed * 20) * (2 + 4 * wind))
            piece(context, x: prop.x, y: prop.y, scale: prop.scale, anchor: TRVillageArt.flowersAnchor, rotation: nod) {
                TRVillageArt.drawFlowers($0)
            }
        case .rock:
            piece(context, x: prop.x, y: prop.y, scale: prop.scale, anchor: TRVillageArt.rockAnchor) { TRVillageArt.drawRock($0) }
        case .pond:
            piece(context, x: prop.x, y: prop.y, scale: prop.scale, anchor: TRVillageArt.pondAnchor) {
                TRVillageArt.drawPond($0, time: ambient + prop.seed * 10)
            }
        }
    }

    private func piece(_ context: GraphicsContext, x: Double, y: Double, scale: Double, anchor: CGPoint, rotation: Angle = .zero, draw: (GraphicsContext) -> Void) {
        let p = lens.project(x: x, y: y, camera: camera)
        TRVillageArt.place(context, at: p.point, scale: p.scale * scale * lens.scaleX, anchor: anchor, rotation: rotation, opacity: fade(p.depth), draw: draw)
    }

    private func drawVan(_ context: GraphicsContext, _ van: VanPose) {
        let p = lens.project(x: Road.roadX(van.y), y: van.y - 0.5, camera: camera)
        let scale = p.scale * 0.95 * lens.scaleX
        var context = context
        context.translateBy(x: p.point.x, y: p.point.y - 0.8 * scale)
        context.rotate(by: .degrees(van.rotation))
        context.scaleBy(x: van.flip * scale, y: scale)
        context.translateBy(x: -TRVillageArt.vanPivot.x, y: -TRVillageArt.vanPivot.y)
        TRVillageArt.drawVan(
            context, spin: van.spin, puffs: van.isReversing ? 0 : van.chip * 0.8,
            idle: clamp(1 - abs(van.speed) / 40), time: ambient
        )
    }

    /// Grass flecks scattered over the lawn, clear of the road.
    private func drawLawnFlecks(_ context: GraphicsContext, near: Double, far: Double) {
        var dark = Path(), light = Path()
        let bands = visibleBands
        for band in (bands.lowerBound - 1)...(bands.upperBound + 1) {
            for j in 0..<10 {
                let x = 28 + 334 * hash(band, j)
                let y = Double(band) * Road.spacing + Road.spacing * hash(band, j + 17)
                guard abs(x - Road.roadX(y)) >= 18, y >= near, y <= far else { continue }
                let p = lens.project(x: x, y: y, camera: camera)
                let side = 2.2 * p.scale * lens.scaleX
                let fleck = CGRect(x: p.point.x, y: p.point.y, width: side, height: side)
                if j.isMultiple(of: 2) { light.addRect(fleck) } else { dark.addRect(fleck) }
            }
        }
        context.fill(dark, with: .color(Color(hex: 0x7FB85A, opacity: 0.75)))
        context.fill(light, with: .color(Color(hex: 0xA9DA7F)))
    }

    private func roadBand(_ near: Double, _ far: Double, halfWidth: Double) -> Path {
        var left: [CGPoint] = [], right: [CGPoint] = []
        var y = near
        while y <= far + 0.01 {
            left.append(project(Road.roadPoint(y, offset: -halfWidth)))
            right.append(project(Road.roadPoint(y, offset: halfWidth)))
            y += Road.sampleStep
        }
        guard left.count > 1 else { return Path() }
        var path = Path()
        path.addLines(left + right.reversed())
        path.closeSubpath()
        return path
    }

    /// Dashes 9 long every 18 along the road.
    private func centreLine(_ near: Double, _ far: Double) -> Path {
        var path = Path()
        guard far > near else { return path }
        let start = road.arcLength(atY: near), end = road.arcLength(atY: far)
        var s = (start / 18).rounded(.up) * 18
        while s + 9 <= end {
            let a = road.y(atArcLength: s), b = road.y(atArcLength: s + 9)
            path.addLines([
                project(Road.roadPoint(a, offset: -1)), project(Road.roadPoint(b, offset: -1)),
                project(Road.roadPoint(b, offset: 1)), project(Road.roadPoint(a, offset: 1)),
            ])
            path.closeSubpath()
            s += 18
        }
        return path
    }

    private func project(_ point: (x: Double, y: Double)) -> CGPoint {
        lens.project(x: point.x, y: point.y, camera: camera).point
    }

    private func hash(_ a: Int, _ b: Int) -> Double {
        let v = sin(Double(a) * 127.1 + Double(b) * 311.7) * 43758.5453
        return v - v.rounded(.down)
    }
}

private func clamp(_ value: Double) -> Double { min(max(value, 0), 1) }

// MARK: - Pieces of chrome

/// A level's number on a plaque over its house: cream with its stars once done,
/// big and blue for the next delivery, dashed and locked beyond.
private struct TRVillagePlaque: View {
    let level: Int
    let house: TRVillageHouse
    let isSelected: Bool
    /// Bobs the next delivery's plaque and pulses its halo.
    let time: Double

    var body: some View {
        switch house.state {
        case .completed:
            VStack(spacing: 0) {
                Text("\(level)")
                    .font(.system(size: 15, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.navy)
                HStack(spacing: 1) {
                    ForEach(0..<3, id: \.self) { index in
                        Image(systemName: "star.fill")
                            .font(.system(size: 6.5, weight: .bold))
                            .foregroundStyle(index < house.stars ? TRVillagePalette.gold : TRVillagePalette.creamLip)
                    }
                }
            }
            .frame(width: 44, height: 44)
            .background {
                Circle()
                    .fill(LinearGradient(colors: [TRVillagePalette.cream, TRVillagePalette.creamDeep], startPoint: .top, endPoint: .bottom))
                    .overlay { Circle().strokeBorder(.white, lineWidth: 1.5) }
                    .background { Circle().fill(TRVillagePalette.creamLip).offset(y: 3) }
                    .shadow(color: TRVillagePalette.ink.opacity(0.3), radius: 5, x: 0, y: 6)
            }
            .overlay {
                if isSelected {
                    Circle().strokeBorder(TRVillagePalette.blue, lineWidth: 4).padding(-4)
                }
            }

        case .current:
            let pulse = (sin(time * 2.4) + 1) / 2
            Text("\(level)")
                .font(.system(size: 21, weight: .bold, design: .rounded))
                .foregroundStyle(.white)
                .frame(width: 54, height: 54)
                .background {
                    Circle()
                        .fill(TRVillagePalette.blue)
                        .overlay { Circle().strokeBorder(.white, lineWidth: 2.5) }
                        .background { Circle().fill(TRVillagePalette.blueDark).offset(y: 4) }
                        .background { Circle().fill(.white.opacity(0.55 - 0.2 * pulse)).padding(-5 - 3 * pulse) }
                        .shadow(color: TRVillagePalette.blue.opacity(0.55), radius: 9, x: 0, y: 10)
                }
                .offset(y: -2 * pulse)

        case .locked:
            VStack(spacing: 0) {
                Text("\(level)")
                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                Image(systemName: "lock.fill")
                    .font(.system(size: 8, weight: .bold))
            }
            .foregroundStyle(TRVillagePalette.slate)
            .frame(width: 44, height: 44)
            .background {
                Circle()
                    .fill(TRVillagePalette.cream.opacity(0.72))
                    .overlay { Circle().strokeBorder(Color(hex: 0x8E9DB3), style: StrokeStyle(lineWidth: 1.5, dash: [3.5, 2.5])) }
            }
        }
    }
}

/// The chip over the van while it drives: on to a delivery, or back for a replay.
private struct TRVillageDriveChip: View {
    let isReversing: Bool

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: isReversing ? "backward.fill" : "forward.fill")
                .font(.system(size: 9, weight: .bold))
            Text(isReversing ? "Replay" : "Drive")
                .font(.system(size: 11, weight: .semibold, design: .rounded))
                .tracking(0.4)
        }
        .foregroundStyle(TRVillagePalette.cream)
        .padding(.leading, 7)
        .padding(.trailing, 9)
        .frame(height: 22)
        .background {
            Capsule()
                .fill(TRVillagePalette.teal)
                .background { Capsule().fill(TRVillagePalette.tealDark).offset(y: 2) }
        }
        .fixedSize()
    }
}

#Preview("Village level map") {
    ZStack {
        TRVillageSky()
        TRVillageLevelMapView(
            levels: (try? MultiVanLevelRepository().loadAllLevels()) ?? [],
            progressService: ProgressService(),
            coinTotal: 1_250,
            onLevelSelected: { _ in },
            onSettingsTapped: {},
            onCoinsTapped: {}
        )
    }
}
