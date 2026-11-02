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

    private enum CodingKeys: String, CodingKey {
        case id, name, graph, vans, houses, initialSwitchEdges, parChanges, liveSwitchNodeIDs, hint
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
    }
}

enum VanColor: String, Decodable {
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

#if DEBUG
import CoreFoundation

/// Only MV-45's three controls are persisted. Engines receive a value snapshot.
struct MultiVanPrototypeTuning {
    enum Parameter: String, CaseIterable {
        case vanSpeed, crashDistance, liveSwitchLockRadius

        var key: String { "multiVanPrototype.\(rawValue)" }

        var label: String {
            switch self {
            case .vanSpeed: "Van speed"
            case .crashDistance: "Collision distance"
            case .liveSwitchLockRadius: "Live-switch locking radius"
            }
        }

        var units: String { self == .vanSpeed ? "grid units/s" : "grid units" }

        // The source plan specifies defaults but no bounds. These are panel
        // limits for controlled playtests, not changes to engine rules.
        var range: ClosedRange<Double> {
            switch self {
            case .vanSpeed: 0.5...3
            case .crashDistance: 0.1...0.75
            case .liveSwitchLockRadius: 0...1
            }
        }

        var step: Double { self == .vanSpeed ? 0.1 : 0.05 }

        var keyPath: WritableKeyPath<MultiVanTuning, Double> {
            switch self {
            case .vanSpeed: \.vanSpeed
            case .crashDistance: \.crashDistance
            case .liveSwitchLockRadius: \.liveSwitchLockRadius
            }
        }

        var defaultValue: Double { MultiVanTuning.default[keyPath: keyPath] }
    }

    let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) { self.defaults = defaults }

    var tuning: MultiVanTuning {
        var result = MultiVanTuning.default
        for parameter in Parameter.allCases {
            guard let number = defaults.object(forKey: parameter.key) as? NSNumber,
                  CFGetTypeID(number) != CFBooleanGetTypeID() else { continue }
            let value = number.doubleValue
            guard value.isFinite, parameter.range.contains(value) else { continue }
            result[keyPath: parameter.keyPath] = value
        }
        return result
    }

    func set(_ value: Double, for parameter: Parameter) {
        guard value.isFinite, parameter.range.contains(value) else { return }
        if value == parameter.defaultValue {
            defaults.removeObject(forKey: parameter.key)
        } else {
            defaults.set(value, forKey: parameter.key)
        }
    }

    func reset() {
        for parameter in Parameter.allCases { defaults.removeObject(forKey: parameter.key) }
    }

    static func isDefault(_ tuning: MultiVanTuning) -> Bool {
        Parameter.allCases.allSatisfy { tuning[keyPath: $0.keyPath] == $0.defaultValue }
    }
}
#endif
