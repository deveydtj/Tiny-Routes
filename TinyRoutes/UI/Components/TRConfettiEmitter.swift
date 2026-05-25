import SpriteKit
import SwiftUI
import UIKit

enum TRConfettiMode {
    case success
    case failure
}

struct TRConfettiEmitter: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let mode: TRConfettiMode
    let playbackID: UUID
    let selectedConfettiOption: ShopCosmeticOption

    init(
        mode: TRConfettiMode,
        playbackID: UUID = UUID(),
        selectedConfettiOption: ShopCosmeticOption = GameplayCosmeticLoadout.default.confetti
    ) {
        self.mode = mode
        self.playbackID = playbackID
        self.selectedConfettiOption = selectedConfettiOption
    }

    var body: some View {
        GeometryReader { geometry in
            TRConfettiSpriteView(
                mode: mode,
                playbackID: playbackID,
                selectedConfettiOption: selectedConfettiOption,
                reduceMotion: reduceMotion,
                containerSize: geometry.size
            )
            .frame(width: geometry.size.width, height: geometry.size.height)
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

private struct TRConfettiSpriteView: UIViewRepresentable {
    let mode: TRConfettiMode
    let playbackID: UUID
    let selectedConfettiOption: ShopCosmeticOption
    let reduceMotion: Bool
    let containerSize: CGSize

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIView(context: Context) -> TRConfettiSKView {
        let view = TRConfettiSKView()
        view.allowsTransparency = true
        view.backgroundColor = .clear
        view.isOpaque = false
        view.isUserInteractionEnabled = false
        view.isAccessibilityElement = false
        view.accessibilityElementsHidden = true
        view.onLayout = { [weak coordinator = context.coordinator] size in
            coordinator?.layoutChanged(to: size)
        }
        return view
    }

    func updateUIView(_ uiView: TRConfettiSKView, context: Context) {
        context.coordinator.update(
            mode: mode,
            playbackID: playbackID,
            selectedConfettiOption: selectedConfettiOption,
            reduceMotion: reduceMotion,
            containerSize: containerSize,
            in: uiView
        )
    }

    static func dismantleUIView(_ uiView: TRConfettiSKView, coordinator: Coordinator) {
        uiView.onLayout = nil
        uiView.presentScene(nil)
        coordinator.reset()
    }

    final class Coordinator {
        private struct PlaybackConfig {
            let mode: TRConfettiMode
            let playbackID: UUID
            let selectedConfettiOption: ShopCosmeticOption
            let reduceMotion: Bool
            let containerSize: CGSize
        }

        private var config: PlaybackConfig?
        private var activePlaybackID: UUID?
        private var startedPlaybackID: UUID?
        private var scene: TRConfettiScene?

        func update(
            mode: TRConfettiMode,
            playbackID: UUID,
            selectedConfettiOption: ShopCosmeticOption,
            reduceMotion: Bool,
            containerSize: CGSize,
            in view: TRConfettiSKView
        ) {
            config = PlaybackConfig(
                mode: mode,
                playbackID: playbackID,
                selectedConfettiOption: selectedConfettiOption,
                reduceMotion: reduceMotion,
                containerSize: containerSize
            )

            if activePlaybackID != playbackID || scene == nil {
                activePlaybackID = playbackID
                startedPlaybackID = nil
                let newScene = TRConfettiScene(size: effectiveSize(viewBoundsSize: view.bounds.size))
                scene = newScene
                view.presentScene(newScene)
            }

            scene?.size = effectiveSize(viewBoundsSize: view.bounds.size)
            startIfPossible()
        }

        func layoutChanged(to size: CGSize) {
            scene?.size = effectiveSize(viewBoundsSize: size)
            startIfPossible()
        }

        func reset() {
            config = nil
            activePlaybackID = nil
            startedPlaybackID = nil
            scene = nil
        }

        private func startIfPossible() {
            guard let config else { return }
            guard startedPlaybackID != config.playbackID else { return }
            guard let scene else { return }
            guard scene.size.width > 0, scene.size.height > 0 else { return }

            let playbackResult = scene.play(
                mode: config.mode,
                reduceMotion: config.reduceMotion,
                selectedConfettiOption: config.selectedConfettiOption
            )

            switch playbackResult {
            case .played, .intentionallySkipped, .alreadyPlayed:
                startedPlaybackID = config.playbackID
            case .failedToCreateEmitter:
                startedPlaybackID = nil
            }
        }

        private func effectiveSize(viewBoundsSize: CGSize) -> CGSize {
            guard let config, config.containerSize.hasArea else {
                return viewBoundsSize
            }
            return config.containerSize
        }
    }
}

final class TRConfettiSKView: SKView {
    var onLayout: ((CGSize) -> Void)?

    override func layoutSubviews() {
        super.layoutSubviews()
        onLayout?(bounds.size)
    }
}

private extension CGSize {
    var hasArea: Bool {
        width > 0 && height > 0
    }
}

#Preview("Confetti") {
    ZStack {
        TRResultScreenBackground()
        TRConfettiEmitter(mode: .success)
    }
}
