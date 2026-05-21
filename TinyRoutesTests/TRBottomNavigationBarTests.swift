import XCTest
@testable import TinyRoutes

final class TRBottomNavigationBarTests: XCTestCase {
    func testBottomTabAllCasesAreInExpectedOrder() {
        XCTAssertEqual(TRBottomTab.allCases, [.home, .levels, .shop, .profile])
    }

    func testBottomTabTitlesMatchExpectedValues() {
        XCTAssertEqual(TRBottomTab.home.title, "Home")
        XCTAssertEqual(TRBottomTab.levels.title, "Levels")
        XCTAssertEqual(TRBottomTab.shop.title, "Shop")
        XCTAssertEqual(TRBottomTab.profile.title, "Profile")
    }

    func testBottomTabSystemImagesAreNonEmpty() {
        for tab in TRBottomTab.allCases {
            XCTAssertFalse(tab.systemImage.isEmpty)
        }
    }

    @MainActor
    func testSelectTabHomeMapsToMainMenu() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.home)
        XCTAssertEqual(coordinator.state, .mainMenu)
    }

    @MainActor
    func testSelectTabLevelsMapsToLevelSelect() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.levels)
        XCTAssertEqual(coordinator.state, .levelSelect)
    }

    @MainActor
    func testSelectTabShopMapsToShop() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.shop)
        XCTAssertEqual(coordinator.state, .shop)
    }

    @MainActor
    func testSelectTabProfileMapsToSettings() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.profile)
        XCTAssertEqual(coordinator.state, .settings)
    }
}
