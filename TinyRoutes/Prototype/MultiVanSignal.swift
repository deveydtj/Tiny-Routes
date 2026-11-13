import Foundation

/// A chapter's look. Art and atmosphere only: no biome changes a rule, and an
/// unknown name falls back to the meadow so newer art never blocks a level.
enum MultiVanBiome: String, Decodable, CaseIterable {
    case meadow, depot, canal, oldTown, market, harbor, snow

    init(from decoder: Decoder) throws {
        self = Self(rawValue: try decoder.singleValueContainer().decode(String.self)) ?? .meadow
    }

    /// A wash laid over the meadow's lawn on both boards: its colour and strength.
    /// Nil keeps the meadow. Roads, vans, houses and parcels are never tinted.
    var groundWash: (hex: UInt32, opacity: Double)? {
        switch self {
        case .meadow: nil
        case .depot: (0xD9C7A3, 0.55)
        case .canal: (0x6FB7A8, 0.3)
        case .oldTown: (0xC9B79A, 0.6)
        case .market: (0xE0B48A, 0.5)
        case .harbor: (0x9CC7D8, 0.4)
        case .snow: (0xF4F8FB, 0.82)
        }
    }

    var displayName: String {
        switch self {
        case .meadow: "Meadow"
        case .depot: "Parcel Row"
        case .canal: "Canal Streets"
        case .oldTown: "Old Town"
        case .market: "Signal Square"
        case .harbor: "Harbor"
        case .snow: "Snowy Village"
        }
    }
}

/// One automatic light, or a drawbridge on a fixed cycle. It decides when a van
/// may enter its marked area; it never chooses where a van goes.
struct MultiVanSignal: Decodable, Equatable {
    enum Kind: String, Decodable {
        case trafficLight
        /// A bridge that lifts on the same schedule: every approach is one group.
        case drawbridge
    }

    struct Approach: Decodable, Equatable {
        /// The road a van arrives on.
        let edgeID: String
        /// How far along that road a held van stops.
        let stopDistance: Double
        /// Approaches in one group are let in together.
        let group: Int
    }

    struct Phase: Decodable, Equatable {
        /// The group that may enter; nil holds every approach.
        let group: Int?
        /// How long the phase lasts, in simulation steps.
        let ticks: Int
    }

    /// The area the signal protects. A van that has passed its stop line occupies
    /// the signal until it has been inside this circle and left it again.
    struct Area: Decodable, Equatable {
        let x: Double
        let y: Double
        let radius: Double
    }

    let id: String
    let kind: Kind
    let approaches: [Approach]
    let phases: [Phase]
    /// How far into the cycle the schedule stands at Go.
    let startTick: Int
    let area: Area

    private enum CodingKeys: String, CodingKey {
        case id, kind, approaches, phases, startTick, area
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        kind = try container.decodeIfPresent(Kind.self, forKey: .kind) ?? .trafficLight
        approaches = try container.decode([Approach].self, forKey: .approaches)
        phases = try container.decode([Phase].self, forKey: .phases)
        startTick = try container.decodeIfPresent(Int.self, forKey: .startTick) ?? 0
        area = try container.decode(Area.self, forKey: .area)
    }

    var cycleTicks: Int { phases.reduce(0) { $0 + max(0, $1.ticks) } }

    /// The group the fixed schedule lets in at `tick`. The schedule never drifts:
    /// a blocked green is shortened or missed, not moved.
    func nominalGroup(atTick tick: Int) -> Int? {
        let cycle = cycleTicks
        guard cycle > 0 else { return nil }
        var position = ((tick + startTick) % cycle + cycle) % cycle
        for phase in phases {
            if position < phase.ticks { return phase.group }
            position -= phase.ticks
        }
        return nil
    }

    /// Steps until the schedule next changes group, for a board's countdown ring.
    func ticksUntilChange(atTick tick: Int) -> Int {
        let cycle = cycleTicks
        guard cycle > 0 else { return 0 }
        var position = ((tick + startTick) % cycle + cycle) % cycle
        for phase in phases {
            if position < phase.ticks { return phase.ticks - position }
            position -= phase.ticks
        }
        return 0
    }

    /// Whether `group` may cross its stop line: the schedule shows it green and no
    /// van from another group is still inside. Vans already let in finish clearing.
    func admits(group: Int, atTick tick: Int, occupiedBy occupants: Set<Int>) -> Bool {
        nominalGroup(atTick: tick) == group && occupants.subtracting([group]).isEmpty
    }
}

/// What a board shows for one signal: the group that may really enter now.
struct MultiVanSignalState: Equatable {
    let signalID: String
    /// Nil while every approach is held, including a green blocked by a van still clearing.
    let openGroup: Int?
    /// A van is past a stop line and has not cleared the area.
    let isOccupied: Bool
}

/// A stretch of road that changes how a van drives it.
struct MultiVanRoadZone: Decodable, Equatable {
    enum Kind: String, Decodable {
        /// A van on ice cannot be re-routed: the switch at the end of the road
        /// stays locked from the moment a van drives onto it.
        case ice
    }

    let id: String
    let kind: Kind
    let edgeIDs: [String]
}
