import SwiftUI
import XCTest
@testable import TinyRoutes

final class TRGameplayStyleTests: XCTestCase {
    func testPlayerCoreSizeTracksConfiguredWhiteRimWidth() {
        let expectedCoreSize = TRGameplayStyle.Metrics.playerOuterSize - (TRGameplayStyle.Metrics.playerWhiteRimWidth * 2)

        XCTAssertEqual(TRGameplayStyle.Metrics.playerCoreSize, expectedCoreSize, accuracy: 0.0001)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.playerCoreSize, 0)
    }

    func testPlayerScaleIsAboutTwentyFivePercentSmallerThanPreviousSize() {
        let previousPlayerScale: CGFloat = 0.75
        let expectedPlayerScale = previousPlayerScale * 0.75

        XCTAssertEqual(TRGameplayStyle.Metrics.playerScale, expectedPlayerScale, accuracy: 0.0001)
    }

    func testSwitchTapTargetIsLargerThanVisibleSwitch() {
        XCTAssertGreaterThanOrEqual(TRGameplayStyle.Metrics.switchTapTargetSize, 72)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.switchTapTargetSize, TRGameplayStyle.Metrics.switchNodeSize)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.switchTapTargetSize, TRGameplayStyle.Metrics.switchCircleSize)
    }

    func testPackageBadgeReadsAsSmallerObjectiveMarker() {
        XCTAssertLessThan(TRGameplayStyle.Metrics.packageBadgeSize, TRGameplayStyle.Metrics.switchCircleSize)
        XCTAssertLessThan(TRGameplayStyle.Metrics.packageBadgeIconSize, TRGameplayStyle.Metrics.packageBadgeSize)
        XCTAssertLessThan(TRGameplayStyle.Metrics.packageBadgeCornerRadius, TRGameplayStyle.Metrics.packageBadgeSize / 2)
    }

    func testResultMetricsArePositiveStaticValues() {
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.resultCardCornerRadius, 0)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.resultPrimaryButtonHeight, 0)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.resultSecondaryButtonHeight, 0)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.resultStatusBadgeSize, 0)
        XCTAssertGreaterThan(TRGameplayStyle.Metrics.resultLargeStarSize, 0)
    }

    func testGameplayCosmeticStyleMapsForestPathToForestRouteColors() throws {
        let routeTheme = try XCTUnwrap(ShopCatalogService().option(withID: "themeForestPath"))
        let loadout = GameplayCosmeticLoadout(
            routeTheme: routeTheme,
            deliveryDot: GameplayCosmeticLoadout.default.deliveryDot,
            trail: GameplayCosmeticLoadout.default.trail,
            confetti: GameplayCosmeticLoadout.default.confetti,
            destination: GameplayCosmeticLoadout.default.destination
        )
        let style = TRGameplayCosmeticStyle(loadout: loadout)

        assertColor(style.roadFillColor, matches: ShopCosmeticAccent.forestPath.routeColor)
        assertColor(style.roadEdgeColor, matches: ShopCosmeticAccent.forestPath.routeShadowColor)
    }

    func testNeonNightsRoadFillDiffersFromDefaultOceanRoute() throws {
        let neonTheme = try XCTUnwrap(ShopCatalogService().option(withID: "themeNeonNights"))
        let neonLoadout = GameplayCosmeticLoadout(
            routeTheme: neonTheme,
            deliveryDot: GameplayCosmeticLoadout.default.deliveryDot,
            trail: GameplayCosmeticLoadout.default.trail,
            confetti: GameplayCosmeticLoadout.default.confetti,
            destination: GameplayCosmeticLoadout.default.destination
        )

        let neonColor = rgbaComponents(TRGameplayCosmeticStyle(loadout: neonLoadout).roadFillColor)
        let oceanColor = rgbaComponents(TRGameplayCosmeticStyle(loadout: .default).roadFillColor)

        XCTAssertFalse(
            neonColor.red == oceanColor.red
                && neonColor.green == oceanColor.green
                && neonColor.blue == oceanColor.blue
                && neonColor.alpha == oceanColor.alpha
        )
    }

    func testDefaultGameplayCosmeticStyleUsesDefaultRouteTheme() {
        let style = TRGameplayCosmeticStyle(loadout: .default)

        assertColor(style.roadFillColor, matches: ShopCosmeticAccent.oceanDrive.routeColor)
    }

    private func assertColor(_ color: Color, matches expectedColor: Color, file: StaticString = #filePath, line: UInt = #line) {
        let components = rgbaComponents(color)
        let expectedComponents = rgbaComponents(expectedColor)

        XCTAssertEqual(components.red, expectedComponents.red, accuracy: 0.001, file: file, line: line)
        XCTAssertEqual(components.green, expectedComponents.green, accuracy: 0.001, file: file, line: line)
        XCTAssertEqual(components.blue, expectedComponents.blue, accuracy: 0.001, file: file, line: line)
        XCTAssertEqual(components.alpha, expectedComponents.alpha, accuracy: 0.001, file: file, line: line)
    }

    private func rgbaComponents(_ color: Color) -> (red: CGFloat, green: CGFloat, blue: CGFloat, alpha: CGFloat) {
        let uiColor = UIColor(color)
        var red: CGFloat = 0
        var green: CGFloat = 0
        var blue: CGFloat = 0
        var alpha: CGFloat = 0
        uiColor.getRed(&red, green: &green, blue: &blue, alpha: &alpha)
        return (red, green, blue, alpha)
    }
}
