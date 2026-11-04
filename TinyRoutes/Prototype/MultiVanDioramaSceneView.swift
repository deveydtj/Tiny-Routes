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

    func makeCoordinator() -> MultiVanDioramaScene {
        MultiVanDioramaScene()
    }

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView(frame: .zero, options: nil)
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
        let scene = context.coordinator
        view.scene = scene.scene
        view.pointOfView = scene.cameraNode
        // In the background, while the player plans.
        view.prepare(MultiVanDioramaEffects.warmUpNodes(), completionHandler: nil)
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        context.coordinator.setCamera(camera)
        context.coordinator.load(level, graph: state.graph)
        context.coordinator.sync(state)
        context.coordinator.play(cues, animates: state.animates)
    }

    /// The switcher removing the board lands here: drop the scene so its GPU
    /// resources go with it, and stop rendering.
    static func dismantleUIView(_ view: SCNView, coordinator: MultiVanDioramaScene) {
        view.isPlaying = false
        view.pointOfView = nil
        view.scene = nil
    }
}
