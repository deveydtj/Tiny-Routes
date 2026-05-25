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

        let result = scene.play(mode: .failure, reduceMotion: false)

        XCTAssertEqual(result, .intentionallySkipped)
        XCTAssertEqual(scene.children.count, 0)
    }

    func testReduceMotionDoesNotAddAnimatedEmitters() {
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        let result = scene.play(mode: .success, reduceMotion: true)

        XCTAssertEqual(result, .intentionallySkipped)
        XCTAssertEqual(scene.children.count, 0)
    }

    func testSuccessModeAddsConfettiEmitters() {
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        let result = scene.play(mode: .success, reduceMotion: false)

        XCTAssertEqual(result, .played)
        XCTAssertEqual(scene.children.count, 3)
        XCTAssertEqual(scene.children.map(\.name), ["confetti.center", "confetti.left", "confetti.right"])
    }

    func testSuccessModeDoesNotDuplicateEmittersWhenPlayedTwice() {
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        let firstResult = scene.play(mode: .success, reduceMotion: false)
        let secondResult = scene.play(mode: .success, reduceMotion: false)

        XCTAssertEqual(firstResult, .played)
        XCTAssertEqual(secondResult, .alreadyPlayed)
        XCTAssertEqual(scene.children.count, 3)
    }

    func testResetForReplayClearsAndAllowsReplay() {
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        XCTAssertEqual(scene.play(mode: .success, reduceMotion: false), .played)
        XCTAssertEqual(scene.children.count, 3)

        scene.resetForReplay()

        XCTAssertEqual(scene.children.count, 0)
        XCTAssertEqual(scene.play(mode: .success, reduceMotion: false), .played)
        XCTAssertEqual(scene.children.count, 3)
    }

    @MainActor
    func testConfettiEmitterCanBeConstructedWithEveryConfettiOption() {
        for option in ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.confetti) {
            let emitter = TRConfettiEmitter(
                mode: .success,
                playbackID: UUID(),
                selectedConfettiOption: option
            )

            XCTAssertNotNil(emitter)
        }
    }

    func testKnownConfettiIDsResolveNonEmptyColorSequences() {
        let ids = [
            "confettiStars",
            "confettiSpark",
            "confettiGarden",
            "confettiCandy"
        ]

        for id in ids {
            XCTAssertFalse(TRConfettiScene.colors(forConfettiID: id).isEmpty)
        }
    }

    func testSuccessModeAcceptsSelectedConfettiOption() throws {
        let option = try XCTUnwrap(ShopCatalogService().option(withID: "confettiCandy"))
        let scene = TRConfettiScene(size: CGSize(width: 390, height: 844))

        let result = scene.play(
            mode: .success,
            reduceMotion: false,
            selectedConfettiOption: option
        )

        XCTAssertEqual(result, .played)
        XCTAssertEqual(scene.children.count, 3)
    }
}
