import SceneKit
import SwiftUI

/// The level map as a 3D island: the scene draws the lawn, road, scenery and van,
/// and SwiftUI tiles stand on the road over it, so they stay crisp, tappable and
/// readable by VoiceOver. Tapping a level drives the van to it, then opens it.
/// Coming back after unlocking a level, the van drives on to the new one.
struct TRLevelMapDioramaView: View {
    let levels: [MultiVanLevel]
    let progressService: ProgressService
    let onLevelSelected: (String) -> Void
    /// The van is about to drive on to a level opened since the last visit.
    var onDriveToNewLevel: (String) -> Void = { _ in }
    /// The current level's tile in the `coordinateSpace` given, for Jump to Current.
    var coordinateSpace: NamedCoordinateSpace = .named("levelMap")
    var onCurrentTileFrame: (CGRect) -> Void = { _ in }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var scene = TRLevelMapScene()
    @State private var width: CGFloat = 0
    /// While the van drives, taps wait and SceneKit draws every frame.
    @State private var isDriving = false
    /// Tiles and van wait for the island's first frame, so they never float in
    /// an empty sky while SceneKit gets going.
    @State private var isIslandShown = false
    /// The level the van last drove to, so it can drive on from there next visit.
    @AppStorage("levelMap.vanLevelID") private var vanLevelID = ""

    private var layout: TRLevelMapLayout { TRLevelMapLayout(levelCount: levels.count) }

    var body: some View {
        let snapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)
        let currentIndex = min(snapshot.firstIncompleteIndex, max(levels.count - 1, 0))
        ZStack(alignment: .topLeading) {
            if width > 0 {
                TRLevelMapSceneView(
                    map: scene, scene: scene.scene, camera: scene.cameraNode, layout: layout,
                    isPlaying: false, height: layout.viewHeight(viewWidth: width),
                    onFirstFrame: { withAnimation(.easeOut(duration: 0.3)) { isIslandShown = true } }
                )
                .frame(width: width, height: layout.viewHeight(viewWidth: width))

                ForEach(Array(levels.enumerated()), id: \.element.id) { index, level in
                    let state = snapshot.tileState(at: index, levelID: level.id)
                    TRLevelTile(
                        levelNumber: levelNumber(level, fallback: index + 1),
                        state: state,
                        stars: snapshot.stars(for: level.id)
                    ) {
                        select(index: index, state: state)
                    }
                    .position(tileCentre(index))
                    .opacity(isIslandShown ? 1 : 0)
                    .id(level.id)
                    .onGeometryChange(for: CGRect.self) { $0.frame(in: coordinateSpace) } action: { frame in
                        if index == currentIndex { onCurrentTileFrame(frame) }
                    }
                }

                // Over the tiles, so the van never hides behind one.
                TRLevelMapSceneView(
                    map: scene, scene: scene.vanScene, camera: scene.vanCameraNode, layout: layout,
                    isPlaying: isDriving, height: layout.viewHeight(viewWidth: width)
                )
                .frame(width: width, height: layout.viewHeight(viewWidth: width))
                .opacity(isIslandShown ? 1 : 0)
                .allowsHitTesting(false)
            }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .frame(height: width > 0 ? layout.viewHeight(viewWidth: width) : 400)
        .onGeometryChange(for: CGFloat.self) { $0.size.width } action: { width = $0 }
        .task(id: levels.map(\.id)) {
            scene.load(layout)
            // Up to a few seconds for the island to draw; the van waits for it.
            for _ in 0..<60 where !isIslandShown {
                do { try await Task.sleep(for: .seconds(0.05)) } catch { return }
            }
            await settleVan(currentIndex: currentIndex, snapshot: snapshot)
        }
    }

    /// Tiles stand on the road at their level's stop.
    private func tileCentre(_ index: Int) -> CGPoint {
        let foot = layout.viewPoint(layout.world(layout.station(index)), viewWidth: width)
        return CGPoint(x: foot.x, y: foot.y - TRLevelTile.size.height / 2 + 10)
    }

    private func levelNumber(_ level: MultiVanLevel, fallback: Int) -> Int {
        level.id.split(separator: "_").last.flatMap { Int($0) } ?? fallback
    }

    /// Parks the van where it last went, then drives it on to the current level if
    /// one has opened since.
    private func settleVan(currentIndex: Int, snapshot: TRLevelProgressSnapshot) async {
        let lastIndex = levels.firstIndex { $0.id == vanLevelID }
        let startIndex = lastIndex.flatMap { snapshot.tileState(at: $0, levelID: levels[$0].id) == .locked ? nil : $0 } ?? currentIndex
        scene.parkVan(atY: layout.parking(startIndex))
        vanLevelID = levels.indices.contains(currentIndex) ? levels[currentIndex].id : ""
        guard startIndex < currentIndex else { return }
        if reduceMotion {
            scene.parkVan(atY: layout.parking(currentIndex))
            return
        }
        onDriveToNewLevel(levels[currentIndex].id)
        // A beat after the page appears, and after it scrolls the level into view.
        do { try await Task.sleep(for: .seconds(0.6)) } catch { return }
        await drive(toIndex: currentIndex)
    }

    private func select(index: Int, state: TRLevelTileState) {
        guard state != .locked, !isDriving else { return }
        let levelID = levels[index].id
        vanLevelID = levelID
        guard !reduceMotion, scene.driveDuration(toY: layout.parking(index)) > 0 else {
            onLevelSelected(levelID)
            return
        }
        Task {
            await drive(toIndex: index)
            onLevelSelected(levelID)
        }
    }

    private func drive(toIndex index: Int) async {
        isDriving = true
        let duration = scene.driveVan(toY: layout.parking(index))
        try? await Task.sleep(for: .seconds(duration + 0.12))
        // SceneKit only runs the drive while it draws; however far it got, the van
        // ends at its stop.
        scene.parkVan(atY: layout.parking(index))
        isDriving = false
    }
}

/// One of the map's `SCNView`s, the island's or the van's: transparent, so what's
/// beneath shows through, and only drawing every frame while the van drives.
private struct TRLevelMapSceneView: UIViewRepresentable {
    let map: TRLevelMapScene
    let scene: SCNScene
    let camera: SCNNode
    let layout: TRLevelMapLayout
    let isPlaying: Bool
    let height: CGFloat
    var onFirstFrame: (() -> Void)? = nil

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
        view.accessibilityElementsHidden = true
        view.scene = scene
        view.pointOfView = camera
        context.coordinator.onFirstFrame = onFirstFrame
        view.delegate = context.coordinator
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        map.load(layout)
        view.isPlaying = isPlaying
        // A long map would outgrow the GPU's largest drawable at full scale.
        view.contentScaleFactor = min(UIScreen.main.scale, 8192 / max(height, 1))
    }

    static func dismantleUIView(_ view: SCNView, coordinator: TRSceneFirstFrameWatcher) {
        view.delegate = nil
        view.isPlaying = false
        view.pointOfView = nil
        view.scene = nil
    }
}

/// Hears SceneKit finish a view's first frame, on its render thread, and tells the
/// main actor once.
final class TRSceneFirstFrameWatcher: NSObject, SCNSceneRendererDelegate, @unchecked Sendable {
    var onFirstFrame: (() -> Void)?
    private var hasRendered = false

    func renderer(_ renderer: SCNSceneRenderer, didRenderScene scene: SCNScene, atTime time: TimeInterval) {
        guard !hasRendered else { return }
        hasRendered = true
        let onFirstFrame = onFirstFrame
        DispatchQueue.main.async { onFirstFrame?() }
    }
}

#Preview("3D level map") {
    ScrollView {
        TRLevelMapDioramaView(
            levels: (try? MultiVanLevelRepository().loadAllLevels()) ?? [],
            progressService: ProgressService(),
            onLevelSelected: { _ in }
        )
    }
    .background(Color(red: 0.74, green: 0.88, blue: 0.96))
}
