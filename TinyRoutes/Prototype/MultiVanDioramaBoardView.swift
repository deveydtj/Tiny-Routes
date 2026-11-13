import SwiftUI

/// The 3D diorama board. It takes the same inputs as `MultiVanBoardView`, so the
/// switcher can swap one for the other without the gameplay screen changing.
/// The scene plays the same feedback models' tokens in 3D; only the score label
/// stays in SwiftUI, where its text stays sharp through the depth of field.
struct MultiVanDioramaBoardView: View {
    let engine: MultiVanEngine
    var onEventsProduced: (() -> Void)? = nil
    var celebration = MultiVanCelebration()
    var reducesExtraAnimations = false
    var personality = MultiVanPersonality()
    var onDeliveryEffectCompleted: (UUID) -> Void = { _ in }
    var crashEffects = MultiVanCrashEffects()
    var switchFeedback = MultiVanSwitchFeedback()
    var onCrashEffectCompleted: (UUID) -> Void = { _ in }
    /// Strips along the top and bottom that the screen's floating cards cover;
    /// the table is framed between them.
    var covered = MultiVanDioramaCamera.Covered()
    /// Rounds the board into a window; a full-screen board passes 0.
    var cornerRadius: CGFloat = 20
    /// Whether the table tilts up out of the flat board or lies down into it.
    var morph = MultiVanBoardMorph.none
    /// Points between the flat board and the view's sides, so the overhead view
    /// lays the lawn where the flat board drew it.
    var flatSideInset: CGFloat = 0
    /// Pieces a tutorial tip is about, ringed under the switches.
    var spotlightNodeIDs: [String] = []
    var onMissedTap: (() -> Void)? = nil
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.multiVanDioramaPreload) private var preload
    @Environment(\.multiVanCosmetics) private var cosmetics
    /// Where the player left the table, and the drag or pinch still under their fingers.
    @State private var orbit = MultiVanDioramaOrbit.resting
    @GestureState private var dragTranslation = CGSize.zero
    @GestureState private var pinch: Pinch?
    /// A pinch's fingers also drag; that drag doesn't turn the table.
    @State private var dragIsPinch = false

    private struct Pinch: Equatable {
        let magnification: CGFloat
        let anchor: CGPoint
    }
    @State private var framing: Framing?
    /// How far the camera has come down to the flat board's overhead view: 1 is
    /// straight down, 0 is the table. Nil until the morph first sets it.
    @State private var flatness: Double?

    /// How long the table takes to lie down before the flat board replaces it.
    static let foldDuration = 0.55
    /// The flat board fades out over the overhead view first, then the table tilts up.
    private static let unfoldDelay = 0.2
    private static let unfoldDuration = 1.1

    /// The camera fitted to the board at the resting angle, and looking straight
    /// down over the flat board. Fitting is a search, so it runs when the size
    /// changes rather than on every engine frame.
    private struct Framing: Equatable {
        let view: FramedView
        let camera: MultiVanDioramaCamera
        let overhead: MultiVanDioramaCamera

        init(_ view: FramedView) {
            self.view = view
            camera = .framed(in: view.size, covered: view.covered)
            overhead = .overhead(
                in: view.size, covered: view.covered,
                sideInset: Double(view.flatSideInset), edgeInset: Double(MultiVanSwitchButton.hitSize / 2)
            )
        }
    }

    private struct FramedView: Equatable {
        let size: CGSize
        let covered: MultiVanDioramaCamera.Covered
        let flatSideInset: CGFloat
    }

    var body: some View {
        // Read observable values here, as the flat board does, so every engine
        // change reaches the scene through `updateUIView` on the main actor.
        let state = MultiVanDioramaFrame(
            engine: engine, systemReduceMotion: reduceMotion, reducesExtraAnimations: reducesExtraAnimations
        )
        let cues = MultiVanDioramaCues(
            engine: engine, celebration: celebration, personality: personality,
            crashEffects: crashEffects, switchFeedback: switchFeedback
        )
        let card = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        GeometryReader { geometry in
            let size = geometry.size
            let view = FramedView(size: size, covered: covered, flatSideInset: flatSideInset)
            let fitted = framing.flatMap { $0.view == view ? $0 : nil } ?? Framing(view)
            let live = pinch.map { orbit.pinched(by: $0.magnification, anchor: $0.anchor, in: size) } ?? orbit
            MultiVanDioramaFlattening(flatness: flatness ?? (morph == .fromFlat && state.animates ? 1 : 0)) { flatness in
                MultiVanDioramaOrbiting(orbit: live.dragged(by: dragIsPinch ? .zero : dragTranslation)) { orbit in
                    let camera = fitted.camera.orbited(orbit)
                    table(state: state, cues: cues, camera: flatness > 0 ? camera.blended(to: fitted.overhead, by: flatness) : camera, size: size)
                }
            }
            .onChange(of: view, initial: true) { _, view in
                framing = Framing(view)
            }
        }
        .onChange(of: morph, initial: true) { _, morph in
            let lyingDown = morph == .toFlat
            let animation: Animation? = !state.animates ? nil
                : lyingDown ? .easeInOut(duration: Self.foldDuration)
                : .smooth(duration: Self.unfoldDuration).delay(Self.unfoldDelay)
            withAnimation(animation) { flatness = lyingDown ? 1 : 0 }
        }
        // The scene paints its own sky, so the board reads as a window onto the
        // table, or fills the screen; nothing outside it takes taps.
        .clipShape(card)
        .contentShape(card)
        // The flat board's puff hands its impact back when it ends; the scene's
        // puff can't, so the board does, after the same time.
        .task(id: crashEffects.impact?.id) {
            guard let id = crashEffects.impact?.id else { return }
            do { try await Task.sleep(for: .seconds(MultiVanCrashEffects.impactDuration)) }
            catch { return }
            guard !Task.isCancelled else { return }
            onCrashEffectCompleted(id)
        }
    }

    private func table(
        state: MultiVanDioramaFrame, cues: MultiVanDioramaCues, camera: MultiVanDioramaCamera, size: CGSize
    ) -> some View {
        let animates = state.animates
        return ZStack(alignment: .topLeading) {
            MultiVanDioramaSceneView(level: engine.level, state: state, cues: cues, camera: camera, preload: preload, cosmetics: cosmetics)
                .accessibilityHidden(true)
            // Drags anywhere off a switch turn the table, pinches zoom it, and a
            // double tap straightens it.
            Color.clear
                .contentShape(Rectangle())
                .gesture(
                    DragGesture(minimumDistance: 7)
                        .updating($dragTranslation) { value, translation, _ in translation = value.translation }
                        .onEnded { value in
                            if !dragIsPinch { orbit = orbit.dragged(by: value.translation) }
                            dragIsPinch = false
                        }
                        .simultaneously(with:
                            MagnifyGesture()
                                .updating($pinch) { value, pinch, _ in
                                    pinch = Pinch(magnification: value.magnification, anchor: CGPoint(x: value.startAnchor.x, y: value.startAnchor.y))
                                }
                                .onChanged { _ in dragIsPinch = true }
                                .onEnded { value in
                                    orbit = orbit.pinched(
                                        by: value.magnification, anchor: CGPoint(x: value.startAnchor.x, y: value.startAnchor.y), in: size
                                    )
                                    if dragTranslation == .zero { dragIsPinch = false }
                                }
                        )
                )
                .simultaneousGesture(
                    TapGesture(count: 2).exclusively(before: TapGesture())
                        .onEnded { tap in
                            switch tap {
                            case .first:
                                if orbit == .resting {
                                    onMissedTap?()
                                } else {
                                    withAnimation(animates ? .smooth(duration: 0.45) : nil) { orbit = .resting }
                                }
                            case .second:
                                onMissedTap?()
                            }
                        }
                )
                .accessibilityHidden(true)
            // VoiceOver finds the pieces the scene draws where it draws them.
            ForEach(Self.landmarks(engine: engine, graph: state.graph, camera: camera, size: size)) { landmark in
                Color.clear
                    .frame(width: Self.landmarkSize, height: Self.landmarkSize)
                    .accessibilityElement()
                    .accessibilityLabel(landmark.label)
                    .accessibilityValue(landmark.value)
                    .position(landmark.point)
                    .allowsHitTesting(false)
            }
            ForEach(spotlightNodeIDs, id: \.self) { nodeID in
                if let node = state.graph.nodesByID[nodeID],
                   let point = camera.viewPoint(for: MultiVanDioramaGeometry.switchPoint(node), in: size) {
                    MultiVanTutorialSpotlight(reduceMotion: !animates)
                        .position(point)
                }
            }
            // The scene draws the dials; the buttons over them take taps and speak.
            ForEach(Self.switchPlacements(controls: state.controls, graph: state.graph, camera: camera, size: size)) { placement in
                MultiVanSwitchButton(
                    control: placement.control, engine: engine,
                    onEventsProduced: onEventsProduced,
                    rejectionToken: switchFeedback.rejectionTokens[placement.control.nodeID],
                    animates: animates,
                    hitShape: placement.hitShape,
                    drawsDial: false,
                    previewOffset: MultiVanSwitchButton.previewOffset(at: placement.point, in: size, topInset: CGFloat(covered.top)),
                    projectPreviewAngle: { angle in
                        guard let node = state.graph.nodesByID[placement.id] else { return angle }
                        let tip = MultiVanDioramaGeometry.switchPoint(node) +
                            MultiVanDioramaGeometry.worldDirection(screenAngle: angle) * 0.22
                        guard let end = camera.viewPoint(for: tip, in: size) else { return angle }
                        return atan2(end.y - placement.point.y, end.x - placement.point.x)
                    }
                )
                .position(placement.point)
            }
            if animates {
                ForEach(Self.scoreLabels(deliveries: celebration.deliveries, engine: engine, graph: state.graph, camera: camera, size: size)) { label in
                    MultiVanDeliveryPopup(
                        delivery: label.delivery, side: Self.scoreLabelSide, showsParcel: false,
                        onComplete: { onDeliveryEffectCompleted(label.delivery.id) }
                    )
                    .position(label.point)
                }
            }
        }
    }

    /// A delivery's "+1" over its house, clear of the house's ✓.
    struct ScoreLabel: Identifiable {
        let delivery: MultiVanCelebration.Delivery
        let point: CGPoint
        var id: UUID { delivery.id }
    }

    private static let scoreLabelSide: CGFloat = 24
    private static let scoreLabelHeight = 1.2

    static func scoreLabels(
        deliveries: [MultiVanCelebration.Delivery], engine: MultiVanEngine, graph: RuntimeRouteGraph,
        camera: MultiVanDioramaCamera, size: CGSize
    ) -> [ScoreLabel] {
        guard !deliveries.isEmpty else { return [] }
        let houses = MultiVanDioramaLawn.Features(level: engine.level, graph: graph).houses
        return deliveries.compactMap { delivery in
            guard let house = houses.first(where: { $0.marking.nodeID == delivery.houseNodeID }),
                  let point = camera.viewPoint(
                    for: MultiVanDioramaGeometry.world(gridX: house.centre.x, gridY: house.centre.y, height: scoreLabelHeight), in: size
                  ) else { return nil }
            return ScoreLabel(delivery: delivery, point: point)
        }
    }

    /// What VoiceOver says about a house, van, roadblock, parcel or lamp, and
    /// where it points.
    struct Landmark: Identifiable {
        let id: String
        let label: String
        let value: String
        let point: CGPoint
    }

    private static let landmarkSize: CGFloat = 32

    /// The flat board's words for every house, van, roadblock, parcel and lamp, at
    /// the middle of each piece as `camera` sees it.
    static func landmarks(
        engine: MultiVanEngine, graph: RuntimeRouteGraph, camera: MultiVanDioramaCamera, size: CGSize
    ) -> [Landmark] {
        let features = MultiVanDioramaLawn.Features(level: engine.level, graph: graph)
        let vans = engine.vans
        let view = { (point: RoadPoint, height: Double) in
            camera.viewPoint(for: MultiVanDioramaGeometry.world(gridX: point.x, gridY: point.y, height: height), in: size)
        }
        let houses = features.houses.compactMap { house -> Landmark? in
            guard let point = view(house.centre, 0.35),
                  let authored = engine.level.houses.first(where: { $0.nodeID == house.marking.nodeID }) else { return nil }
            return Landmark(
                id: "house \(house.marking.nodeID)", label: MultiVanHouseView.accessibilityLabel(color: house.color),
                value: MultiVanHouseView.accessibilityValue(isDelivered: MultiVanBoardRules.isDelivered(authored, vans: vans, graph: graph)),
                point: point
            )
        }
        let vanLandmarks = vans.compactMap { van -> Landmark? in
            guard let point = view(van.position, 0.15) else { return nil }
            let isDelivered = engine.level.houses.contains { MultiVanBoardRules.isDelivered($0, vans: [van], graph: graph) }
            return Landmark(
                id: "van \(van.id)", label: MultiVanVanView.accessibilityLabel(color: van.color),
                value: MultiVanVanView.accessibilityValue(
                    color: van.color, status: van.status, isDelivered: isDelivered, cargo: engine.cargoStatus(forVanID: van.id)
                ),
                point: point
            )
        }
        let barriers = features.barriers.compactMap { barrier -> Landmark? in
            let standing = MultiVanDioramaGeometry.offset(barrier.point, along: barrier.heading, by: MultiVanDioramaGeometry.roadblockSetback)
            guard let point = view(standing, 0.15) else { return nil }
            return Landmark(id: "barrier \(barrier.nodeID)", label: MultiVanBarrierView.accessibilityLabel, value: "", point: point)
        }
        let parcels = MultiVanPickup.pickups(engine: engine).compactMap { pickup -> Landmark? in
            guard let point = view(pickup.point, 0.1) else { return nil }
            return Landmark(id: "parcel \(pickup.id)", label: pickup.accessibilityLabel, value: pickup.accessibilityValue, point: point)
        }
        let lamps = MultiVanSignalApproach.approaches(engine: engine).compactMap { approach -> Landmark? in
            guard let point = view(approach.postPoint, 0.3) else { return nil }
            return Landmark(
                id: "lamp \(approach.id)", label: MultiVanSignalLampView.accessibilityLabel(kind: approach.kind),
                value: MultiVanSignalLampView.accessibilityValue(kind: approach.kind, isOpen: approach.isOpen), point: point
            )
        }
        return houses + vanLandmarks + barriers + parcels + lamps
    }

    /// The switch buttons over their dials as `camera` sees them in a view of `size`.
    static func switchPlacements(
        controls: [MultiVanSwitchControl], graph: RuntimeRouteGraph, camera: MultiVanDioramaCamera, size: CGSize
    ) -> [MultiVanSwitchPlacement] {
        MultiVanSwitchPlacement.make(
            controls.compactMap { control in
                graph.nodesByID[control.nodeID]
                    .flatMap { camera.viewPoint(for: MultiVanDioramaGeometry.switchPoint($0), in: size) }
                    .map { (control, $0) }
            },
            bounds: CGRect(origin: .zero, size: size)
        )
    }
}

/// Hands its content each step of the morph SwiftUI animates through, so the
/// camera tilts between the table and the flat board's overhead view frame by frame.
private struct MultiVanDioramaFlattening<Content: View>: View, Animatable {
    var flatness: Double
    @ViewBuilder let content: (Double) -> Content

    var animatableData: Double {
        get { flatness }
        set { flatness = newValue }
    }

    var body: some View {
        content(flatness)
    }
}

/// Hands its content each orbit SwiftUI animates through, so straightening the
/// table turns and zooms the scene and moves its buttons together, frame by frame.
private struct MultiVanDioramaOrbiting<Content: View>: View, Animatable {
    var orbit: MultiVanDioramaOrbit
    @ViewBuilder let content: (MultiVanDioramaOrbit) -> Content

    var animatableData: AnimatablePair<AnimatablePair<Double, Double>, AnimatablePair<Double, AnimatablePair<Double, Double>>> {
        get {
            AnimatablePair(
                AnimatablePair(orbit.yaw, orbit.pitch),
                AnimatablePair(orbit.zoom, AnimatablePair(orbit.zoomCentre.x, orbit.zoomCentre.y))
            )
        }
        set {
            orbit = MultiVanDioramaOrbit(
                yaw: newValue.first.first, pitch: newValue.first.second, zoom: newValue.second.first,
                zoomCentre: SIMD2(newValue.second.second.first, newValue.second.second.second)
            )
        }
    }

    var body: some View {
        content(orbit)
    }
}

#if DEBUG
struct MultiVanDioramaBoardView_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            board(levelID: "level_014").previewDisplayName("Level 12 — Big Delivery")
            board(levelID: "level_005").previewDisplayName("Level 5 — Two colours")
        }
        .previewLayout(.fixed(width: 360, height: 460))
    }

    @ViewBuilder
    private static func board(levelID: String) -> some View {
        let result = Result { () throws -> MultiVanEngine in
            let level = try MultiVanLevelRepository().loadAllLevels().first { $0.id == levelID }
            guard let level else { throw CocoaError(.fileNoSuchFile) }
            return try MultiVanEngine(level: level)
        }
        switch result {
        case .success(let engine):
            MultiVanDioramaBoardView(engine: engine)
                .background(Color(red: 0.88, green: 0.94, blue: 0.97))
        case .failure(let error):
            Text("Preview unavailable: \(error.localizedDescription)")
        }
    }
}
#endif
