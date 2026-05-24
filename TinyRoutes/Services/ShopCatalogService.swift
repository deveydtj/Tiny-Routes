import Foundation

struct ShopCatalogService {
    let featuredOffers: [ShopFeaturedOffer]
    let categories: [ShopCosmeticCategory]
    let cosmeticOptions: [ShopCosmeticOption]
    let goodieActions: [ShopGoodieAction]

    init(
        featuredOffers: [ShopFeaturedOffer] = Self.defaultFeaturedOffers,
        categories: [ShopCosmeticCategory] = Self.defaultCategories,
        cosmeticOptions: [ShopCosmeticOption] = Self.defaultCosmeticOptions,
        goodieActions: [ShopGoodieAction] = Self.defaultGoodieActions
    ) {
        self.featuredOffers = featuredOffers
        self.categories = categories
        self.cosmeticOptions = cosmeticOptions
        self.goodieActions = goodieActions
    }

    func options(forCategoryID categoryID: String) -> [ShopCosmeticOption] {
        cosmeticOptions.filter { $0.categoryID == categoryID }
    }
}

private extension ShopCatalogService {
    static let defaultFeaturedOffers = [
        ShopFeaturedOffer(
            id: "starterPack",
            title: "Starter Pack",
            subtitle: "Coins, gems, and bonus delivery goodies.",
            badgeText: "Best Value",
            displayPrice: "$2.99",
            style: .starterPack
        ),
        ShopFeaturedOffer(
            id: "removeAds",
            title: "Remove Ads",
            subtitle: "Keep every route clean and uninterrupted.",
            badgeText: nil,
            displayPrice: "$2.49",
            style: .removeAds
        )
    ]

    static let defaultCategories = [
        ShopCosmeticCategory(
            id: ShopCosmeticCategoryID.routeThemes,
            title: "Route Themes",
            systemImage: "paintbrush.fill"
        ),
        ShopCosmeticCategory(
            id: ShopCosmeticCategoryID.deliveryDots,
            title: "Delivery Dots",
            systemImage: "circle.fill"
        ),
        ShopCosmeticCategory(
            id: ShopCosmeticCategoryID.trails,
            title: "Trails",
            systemImage: "sparkles"
        ),
        ShopCosmeticCategory(
            id: ShopCosmeticCategoryID.confetti,
            title: "Confetti",
            systemImage: "party.popper.fill"
        ),
        ShopCosmeticCategory(
            id: ShopCosmeticCategoryID.destinations,
            title: "Destinations",
            systemImage: "mappin.circle.fill"
        )
    ]

    static let defaultCosmeticOptions = [
        ShopCosmeticOption(
            id: "themeClassic",
            categoryID: ShopCosmeticCategoryID.routeThemes,
            title: "Classic",
            price: nil,
            isUnlocked: true,
            isSelected: false,
            accent: .classic
        ),
        ShopCosmeticOption(
            id: "themeOceanDrive",
            categoryID: ShopCosmeticCategoryID.routeThemes,
            title: "Ocean Drive",
            price: nil,
            isUnlocked: true,
            isSelected: true,
            accent: .oceanDrive
        ),
        ShopCosmeticOption(
            id: "themeForestPath",
            categoryID: ShopCosmeticCategoryID.routeThemes,
            title: "Forest Path",
            price: 500,
            isUnlocked: false,
            isSelected: false,
            accent: .forestPath
        ),
        ShopCosmeticOption(
            id: "themeSunsetBlvd",
            categoryID: ShopCosmeticCategoryID.routeThemes,
            title: "Sunset Blvd",
            price: 500,
            isUnlocked: false,
            isSelected: false,
            accent: .sunsetBlvd
        ),
        ShopCosmeticOption(
            id: "themeNeonNights",
            categoryID: ShopCosmeticCategoryID.routeThemes,
            title: "Neon Nights",
            price: 750,
            isUnlocked: false,
            isSelected: false,
            accent: .neonNights
        ),
        ShopCosmeticOption(
            id: "themeCandyLane",
            categoryID: ShopCosmeticCategoryID.routeThemes,
            title: "Candy Lane",
            price: 750,
            isUnlocked: false,
            isSelected: false,
            accent: .candyLane
        ),
        ShopCosmeticOption(
            id: "dotCourierBlue",
            categoryID: ShopCosmeticCategoryID.deliveryDots,
            title: "Courier Blue",
            price: nil,
            isUnlocked: true,
            isSelected: true,
            accent: .oceanDrive
        ),
        ShopCosmeticOption(
            id: "dotGarden",
            categoryID: ShopCosmeticCategoryID.deliveryDots,
            title: "Garden",
            price: 300,
            isUnlocked: false,
            isSelected: false,
            accent: .forestPath
        ),
        ShopCosmeticOption(
            id: "dotGolden",
            categoryID: ShopCosmeticCategoryID.deliveryDots,
            title: "Golden",
            price: 450,
            isUnlocked: false,
            isSelected: false,
            accent: .sunsetBlvd
        ),
        ShopCosmeticOption(
            id: "dotCandy",
            categoryID: ShopCosmeticCategoryID.deliveryDots,
            title: "Candy",
            price: 450,
            isUnlocked: false,
            isSelected: false,
            accent: .candyLane
        ),
        ShopCosmeticOption(
            id: "trailClean",
            categoryID: ShopCosmeticCategoryID.trails,
            title: "Clean Line",
            price: nil,
            isUnlocked: true,
            isSelected: true,
            accent: .classic
        ),
        ShopCosmeticOption(
            id: "trailBubbles",
            categoryID: ShopCosmeticCategoryID.trails,
            title: "Bubbles",
            price: 350,
            isUnlocked: false,
            isSelected: false,
            accent: .oceanDrive
        ),
        ShopCosmeticOption(
            id: "trailFireflies",
            categoryID: ShopCosmeticCategoryID.trails,
            title: "Fireflies",
            price: 500,
            isUnlocked: false,
            isSelected: false,
            accent: .forestPath
        ),
        ShopCosmeticOption(
            id: "trailNeon",
            categoryID: ShopCosmeticCategoryID.trails,
            title: "Neon Glow",
            price: 650,
            isUnlocked: false,
            isSelected: false,
            accent: .neonNights
        ),
        ShopCosmeticOption(
            id: "confettiStars",
            categoryID: ShopCosmeticCategoryID.confetti,
            title: "Stars",
            price: nil,
            isUnlocked: true,
            isSelected: true,
            accent: .sunsetBlvd
        ),
        ShopCosmeticOption(
            id: "confettiSpark",
            categoryID: ShopCosmeticCategoryID.confetti,
            title: "Spark Pop",
            price: 250,
            isUnlocked: false,
            isSelected: false,
            accent: .oceanDrive
        ),
        ShopCosmeticOption(
            id: "confettiGarden",
            categoryID: ShopCosmeticCategoryID.confetti,
            title: "Leaves",
            price: 350,
            isUnlocked: false,
            isSelected: false,
            accent: .forestPath
        ),
        ShopCosmeticOption(
            id: "confettiCandy",
            categoryID: ShopCosmeticCategoryID.confetti,
            title: "Sugar Burst",
            price: 500,
            isUnlocked: false,
            isSelected: false,
            accent: .candyLane
        ),
        ShopCosmeticOption(
            id: "destinationFlag",
            categoryID: ShopCosmeticCategoryID.destinations,
            title: "Finish Flag",
            price: nil,
            isUnlocked: true,
            isSelected: true,
            accent: .classic
        ),
        ShopCosmeticOption(
            id: "destinationBeach",
            categoryID: ShopCosmeticCategoryID.destinations,
            title: "Beach Pin",
            price: 350,
            isUnlocked: false,
            isSelected: false,
            accent: .oceanDrive
        ),
        ShopCosmeticOption(
            id: "destinationCabin",
            categoryID: ShopCosmeticCategoryID.destinations,
            title: "Cabin",
            price: 500,
            isUnlocked: false,
            isSelected: false,
            accent: .forestPath
        ),
        ShopCosmeticOption(
            id: "destinationArcade",
            categoryID: ShopCosmeticCategoryID.destinations,
            title: "Arcade",
            price: 650,
            isUnlocked: false,
            isSelected: false,
            accent: .neonNights
        )
    ]

    static let defaultGoodieActions = [
        ShopGoodieAction(
            id: "coins",
            title: "Coins",
            subtitle: "Top up unlocks",
            buttonTitle: "Add",
            icon: .coins
        ),
        ShopGoodieAction(
            id: "gems",
            title: "Gems",
            subtitle: "Premium boosts",
            buttonTitle: "View",
            icon: .gems
        ),
        ShopGoodieAction(
            id: "dailyDeals",
            title: "Daily Deals",
            subtitle: "Fresh bundles",
            buttonTitle: "Open",
            icon: .dailyDeals
        ),
        ShopGoodieAction(
            id: "dailyBonus",
            title: "Daily Bonus",
            subtitle: "Claim rewards",
            buttonTitle: "Claim",
            icon: .dailyBonus
        )
    ]
}
