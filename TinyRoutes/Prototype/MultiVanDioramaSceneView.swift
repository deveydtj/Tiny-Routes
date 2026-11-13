import SceneKit
import SwiftUI

/// SwiftUI's handle on the diorama's `SCNView`. SwiftUI pushes values in from
/// `updateUIView`; SceneKit's render thread never reads the engine. Taps and
/// accessibility stay in SwiftUI, so the view takes no touches, and SwiftUI owns
/// the camera so its buttons know where every switch is.
struct MultiVanDioramaSceneView: UIViewRepresentable {
    let level: MultiVanLevel
    /// This frame's engine state, read in the board's `body`.
    let state: MultiVanDioramaFrame
    /// This frame's feedback tokens; the scene plays the new ones.
    var cues = MultiVanDioramaCues()
    let camera: MultiVanDioramaCamera
    /// Hands over a renderer built while the flat board was up, and keeps this one
    /// when the board goes. Nil builds a fresh one and drops it after.
    var preload: MultiVanDioramaPreload?
    /// The shop's choices; the scene repaints only when they change.
    var cosmetics = MultiVanCosmetics.standard

    func makeCoordinator() -> MultiVanDioramaRenderer {
        let renderer = preload?.take() ?? MultiVanDioramaRenderer()
        renderer.preload = preload
        return renderer
    }

    func makeUIView(context: Context) -> SCNView {
        context.coordinator.view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        // Low Power Mode takes the preload away, so the board drops this when it goes.
        context.coordinator.preload = preload
        let scene = context.coordinator.scene
        scene.setCamera(camera)
        scene.apply(cosmetics)
        scene.load(level, graph: state.graph)
        scene.sync(state)
        scene.play(cues, animates: state.animates)
    }

    /// The switcher removing the board lands here. The preload keeps the renderer,
    /// out of any window so it stops drawing; otherwise drop the scene so its GPU
    /// resources go with it.
    static func dismantleUIView(_ view: SCNView, coordinator: MultiVanDioramaRenderer) {
        view.isPlaying = false
        if let preload = coordinator.preload, preload.park(coordinator) { return }
        view.pointOfView = nil
        view.scene = nil
    }
}

/// The diorama's `SCNView` and the scene it draws, built together.
@MainActor
final class MultiVanDioramaRenderer {
    let view: SCNView
    let scene: MultiVanDioramaScene
    /// Where the board hands this back when it goes.
    weak var preload: MultiVanDioramaPreload?
    /// The level SceneKit has uploaded and compiled, so warming it again is free.
    fileprivate var preparedLevelID: String?

    init() {
        scene = MultiVanDioramaScene()
        view = SCNView(frame: .zero, options: nil)
        // The grade and depth of field only run on an opaque view without
        // multisampling, so the scene paints its own sky and jitters still frames
        // for antialiasing instead.
        view.isOpaque = true
        view.antialiasingMode = .none
        view.isJitteringEnabled = true
        view.preferredFramesPerSecond = 60
        view.isUserInteractionEnabled = false
        view.accessibilityElementsHidden = true
        #if DEBUG || MULTIVAN_INTERNAL
        // Times SceneKit's own frames during autoplay; nil otherwise.
        view.delegate = MultiVanPerformanceMeter.shared
        #endif
        view.scene = scene.scene
        view.pointOfView = scene.cameraNode
        // In the background, while the player plans.
        view.prepare(MultiVanDioramaEffects.warmUpNodes(), completionHandler: nil)
    }
}

/// Builds the diorama ahead of time while the flat board is up, so the 2D/3D
/// button shows a table that's already built, painted and compiled rather than
/// building it all in the frame the player asked for it. The renderer waits out of
/// any window, so it draws nothing until a board takes it.
@MainActor
final class MultiVanDioramaPreload {
    private var parked: MultiVanDioramaRenderer?

    var hasRenderer: Bool { parked != nil }

    /// The parked renderer, set up for a new board; nil when there isn't one.
    func take() -> MultiVanDioramaRenderer? {
        guard let renderer = parked else { return nil }
        parked = nil
        renderer.scene.prepareForBoard()
        return renderer
    }

    /// Keeps a renderer a board has finished with, for the next one. False when
    /// one is already waiting.
    func park(_ renderer: MultiVanDioramaRenderer) -> Bool {
        guard parked == nil else { return false }
        // It drew this level, so SceneKit already has it.
        renderer.preparedLevelID = renderer.scene.levelID
        parked = renderer
        return true
    }

    /// Lets the parked renderer and its GPU resources go.
    func release() {
        parked = nil
    }

    /// Builds the renderer if there isn't one and loads `level` into it, a step at
    /// a time so the flat board keeps drawing: the lawn and scenery are made off the
    /// main thread, then SceneKit uploads and compiles them off it too.
    func warm(_ level: MultiVanLevel, graph: RuntimeRouteGraph) async {
        if parked == nil {
            parked = MultiVanDioramaRenderer()
            try? await Task.sleep(for: Self.step)
        }
        guard !Task.isCancelled, let renderer = parked, renderer.preparedLevelID != level.id else { return }
        if renderer.scene.levelID != level.id {
            // Placing the scenery and painting the lawn are the long steps, and need no renderer.
            let ground = await Task.detached(priority: .utility) { MultiVanDioramaGround(level: level, graph: graph) }.value
            guard !Task.isCancelled, parked === renderer else { return }
            renderer.scene.load(level, graph: graph, ground: ground)
        }
        try? await Task.sleep(for: Self.step)
        guard !Task.isCancelled, parked === renderer else { return }
        let prepared = await withCheckedContinuation { continuation in
            renderer.view.prepare([renderer.scene.scene]) { continuation.resume(returning: $0) }
        }
        if prepared, renderer.scene.levelID == level.id { renderer.preparedLevelID = level.id }
    }

    /// Long enough between steps for the flat board to draw a frame or two.
    private static let step = Duration.milliseconds(50)
}

private struct MultiVanDioramaPreloadKey: EnvironmentKey {
    static let defaultValue: MultiVanDioramaPreload? = nil
}

extension EnvironmentValues {
    /// The switcher's preload, which the diorama takes its renderer from.
    var multiVanDioramaPreload: MultiVanDioramaPreload? {
        get { self[MultiVanDioramaPreloadKey.self] }
        set { self[MultiVanDioramaPreloadKey.self] = newValue }
    }
}
