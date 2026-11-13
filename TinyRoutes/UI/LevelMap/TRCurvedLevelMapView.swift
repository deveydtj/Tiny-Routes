import SceneKit
import SwiftUI

/// The level map as a curved 3D world: the road winds away over a near horizon, each
/// level's tile on a signpost by it. Dragging slides the world under the lens like a
/// treadmill, and a flick glides on. Tapping a level drives the van to it, the map
/// following, then opens it; coming back after unlocking a level, the van drives on
/// to the new one. The signs are drawn in the scene, so VoiceOver reads clear
/// elements laid over them.
struct TRCurvedLevelMapView: View {
    let levels: [MultiVanLevel]
    let progressService: ProgressService
    let onLevelSelected: (String) -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var scene = TRCurvedLevelMapScene()
    @State private var size: CGSize = .zero
    /// The map y under the pivot: where it is, or where a glide or drive will end.
    @State private var focus = 0.0
    /// The focus when the finger went down, while it's down.
    @State private var dragStart: Double?
    @State private var isGliding = false
    @State private var isDriving = false
    /// The world waits for its first frame, so it never pops in half drawn.
    @State private var isMapShown = false
    @State private var glideEnd: Task<Void, Never>?
    /// The level the van last drove to, shared with the flat map.
    @AppStorage("levelMap.vanLevelID") private var vanLevelID = ""

    private var lens: TRCurvedLevelMapLens { TRCurvedLevelMapLens(levelCount: levels.count) }

    var body: some View {
        let snapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)
        let currentIndex = min(snapshot.firstIncompleteIndex, max(levels.count - 1, 0))
        let art = levels.enumerated().map { index, level in
            TRCurvedLevelMapScene.SignArt(
                levelNumber: levelNumber(level, fallback: index + 1),
                state: snapshot.tileState(at: index, levelID: level.id),
                stars: snapshot.stars(for: level.id)
            )
        }
        ZStack(alignment: .topLeading) {
            TRCurvedLevelMapSceneView(
                scene: scene.scene, camera: scene.cameraNode,
                isPlaying: isDriving || isGliding || dragStart != nil,
                onFirstFrame: { withAnimation(.easeOut(duration: 0.3)) { isMapShown = true } }
            )
            .opacity(isMapShown ? 1 : 0)
            .accessibilityHidden(true)

            ForEach(Array(art.enumerated()), id: \.offset) { index, art in
                if let frame = lens.signFrame(index, focus: focus, in: size) {
                    signElement(art, frame: frame) { select(index: index, state: art.state) }
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .contentShape(Rectangle())
        .gesture(drag(art: art))
        .overlay(alignment: .bottomTrailing) {
            if isMapShown, levels.indices.contains(currentIndex), lens.signFrame(currentIndex, focus: focus, in: size) == nil {
                TRJumpToCurrentButton { glide(to: lens.focus(forLevel: currentIndex), duration: 0.6) }
                    .padding(.trailing, 18)
                    .padding(.bottom, 12)
                    .transition(.opacity.combined(with: .scale(scale: 0.9)))
            }
        }
        .animation(.easeOut(duration: 0.2), value: lens.signFrame(currentIndex, focus: focus, in: size) == nil)
        .onGeometryChange(for: CGSize.self) { $0.size } action: { size in
            self.size = size
            scene.aim(in: size)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Level map")
        .accessibilityScrollAction { edge in
            // A page of levels at a time, towards the edge VoiceOver scrolls to.
            let page = TRLevelMapLayout.step * 3
            glide(to: focus + (edge == .top || edge == .leading ? page : -page), duration: 0.4)
        }
        .onChange(of: art) { _, art in scene.setSigns(art) }
        .task(id: levels.map(\.id)) {
            scene.load(lens)
            scene.setSigns(art)
            // Up to a few seconds for the world to draw; the van waits for it.
            for _ in 0..<60 where !isMapShown {
                do { try await Task.sleep(for: .seconds(0.05)) } catch { return }
            }
            await settleVan(currentIndex: currentIndex, snapshot: snapshot)
        }
    }

    /// A clear stand-in over a sign, for VoiceOver; taps go to the map's gesture.
    private func signElement(_ art: TRCurvedLevelMapScene.SignArt, frame: CGRect, action: @escaping () -> Void) -> some View {
        Rectangle()
            .fill(Color.clear)
            .frame(width: frame.width, height: frame.height)
            .position(x: frame.midX, y: frame.midY)
            .allowsHitTesting(false)
            .accessibilityElement()
            .accessibilityLabel(Text("Level \(art.levelNumber)"))
            .accessibilityValue(Text(TRLevelTile.accessibilityValue(state: art.state, stars: art.stars)))
            .accessibilityAddTraits(.isButton)
            .accessibilityAction(.default, action)
            // VoiceOver reads a locked level dimmed, as the flat map's tile.
            .disabled(art.state == .locked)
    }

    private func levelNumber(_ level: MultiVanLevel, fallback: Int) -> Int {
        level.id.split(separator: "_").last.flatMap { Int($0) } ?? fallback
    }

    // MARK: - Scrolling

    /// Drags slide the world, keeping the road under the pivot moving with the
    /// finger; a flick glides on. A touch that barely moves is a tap on a sign.
    private func drag(art: [TRCurvedLevelMapScene.SignArt]) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                guard !isDriving else { return }
                let start = dragStart ?? beginDrag()
                let range = lens.focusRange
                let wanted = start + Double(value.translation.height / TRCurvedLevelMapLens.pointsPerUnit(in: size))
                // Past either end the world gives a little, then springs back.
                let overshoot = wanted - min(max(wanted, range.lowerBound), range.upperBound)
                focus = wanted - overshoot * 0.65
                scene.setFocus(focus)
            }
            .onEnded { value in
                guard let start = dragStart else { return }
                dragStart = nil
                if hypot(value.translation.width, value.translation.height) < 8 {
                    tap(at: value.location, art: art)
                    // A tap only stops a glide where it is.
                    glide(to: start, duration: 0)
                    return
                }
                let ppu = Double(TRCurvedLevelMapLens.pointsPerUnit(in: size))
                let flick = Double(value.predictedEndTranslation.height - value.translation.height) / ppu
                glide(to: focus + flick, duration: reduceMotion ? 0.2 : min(max(abs(flick) * 0.25, 0.35), 0.9))
            }
    }

    /// Catches a glide where it has got to, for the finger to carry on from.
    private func beginDrag() -> Double {
        glideEnd?.cancel()
        isGliding = false
        let current = scene.focus
        scene.setFocus(current)
        focus = current
        dragStart = current
        return current
    }

    /// Glides the world to `target`, kept within the map.
    private func glide(to target: Double, duration: Double) {
        let range = lens.focusRange
        let target = min(max(target, range.lowerBound), range.upperBound)
        glideEnd?.cancel()
        focus = target
        guard duration > 0, abs(target - scene.focus) > 0.001 else {
            scene.setFocus(target)
            isGliding = false
            return
        }
        scene.glide(toFocus: target, duration: duration)
        isGliding = true
        glideEnd = Task {
            do { try await Task.sleep(for: .seconds(duration + 0.05)) } catch { return }
            isGliding = false
        }
    }

    /// The nearest sign under the finger, with room round small far ones.
    private func tap(at location: CGPoint, art: [TRCurvedLevelMapScene.SignArt]) {
        let hits = art.indices.compactMap { index -> (index: Int, frame: CGRect)? in
            guard let frame = lens.signFrame(index, focus: focus, in: size) else { return nil }
            let grow = max(44 - frame.width, 44 - frame.height, 0) / 2
            return frame.insetBy(dx: -grow, dy: -grow).contains(location) ? (index, frame) : nil
        }
        // Nearer signs are bigger and stand in front.
        guard let hit = hits.max(by: { $0.frame.width < $1.frame.width }) else { return }
        select(index: hit.index, state: art[hit.index].state)
    }

    // MARK: - The van

    /// Parks the van where it last went, with the map there, then drives it on to
    /// the current level if one has opened since.
    private func settleVan(currentIndex: Int, snapshot: TRLevelProgressSnapshot) async {
        let lastIndex = levels.firstIndex { $0.id == vanLevelID }
        let startIndex = lastIndex.flatMap { snapshot.tileState(at: $0, levelID: levels[$0].id) == .locked ? nil : $0 } ?? currentIndex
        scene.parkVan(atY: lens.layout.parking(startIndex))
        glide(to: lens.focus(forLevel: startIndex), duration: 0)
        vanLevelID = levels.indices.contains(currentIndex) ? levels[currentIndex].id : ""
        guard startIndex < currentIndex else { return }
        if reduceMotion {
            scene.parkVan(atY: lens.layout.parking(currentIndex))
            glide(to: lens.focus(forLevel: currentIndex), duration: 0)
            return
        }
        // A beat after the page appears.
        do { try await Task.sleep(for: .seconds(0.6)) } catch { return }
        await drive(toIndex: currentIndex)
    }

    private func select(index: Int, state: TRLevelTileState) {
        guard state != .locked, !isDriving else { return }
        let levelID = levels[index].id
        vanLevelID = levelID
        guard !reduceMotion, scene.driveDuration(toY: lens.layout.parking(index)) > 0 else {
            onLevelSelected(levelID)
            return
        }
        Task {
            await drive(toIndex: index)
            onLevelSelected(levelID)
        }
    }

    private func drive(toIndex index: Int) async {
        glideEnd?.cancel()
        isGliding = false
        isDriving = true
        let target = lens.focus(forLevel: index)
        let duration = scene.driveVan(toY: lens.layout.parking(index), focus: target)
        focus = target
        try? await Task.sleep(for: .seconds(duration + 0.12))
        // SceneKit only runs the drive while it draws; however far it got, the van
        // ends at its stop and the map on its level.
        scene.parkVan(atY: lens.layout.parking(index))
        scene.setFocus(target)
        isDriving = false
    }
}

/// The curved map's `SCNView`: transparent, so the page's sky shows over the
/// horizon, and only drawing every frame while the world moves.
private struct TRCurvedLevelMapSceneView: UIViewRepresentable {
    let scene: SCNScene
    let camera: SCNNode
    let isPlaying: Bool
    var onFirstFrame: (() -> Void)?

    func makeCoordinator() -> TRSceneFirstFrameWatcher {
        TRSceneFirstFrameWatcher()
    }

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView(frame: .zero, options: nil)
        view.backgroundColor = .clear
        view.isOpaque = false
        view.antialiasingMode = .multisampling4X
        view.preferredFramesPerSecond = 60
        view.isUserInteractionEnabled = false
        view.scene = scene
        view.pointOfView = camera
        context.coordinator.onFirstFrame = onFirstFrame
        view.delegate = context.coordinator
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        view.isPlaying = isPlaying
    }

    static func dismantleUIView(_ view: SCNView, coordinator: TRSceneFirstFrameWatcher) {
        view.delegate = nil
        view.isPlaying = false
        view.pointOfView = nil
        view.scene = nil
    }
}

#Preview("Curved 3D level map") {
    TRCurvedLevelMapView(
        levels: (try? MultiVanLevelRepository().loadAllLevels()) ?? [],
        progressService: ProgressService(),
        onLevelSelected: { _ in }
    )
    .background(Color(red: 0.74, green: 0.88, blue: 0.96))
}
