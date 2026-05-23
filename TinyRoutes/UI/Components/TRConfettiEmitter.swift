import SpriteKit
import SwiftUI

enum TRConfettiMode {
    case success
    case failure
}

struct TRConfettiEmitter: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let mode: TRConfettiMode

    @State private var scene = TRConfettiScene()
    @State private var didStart = false

    private var modeIdentifier: String {
        switch mode {
        case .success: "success"
        case .failure: "failure"
        }
    }

    var body: some View {
        GeometryReader { geometry in
            SpriteView(scene: scene, options: [.allowsTransparency])
                .frame(width: geometry.size.width, height: geometry.size.height)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .onAppear {
                    startIfNeeded(in: geometry.size)
                }
                .onChange(of: geometry.size) { _, newSize in
                    scene.size = newSize
                    startIfNeeded(in: newSize)
                }
        }
        .id(modeIdentifier)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    private func startIfNeeded(in size: CGSize) {
        scene.size = size
        guard size.width > 0, size.height > 0 else { return }
        guard !didStart else { return }
        let playbackResult = scene.play(mode: mode, reduceMotion: reduceMotion)

        switch playbackResult {
        case .played, .intentionallySkipped, .alreadyPlayed:
            didStart = true
        case .failedToCreateEmitter:
            didStart = false
        }
    }
}

#Preview("Confetti") {
    ZStack {
        TRResultScreenBackground()
        TRConfettiEmitter(mode: .success)
    }
}
