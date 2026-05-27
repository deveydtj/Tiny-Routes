import SwiftUI
import XCTest
@testable import TinyRoutes

final class TRMenuHeaderTests: XCTestCase {
    @MainActor
    func testMenuHeaderCanBeCreated() {
        let header = TRMenuHeader(
            pageTitle: "Levels",
            coinTotal: 1_250,
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )

        XCTAssertNotNil(header)
    }

    @MainActor
    func testMenuHeaderCanBeCreatedWithSubtitleOverride() {
        let header = TRMenuHeader(
            pageTitle: "Shop",
            subtitleOverride: "Customize your journey",
            coinTotal: 1_250,
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )

        XCTAssertNotNil(header)
    }

    @MainActor
    func testMenuSettingsButtonCanBeCreated() {
        let button = TRMenuSettingsButton(action: {})

        XCTAssertNotNil(button)
    }

    @MainActor
    func testMenuTitleLogoCanBeCreated() {
        let logo = TRMenuTitleLogo(
            pageTitle: "Shop",
            subtitleOverride: "Customize your journey"
        )

        XCTAssertNotNil(logo)
    }

    @MainActor
    func testShopScreenCanBeCreatedWithStandardHeaderInputs() {
        let screen = ShopScreen(
            coinTotal: 1_250,
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )

        XCTAssertNotNil(screen)
    }
}
