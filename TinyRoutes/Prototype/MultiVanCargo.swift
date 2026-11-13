import Foundation

/// A parcel one van must collect before it goes home. The owner never changes;
/// colour and symbol on the board come from the owner, they are not keys.
struct MultiVanPackage: Decodable, Equatable {
    let id: String
    /// Where the parcel waits. The owner collects it on arriving at this node.
    let nodeID: String
    let ownerVanID: String
}

/// Where one parcel is in a run. The engine holds the only copy, keyed by
/// package ID; who carries it follows from the package's fixed owner.
enum MultiVanPackageState: Equatable {
    case atPickup, carried, delivered
}

/// One van's cargo, derived from its packages and their states.
enum MultiVanCargoStatus: Equatable {
    /// No parcels assigned: the van only has to reach its house.
    case ready
    /// Still has parcels to collect, in authored order.
    case pickupNeeded(remaining: [MultiVanPackage])
    /// Holds every parcel it needs.
    case carrying
    case delivered

    static func make(packages: [MultiVanPackage], states: [String: MultiVanPackageState]) -> Self {
        guard !packages.isEmpty else { return .ready }
        let remaining = packages.filter { states[$0.id] ?? .atPickup == .atPickup }
        if !remaining.isEmpty { return .pickupNeeded(remaining: remaining) }
        return packages.allSatisfy { states[$0.id] == .delivered } ? .delivered : .carrying
    }

    /// The words the chip, the board and VoiceOver share.
    var label: String {
        switch self {
        case .ready: "Ready to deliver"
        case .pickupNeeded(let remaining):
            remaining.count == 1 ? "Pickup needed" : "\(remaining.count) pickups needed"
        case .carrying: "Carrying"
        case .delivered: "Delivered"
        }
    }
}

/// Rules shared by the engine and the route preview, so a traced route collects
/// exactly what a driven one would.
enum MultiVanCargoRules {
    /// The most parcels one van may be assigned. A content limit, not something
    /// the player manages: there are no slots and no capacity to fill.
    static let maxPackagesPerVan = 2

    /// The parcels of `owned` that wait at `nodeID` and are not yet in `collected`.
    static func pickups(at nodeID: String, owned: [MultiVanPackage], collected: Set<String>) -> [MultiVanPackage] {
        owned.filter { $0.nodeID == nodeID && !collected.contains($0.id) }
    }

    /// The first parcel in authored order that `collected` lacks.
    static func firstMissing(owned: [MultiVanPackage], collected: Set<String>) -> MultiVanPackage? {
        owned.first { !collected.contains($0.id) }
    }
}

/// A level the engine cannot run. Thrown before play, never mid-run.
enum MultiVanLevelError: Error, LocalizedError, Equatable {
    case duplicateVan(String)
    case duplicatePackage(String)
    case emptyPackageID
    case packageOwnerMissing(packageID: String, vanID: String)
    case packageNodeMissing(packageID: String, nodeID: String)
    case tooManyPackages(vanID: String, count: Int)
    case unsupportedEdgeRule(edgeID: String)
    case invalidSignal(signalID: String, reason: String)
    case invalidRoadZone(zoneID: String, reason: String)

    var errorDescription: String? {
        switch self {
        case .duplicateVan(let id): "Two vans share the ID \(id)."
        case .duplicatePackage(let id): "Two packages share the ID \(id)."
        case .emptyPackageID: "A package has no ID."
        case let .packageOwnerMissing(packageID, vanID): "Package \(packageID) belongs to unknown van \(vanID)."
        case let .packageNodeMissing(packageID, nodeID): "Package \(packageID) waits at unknown node \(nodeID)."
        case let .tooManyPackages(vanID, count):
            "Van \(vanID) has \(count) packages; at most \(MultiVanCargoRules.maxPackagesPerVan) are supported."
        case .unsupportedEdgeRule(let edgeID): "Road \(edgeID) uses an availability rule Multi-Van does not run."
        case let .invalidSignal(signalID, reason): "Signal \(signalID): \(reason)."
        case let .invalidRoadZone(zoneID, reason): "Road zone \(zoneID): \(reason)."
        }
    }
}
