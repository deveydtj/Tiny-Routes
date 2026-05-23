import SpriteKit
import UIKit

enum TRConfettiPlaybackResult: Equatable {
    case played
    case intentionallySkipped
    case failedToCreateEmitter
    case alreadyPlayed
}

final class TRConfettiScene: SKScene {
    private var hasPlayed = false
    #if DEBUG
    private static var hasLoggedResourceAvailability = false
    #endif

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

    func play(mode: TRConfettiMode, reduceMotion: Bool) -> TRConfettiPlaybackResult {
        guard !hasPlayed else { return .alreadyPlayed }
        removeAllChildren()

        guard mode == .success else { return .intentionallySkipped }
        guard !reduceMotion else { return .intentionallySkipped }

        guard addLevelCompleteBurst() else { return .failedToCreateEmitter }

        hasPlayed = true
        return .played
    }

    func resetForReplay() {
        hasPlayed = false
        removeAllChildren()
    }

    private func commonInit() {
        backgroundColor = .clear
        scaleMode = .resizeFill
        isUserInteractionEnabled = false
        Self.logResourceAvailability()
    }

    private func addLevelCompleteBurst() -> Bool {
        let center = CGPoint(x: size.width * 0.50, y: size.height * 0.72)
        let left = CGPoint(x: size.width * 0.18, y: size.height * 0.42)
        let right = CGPoint(x: size.width * 0.82, y: size.height * 0.42)

        let addedCenter = addBurstEmitter(
            name: "confetti.center",
            position: center,
            emissionAngle: .pi / 2,
            emissionRange: .pi * 2.0,
            scale: 1.0,
            particleCount: 150
        )
        let addedLeft = addBurstEmitter(
            name: "confetti.left",
            position: left,
            emissionAngle: .pi * 0.28,
            emissionRange: .pi * 0.65,
            scale: 0.75,
            particleCount: 55
        )
        let addedRight = addBurstEmitter(
            name: "confetti.right",
            position: right,
            emissionAngle: .pi * 0.72,
            emissionRange: .pi * 0.65,
            scale: 0.75,
            particleCount: 55
        )

        return addedCenter || addedLeft || addedRight
    }

    private func addBurstEmitter(
        name: String,
        position: CGPoint,
        emissionAngle: CGFloat,
        emissionRange: CGFloat,
        scale: CGFloat,
        particleCount: Int
    ) -> Bool {
        guard let emitter = makeBestAvailableEmitter() else { return false }

        emitter.name = name
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

        return true
    }

    private func makeBestAvailableEmitter() -> SKEmitterNode? {
        if let emitter = SKEmitterNode(fileNamed: "LevelCompleteConfetti") {
            configureEmitter(emitter)
            return emitter
        }

        #if DEBUG
        print("TRConfettiScene: LevelCompleteConfetti.sks failed to load. Using fallback emitter.")
        #endif

        guard let emitter = makeProgrammaticEmitter() else {
            assertionFailure("Unable to create fallback confetti emitter.")
            return nil
        }

        configureEmitter(emitter)
        return emitter
    }

    private func configureEmitter(_ emitter: SKEmitterNode) {
        emitter.targetNode = self
        emitter.particleBirthRate = max(emitter.particleBirthRate, 900)
        emitter.numParticlesToEmit = max(emitter.numParticlesToEmit, 140)
        emitter.particleLifetime = max(emitter.particleLifetime, 1.8)
        emitter.particleLifetimeRange = max(emitter.particleLifetimeRange, 0.35)
        emitter.particleColorBlendFactor = 1.0
        emitter.particleColorSequence = Self.successColorSequence
    }

    private func makeProgrammaticEmitter() -> SKEmitterNode? {
        let emitter = SKEmitterNode()
        emitter.particleTexture = makeFallbackTexture()
        emitter.particleBirthRate = 1200
        emitter.numParticlesToEmit = 140
        emitter.particleLifetime = 2.1
        emitter.particleLifetimeRange = 0.55
        emitter.particleSpeed = 260
        emitter.particleSpeedRange = 150
        emitter.particleScale = 0.34
        emitter.particleScaleRange = 0.18
        emitter.particleAlpha = 1.0
        emitter.particleAlphaRange = 0.15
        emitter.particleAlphaSpeed = -0.45
        emitter.particleRotationRange = .pi * 2
        emitter.particleRotationSpeed = .pi * 4.5
        emitter.particleBlendMode = .alpha
        emitter.yAcceleration = -220
        emitter.xAcceleration = 0
        emitter.particlePositionRange = CGVector(dx: 24, dy: 18)
        return emitter
    }

    private func makeFallbackTexture() -> SKTexture? {
        let texture = SKTexture(imageNamed: "confetti_particle")
        if texture.size() != .zero {
            return texture
        }

        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 8, height: 8))
        let image = renderer.image { context in
            UIColor.white.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 8, height: 8))
        }
        return SKTexture(image: image)
    }

    #if DEBUG
    private static func logResourceAvailability() {
        guard !hasLoggedResourceAvailability else { return }
        hasLoggedResourceAvailability = true
        let exists = Bundle.main.url(forResource: "LevelCompleteConfetti", withExtension: "sks") != nil
        print("TRConfettiScene: LevelCompleteConfetti.sks available = \(exists)")
    }
    #else
    private static func logResourceAvailability() {}
    #endif

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
