import SpriteKit
import UIKit

final class TRConfettiScene: SKScene {
    private var hasPlayed = false

    override init(size: CGSize) {
        super.init(size: size)
        commonInit()
    }

    required init?(coder aDecoder: NSCoder) {
        super.init(coder: aDecoder)
        commonInit()
    }

    override init() {
        super.init(size: .zero)
        commonInit()
    }

    func play(mode: TRConfettiMode, reduceMotion: Bool) {
        guard !hasPlayed else { return }
        hasPlayed = true
        removeAllChildren()

        guard mode == .success else { return }
        guard !reduceMotion else { return }

        addLevelCompleteBurst()
    }

    func resetForReplay() {
        hasPlayed = false
        removeAllChildren()
    }

    private func commonInit() {
        backgroundColor = .clear
        scaleMode = .resizeFill
        isUserInteractionEnabled = false
    }

    private func addLevelCompleteBurst() {
        let center = CGPoint(x: size.width * 0.50, y: size.height * 0.72)
        let left = CGPoint(x: size.width * 0.18, y: size.height * 0.42)
        let right = CGPoint(x: size.width * 0.82, y: size.height * 0.42)

        addBurstEmitter(
            position: center,
            emissionAngle: .pi / 2,
            emissionRange: .pi * 2.0,
            scale: 1.0,
            particleCount: 150
        )
        addBurstEmitter(
            position: left,
            emissionAngle: .pi * 0.28,
            emissionRange: .pi * 0.65,
            scale: 0.75,
            particleCount: 55
        )
        addBurstEmitter(
            position: right,
            emissionAngle: .pi * 0.72,
            emissionRange: .pi * 0.65,
            scale: 0.75,
            particleCount: 55
        )
    }

    private func addBurstEmitter(
        position: CGPoint,
        emissionAngle: CGFloat,
        emissionRange: CGFloat,
        scale: CGFloat,
        particleCount: Int
    ) {
        guard let emitter = makeEmitter() else { return }

        emitter.position = position
        emitter.emissionAngle = emissionAngle
        emitter.emissionAngleRange = emissionRange
        emitter.particleScale *= scale
        emitter.particleScaleRange *= scale
        emitter.numParticlesToEmit = particleCount

        addChild(emitter)

        let cleanupDelay = TimeInterval(emitter.particleLifetime + emitter.particleLifetimeRange + 0.7)
        emitter.run(.sequence([
            .wait(forDuration: cleanupDelay),
            .removeFromParent()
        ]))
    }

    private func makeEmitter() -> SKEmitterNode? {
        guard let emitter = SKEmitterNode(fileNamed: "LevelCompleteConfetti") else {
            assertionFailure("Missing LevelCompleteConfetti.sks from app bundle resources.")
            return nil
        }

        emitter.targetNode = self
        emitter.particleBirthRate = max(emitter.particleBirthRate, 900)
        emitter.numParticlesToEmit = max(emitter.numParticlesToEmit, 140)
        emitter.particleLifetime = max(emitter.particleLifetime, 1.8)
        emitter.particleLifetimeRange = max(emitter.particleLifetimeRange, 0.35)
        emitter.particleColorBlendFactor = 1.0
        emitter.particleColorSequence = Self.successColorSequence

        return emitter
    }

    private static let successColorSequence = SKKeyframeSequence(
        keyframeValues: [
            UIColor(red: 0.20, green: 0.56, blue: 0.95, alpha: 1.0),
            UIColor(red: 0.16, green: 0.75, blue: 0.68, alpha: 1.0),
            UIColor(red: 1.00, green: 0.78, blue: 0.20, alpha: 1.0),
            UIColor(red: 1.00, green: 0.48, blue: 0.20, alpha: 1.0),
            UIColor(red: 0.53, green: 0.36, blue: 0.96, alpha: 1.0),
            UIColor(red: 0.30, green: 0.78, blue: 0.40, alpha: 1.0)
        ],
        times: [0.0, 0.18, 0.36, 0.54, 0.72, 1.0]
    )
}
