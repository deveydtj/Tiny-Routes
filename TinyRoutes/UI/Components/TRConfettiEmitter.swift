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

    var body: some View {
        GeometryReader { geometry in
            SpriteView(scene: scene, options: [.allowsTransparency])
                .frame(width: geometry.size.width, height: geometry.size.height)
                .onAppear {
                    startIfNeeded(in: geometry.size)
                }
                .onChange(of: geometry.size) { _, newSize in
                    scene.size = newSize
                    startIfNeeded(in: newSize)
                }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    private func startIfNeeded(in size: CGSize) {
        scene.size = size
        guard size.width > 0, size.height > 0 else { return }
        guard !didStart else { return }
        didStart = true
        scene.play(mode: mode, reduceMotion: reduceMotion)
    }
}

#Preview("Confetti") {
    ZStack {
        TRResultScreenBackground()
        TRConfettiEmitter(mode: .success)
    }
}
