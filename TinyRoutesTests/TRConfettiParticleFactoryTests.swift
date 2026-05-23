import XCTest
@testable import TinyRoutes

final class TRConfettiParticleFactoryTests: XCTestCase {
    func testSuccessModeCreatesMoreParticlesThanFailureMode() {
        let factory = TRConfettiParticleFactory()
        let size = CGSize(width: 390, height: 844)

        let successParticles = factory.makeParticles(mode: .success, in: size, seed: 42)
        let failureParticles = factory.makeParticles(mode: .failure, in: size, seed: 42)

        XCTAssertGreaterThan(successParticles.count, failureParticles.count)
        XCTAssertGreaterThanOrEqual(successParticles.count, 36)
        XCTAssertLessThanOrEqual(successParticles.count, 60)
        XCTAssertGreaterThanOrEqual(failureParticles.count, 8)
        XCTAssertLessThanOrEqual(failureParticles.count, 16)
    }

    func testParticlesHaveValidSizeAndDuration() {
        let particles = TRConfettiParticleFactory().makeParticles(
            mode: .success,
            in: CGSize(width: 320, height: 568),
            seed: 7
        )

        for particle in particles {
            XCTAssertGreaterThan(particle.size, 0)
            XCTAssertGreaterThanOrEqual(particle.duration, 0)
            XCTAssertGreaterThanOrEqual(particle.delay, 0)
        }
    }

    func testColorIndexesAreInsidePaletteRange() {
        let factory = TRConfettiParticleFactory()

        for mode in [TRConfettiMode.success, .failure] {
            let particles = factory.makeParticles(mode: mode, in: CGSize(width: 320, height: 568), seed: 99)
            let palette = TRConfettiParticleFactory.palette(for: mode)

            for particle in particles {
                XCTAssertTrue(palette.indices.contains(particle.colorIndex))
            }
        }
    }

    func testReduceMotionCreatesSmallBoundedStaticParticleCount() {
        let factory = TRConfettiParticleFactory()
        let size = CGSize(width: 390, height: 844)

        let successParticles = factory.makeParticles(mode: .success, in: size, reduceMotion: true, seed: 11)
        let failureParticles = factory.makeParticles(mode: .failure, in: size, reduceMotion: true, seed: 11)

        XCTAssertLessThanOrEqual(successParticles.count, 8)
        XCTAssertLessThanOrEqual(failureParticles.count, 1)
        XCTAssertTrue(successParticles.allSatisfy { $0.startX == $0.endX && $0.startY == $0.endY })
        XCTAssertTrue(failureParticles.allSatisfy { $0.startX == $0.endX && $0.startY == $0.endY })
    }
}
