import Foundation

struct GameplayCosmeticLoadout: Equatable {
    let routeThemeID: String
    let deliveryDotID: String
    let trailID: String
    let confettiID: String
    let destinationID: String

    let routeTheme: ShopCosmeticOption
    let deliveryDot: ShopCosmeticOption
    let trail: ShopCosmeticOption
    let confetti: ShopCosmeticOption
    let destination: ShopCosmeticOption

    init(
        routeTheme: ShopCosmeticOption,
        deliveryDot: ShopCosmeticOption,
        trail: ShopCosmeticOption,
        confetti: ShopCosmeticOption,
        destination: ShopCosmeticOption
    ) {
        self.routeThemeID = routeTheme.id
        self.deliveryDotID = deliveryDot.id
        self.trailID = trail.id
        self.confettiID = confetti.id
        self.destinationID = destination.id
        self.routeTheme = routeTheme
        self.deliveryDot = deliveryDot
        self.trail = trail
        self.confetti = confetti
        self.destination = destination
    }

    init(
        routeThemeID: String,
        deliveryDotID: String,
        trailID: String,
        confettiID: String,
        destinationID: String,
        routeTheme: ShopCosmeticOption,
        deliveryDot: ShopCosmeticOption,
        trail: ShopCosmeticOption,
        confetti: ShopCosmeticOption,
        destination: ShopCosmeticOption
    ) {
        self.routeThemeID = routeThemeID
        self.deliveryDotID = deliveryDotID
        self.trailID = trailID
        self.confettiID = confettiID
        self.destinationID = destinationID
        self.routeTheme = routeTheme
        self.deliveryDot = deliveryDot
        self.trail = trail
        self.confetti = confetti
        self.destination = destination
    }

    static let `default` = GameplayCosmeticLoadout(
        routeTheme: defaultOption(
            categoryID: ShopCosmeticCategoryID.routeThemes,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.routeThemes] ?? "themeOceanDrive"
        ),
        deliveryDot: defaultOption(
            categoryID: ShopCosmeticCategoryID.deliveryDots,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.deliveryDots] ?? "dotCourierBlue"
        ),
        trail: defaultOption(
            categoryID: ShopCosmeticCategoryID.trails,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.trails] ?? "trailClean"
        ),
        confetti: defaultOption(
            categoryID: ShopCosmeticCategoryID.confetti,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.confetti] ?? "confettiStars"
        ),
        destination: defaultOption(
            categoryID: ShopCosmeticCategoryID.destinations,
            defaultID: PlayerProfile.defaultSelectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.destinations] ?? "destinationFlag"
        )
    )

    private static func defaultOption(categoryID: String, defaultID: String) -> ShopCosmeticOption {
        let catalogService = ShopCatalogService()
        if let option = catalogService.option(withID: defaultID), option.categoryID == categoryID {
            return option
        }

        if let option = catalogService.options(forCategoryID: categoryID).first {
            return option
        }

        return ShopCosmeticOption(
            id: defaultID,
            categoryID: categoryID,
            title: "Default",
            price: nil,
            isUnlocked: true,
            isSelected: true,
            accent: .classic
        )
    }
}
