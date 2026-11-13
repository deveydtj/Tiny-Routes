import Foundation

enum MultiVanStars {
    static func rating(changes: Int, par: Int) -> Int {
        if changes <= par { return 3 }
        if changes <= par + 2 { return 2 }
        return 1
    }
}

struct MultiVanLevel: Decodable {
    let id: String
    let name: String
    let graph: RouteGraph
    let vans: [MultiVanVan]
    let houses: [MultiVanHouse]
    let initialSwitchEdges: [String: String]
    let parChanges: Int
    let liveSwitchNodeIDs: [String]
    let hint: String?
    /// Explains a mechanic the first time the player meets it.
    let tutorial: [MultiVanTutorialTip]
    /// Lays out the diorama's lawn and scenery. Defaults to the level's number;
    /// a level that moved keeps the seed of its old number, and so its look.
    let scenerySeed: Int
    /// The content features this file uses; see `supportedSchemaVersion`.
    let schemaVersion: Int
    /// Parcels a van collects on the way home. Empty on a delivery-only board.
    let packages: [MultiVanPackage]
    /// Switches the second step of help rings; see `MultiVanAssistance`.
    let hintFocusNodeIDs: [String]
    /// The chapter's look. Art only: it never changes a rule.
    let biome: MultiVanBiome
    /// Automatic lights and bridges that hold vans at a stop line.
    let signals: [MultiVanSignal]
    /// Stretches of road that change how a van drives; see `MultiVanRoadZone`.
    let roadZones: [MultiVanRoadZone]

    /// Files without a version are 1: forks, houses and live switches. 2 adds
    /// packages; 3 adds signals and road zones. A newer file is refused rather
    /// than played with its rules missing.
    static let supportedSchemaVersion = 3

    private enum CodingKeys: String, CodingKey {
        case id, name, graph, vans, houses, initialSwitchEdges, parChanges, liveSwitchNodeIDs, hint, tutorial, scenerySeed
        case schemaVersion, packages, hintFocusNodeIDs, biome, signals, roadZones
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        graph = try container.decode(RouteGraph.self, forKey: .graph)
        vans = try container.decode([MultiVanVan].self, forKey: .vans)
        houses = try container.decode([MultiVanHouse].self, forKey: .houses)
        initialSwitchEdges = try container.decode([String: String].self, forKey: .initialSwitchEdges)
        parChanges = try container.decode(Int.self, forKey: .parChanges)
        liveSwitchNodeIDs = try container.decodeIfPresent([String].self, forKey: .liveSwitchNodeIDs) ?? []
        hint = try container.decodeIfPresent(String.self, forKey: .hint)
        tutorial = try container.decodeIfPresent([MultiVanTutorialTip].self, forKey: .tutorial) ?? []
        scenerySeed = try container.decodeIfPresent(Int.self, forKey: .scenerySeed) ?? Int(id.filter(\.isNumber)) ?? 0
        schemaVersion = try container.decodeIfPresent(Int.self, forKey: .schemaVersion) ?? 1
        packages = try container.decodeIfPresent([MultiVanPackage].self, forKey: .packages) ?? []
        hintFocusNodeIDs = try container.decodeIfPresent([String].self, forKey: .hintFocusNodeIDs) ?? []
        biome = try container.decodeIfPresent(MultiVanBiome.self, forKey: .biome) ?? .meadow
        signals = try container.decodeIfPresent([MultiVanSignal].self, forKey: .signals) ?? []
        roadZones = try container.decodeIfPresent([MultiVanRoadZone].self, forKey: .roadZones) ?? []

        func refuse(_ key: CodingKeys, _ message: String) -> DecodingError {
            .dataCorruptedError(forKey: key, in: container, debugDescription: "\(id): \(message)")
        }
        guard (1...Self.supportedSchemaVersion).contains(schemaVersion) else {
            throw refuse(.schemaVersion, "schema version \(schemaVersion) is not supported (1 to \(Self.supportedSchemaVersion))")
        }
        if !packages.isEmpty, schemaVersion < 2 {
            throw refuse(.packages, "packages need schemaVersion 2")
        }
        if !signals.isEmpty, schemaVersion < 3 {
            throw refuse(.signals, "signals need schemaVersion 3")
        }
        if !roadZones.isEmpty, schemaVersion < 3 {
            throw refuse(.roadZones, "road zones need schemaVersion 3")
        }
    }

    /// The parcels `vanID` must collect before home, in authored order.
    func packages(ownedBy vanID: String) -> [MultiVanPackage] {
        packages.filter { $0.ownerVanID == vanID }
    }

    func tutorialTip(for trigger: MultiVanTutorialTip.Trigger) -> MultiVanTutorialTip? {
        tutorial.first { $0.trigger == trigger }
    }
}

/// A short cue for practicing a mechanic on the board, or a tip after a crash.
struct MultiVanTutorialTip: Decodable, Equatable {
    enum Trigger: String, Decodable {
        /// When the level first opens, before anything moves.
        case start
        /// On the level's first crash, so the collision itself stays the surprise.
        case crash
    }

    enum Practice: String, Decodable {
        case deliver, route, stop, live
    }

    let trigger: Trigger
    let title: String
    let body: String
    let focusNodeIDs: [String]
    let practice: Practice?
    let practiceEdgeID: String?

    private enum CodingKeys: String, CodingKey {
        case trigger, title, body, focusNodeIDs, practice, practiceEdgeID
    }

    init(trigger: Trigger, title: String, body: String, focusNodeIDs: [String] = []) {
        self.trigger = trigger
        self.title = title
        self.body = body
        self.focusNodeIDs = focusNodeIDs
        practice = nil
        practiceEdgeID = nil
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        trigger = try container.decode(Trigger.self, forKey: .trigger)
        title = try container.decode(String.self, forKey: .title)
        body = try container.decode(String.self, forKey: .body)
        focusNodeIDs = try container.decodeIfPresent([String].self, forKey: .focusNodeIDs) ?? []
        practice = try container.decodeIfPresent(Practice.self, forKey: .practice)
        practiceEdgeID = try container.decodeIfPresent(String.self, forKey: .practiceEdgeID)
    }
}

enum VanColor: String, Decodable, CaseIterable {
    case red, blue, yellow, green

    var symbol: String {
        switch self {
        case .red: return "●"
        case .blue: return "▲"
        case .yellow: return "■"
        case .green: return "★"
        }
    }

    var displayName: String {
        rawValue.capitalized
    }

    var accessibilitySymbolName: String {
        switch self {
        case .red: "circle"
        case .blue: "triangle"
        case .yellow: "square"
        case .green: "star"
        }
    }
}

struct MultiVanVan: Decodable {
    let id: String
    let color: VanColor
    let startNodeID: String
    let departDelay: Double

    private enum CodingKeys: String, CodingKey {
        case id, color, startNodeID, departDelay
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        color = try container.decode(VanColor.self, forKey: .color)
        startNodeID = try container.decode(String.self, forKey: .startNodeID)
        departDelay = try container.decodeIfPresent(Double.self, forKey: .departDelay) ?? 0
    }
}

struct MultiVanHouse: Decodable {
    let nodeID: String
    let color: VanColor
}

/// Pass a copy to the engine so tuning can change without mutable global state.
struct MultiVanTuning {
    static let `default` = MultiVanTuning()

    var vanSpeed = 1.5
    var stepDuration = 1.0 / 120.0
    var crashDistance = 0.35
    var liveSwitchLockRadius = 0.4
    var previewEdgeLimit = 40
    var failFreezeDuration = 0.6
    var fastForwardMultiplier = 2.0
    var gridColumns = 5
    var gridRows = 7
}
