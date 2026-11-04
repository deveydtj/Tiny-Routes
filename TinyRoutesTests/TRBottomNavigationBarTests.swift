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
    func testSelectTabProfileShowsProfile() {
        let coordinator = AppCoordinator()
        coordinator.selectTab(.profile)
        XCTAssertEqual(coordinator.state, .profile)
    }

    @MainActor
    func testOpenProfileShowsProfile() {
        let coordinator = AppCoordinator()
        coordinator.openProfile()
        XCTAssertEqual(coordinator.state, .profile)
    }

    @MainActor
    func testOpenSettingsStillShowsSettings() {
        let coordinator = AppCoordinator()
        coordinator.openSettings()
        XCTAssertEqual(coordinator.state, .settings)
        XCTAssertNil(coordinator.selectedBottomTab)
    }

    @MainActor
    func testSelectedBottomTabIsProfileForProfileState() {
        let coordinator = AppCoordinator()
        coordinator.openProfile()
        XCTAssertEqual(coordinator.selectedBottomTab, .profile)
    }

    @MainActor
    func testCloseSettingsReturnsToLevelsWhenOpenedFromLevels() {
        let coordinator = AppCoordinator()
        coordinator.openLevelSelect()

        coordinator.openSettings()
        coordinator.closeSettings()

        XCTAssertEqual(coordinator.state, .levelSelect)
    }

    @MainActor
    func testCloseSettingsReturnsToShopWhenOpenedFromShop() {
        let coordinator = AppCoordinator()
        coordinator.openShop()

        coordinator.openSettings()
        coordinator.closeSettings()

        XCTAssertEqual(coordinator.state, .shop)
    }

    @MainActor
    func testCloseSettingsReturnsToProfileWhenOpenedFromProfile() {
        let coordinator = AppCoordinator()
        coordinator.openProfile()

        coordinator.openSettings()
        coordinator.closeSettings()

        XCTAssertEqual(coordinator.state, .profile)
    }

    @MainActor
    func testCloseSettingsFallsBackToMainMenuWhenOpenedFromInvalidState() {
        let coordinator = AppCoordinator()
        coordinator.startGameplay(levelID: PlayerProfile.firstLevelID)

        coordinator.openSettings()
        coordinator.closeSettings()

        XCTAssertEqual(coordinator.state, .mainMenu)
    }

    @MainActor
    func testSelectedBottomTabIsNilForNonTopLevelStates() {
        let coordinator = AppCoordinator()
        XCTAssertNil(coordinator.selectedBottomTab)

        coordinator.startGameplay(levelID: PlayerProfile.firstLevelID)
        XCTAssertNil(coordinator.selectedBottomTab)

        coordinator.openSettings()
        XCTAssertNil(coordinator.selectedBottomTab)
    }

    @MainActor
    func testExitingGameplayReturnsToLevelMap() {
        let coordinator = AppCoordinator()
        coordinator.startGameplay(levelID: PlayerProfile.firstLevelID)

        coordinator.exitGameplayToLevels()

        XCTAssertEqual(coordinator.state, .levelSelect)
        XCTAssertEqual(coordinator.selectedBottomTab, .levels)
    }
}
