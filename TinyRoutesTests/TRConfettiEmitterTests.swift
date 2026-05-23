import SpriteKit
import XCTest
@testable import TinyRoutes

final class TRConfettiEmitterTests: XCTestCase {
    func testConfettiSceneStartsEmpty() {
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        XCTAssertEqual(scene.children.count, 0)
    }

    func testFailureModeDoesNotAddCelebratoryEmitters() {
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        scene.play(mode: .failure, reduceMotion: false)

        XCTAssertEqual(scene.children.count, 0)
    }

    func testReduceMotionDoesNotAddAnimatedEmitters() {
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        scene.play(mode: .success, reduceMotion: true)

        XCTAssertEqual(scene.children.count, 0)
    }
}
