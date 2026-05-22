import XCTest
@testable import TinyRoutes

final class TRBottomNavigationBarTests: XCTestCase {
    func testAllCasesAreInExpectedOrder() {
        XCTAssertEqual(TRBottomTab.allCases, [.home, .levels, .shop, .profile])
    }

    func testTabTitles() {
        XCTAssertEqual(TRBottomTab.home.title, "Home")
        XCTAssertEqual(TRBottomTab.levels.title, "Levels")
        XCTAssertEqual(TRBottomTab.shop.title, "Shop")
        XCTAssertEqual(TRBottomTab.profile.title, "Profile")
    }

    func testTabSystemImagesAreNotEmpty() {
        for tab in TRBottomTab.allCases {
            XCTAssertFalse(tab.systemImage.isEmpty, "\(tab.title) should have an icon name")
        }
    }

    @MainActor
    func testSelectTabHomeShowsMainMenu() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.home)
        XCTAssertEqual(coordinator.state, .mainMenu)
    }

    @MainActor
    func testSelectTabLevelsShowsLevelSelect() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.levels)
        XCTAssertEqual(coordinator.state, .levelSelect)
    }

    @MainActor
    func testSelectTabShopShowsShop() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.shop)
        XCTAssertEqual(coordinator.state, .shop)
    }

    @MainActor
    func testSelectTabProfileShowsSettings() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.profile)
        XCTAssertEqual(coordinator.state, .settings)
    }

    @MainActor
    func testSelectedBottomTabIsNilForNonTopLevelStates() {
        let coordinator = AppCoordinator()
        XCTAssertNil(coordinator.selectedBottomTab)

        coordinator.startGameplay(levelID: "level_001")
        XCTAssertNil(coordinator.selectedBottomTab)

        coordinator.pauseGameplay()
        XCTAssertNil(coordinator.selectedBottomTab)

        coordinator.completeLevel(elapsedTime: 12, tapCount: 3)
        XCTAssertNil(coordinator.selectedBottomTab)

        coordinator.restartGameplay()
        coordinator.failLevel(reason: .timeExpired, elapsedTime: 45, tapCount: 5)
        XCTAssertNil(coordinator.selectedBottomTab)
    }
}
