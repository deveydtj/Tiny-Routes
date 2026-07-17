import Foundation

enum RouteObjectiveKind: String, Codable, CaseIterable {
    case pickup
    case checkpoint
    case delivery
    case destination
}

/// A JSON value used to preserve schema extensions in objective documents.
enum RouteObjectiveJSONValue: Codable, Equatable {
    case string(String)
    case integer(Int)
    case number(Double)
    case boolean(Bool)
    case object([String: RouteObjectiveJSONValue])
    case array([RouteObjectiveJSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .boolean(value)
        } else if let value = try? container.decode(Int.self) {
            self = .integer(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([String: RouteObjectiveJSONValue].self) {
            self = .object(value)
        } else if let value = try? container.decode([RouteObjectiveJSONValue].self) {
            self = .array(value)
        } else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unsupported JSON value in route objective"
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value):
            try container.encode(value)
        case .integer(let value):
            try container.encode(value)
        case .number(let value):
            try container.encode(value)
        case .boolean(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }
}

/// A stable, ordered stop in a schema-3 route.
struct RouteObjective: Codable, Equatable {
    static let legacyPickupID = "legacy_pickup"
    static let legacyDestinationID = "legacy_destination"

    var id: String
    var nodeID: String
    var kind: RouteObjectiveKind
    var sequenceIndex: Int
    var revealPolicy: String
    var displayMetadata: [String: RouteObjectiveJSONValue]?
    var additionalFields: [String: RouteObjectiveJSONValue]

    private var displayMetadataWasPresent: Bool

    init(
        id: String,
        nodeID: String,
        kind: RouteObjectiveKind,
        sequenceIndex: Int,
        revealPolicy: String,
        displayMetadata: [String: RouteObjectiveJSONValue]? = nil,
        additionalFields: [String: RouteObjectiveJSONValue] = [:]
    ) {
        self.id = id
        self.nodeID = nodeID
        self.kind = kind
        self.sequenceIndex = sequenceIndex
        self.revealPolicy = revealPolicy
        self.displayMetadata = displayMetadata
        self.additionalFields = additionalFields
        displayMetadataWasPresent = displayMetadata != nil
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: RouteObjectiveCodingKey.self)
        id = try container.decode(String.self, forKey: .id)
        nodeID = try container.decode(String.self, forKey: .nodeID)
        kind = try container.decode(RouteObjectiveKind.self, forKey: .kind)
        sequenceIndex = try container.decode(Int.self, forKey: .sequenceIndex)
        revealPolicy = try container.decode(String.self, forKey: .revealPolicy)
        displayMetadataWasPresent = container.contains(.displayMetadata)
        displayMetadata = try container.decodeIfPresent(
            [String: RouteObjectiveJSONValue].self,
            forKey: .displayMetadata
        )

        let knownKeys = Set(RouteObjectiveCodingKey.knownKeys.map(\.stringValue))
        additionalFields = try container.allKeys.reduce(into: [:]) { fields, key in
            guard !knownKeys.contains(key.stringValue) else { return }
            fields[key.stringValue] = try container.decode(RouteObjectiveJSONValue.self, forKey: key)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: RouteObjectiveCodingKey.self)
        let knownKeys = Set(RouteObjectiveCodingKey.knownKeys.map(\.stringValue))
        for (name, value) in additionalFields where !knownKeys.contains(name) {
            guard let key = RouteObjectiveCodingKey(stringValue: name) else { continue }
            try container.encode(value, forKey: key)
        }
        try container.encode(id, forKey: .id)
        try container.encode(nodeID, forKey: .nodeID)
        try container.encode(kind, forKey: .kind)
        try container.encode(sequenceIndex, forKey: .sequenceIndex)
        try container.encode(revealPolicy, forKey: .revealPolicy)
        if displayMetadataWasPresent || displayMetadata != nil {
            try container.encodeIfPresent(displayMetadata, forKey: .displayMetadata)
            if displayMetadata == nil {
                try container.encodeNil(forKey: .displayMetadata)
            }
        }
    }

    static func legacySequence(
        packageNodeID: String,
        destinationNodeID: String
    ) -> [RouteObjective] {
        [
            RouteObjective(
                id: legacyPickupID,
                nodeID: packageNodeID,
                kind: .pickup,
                sequenceIndex: 0,
                revealPolicy: "always"
            ),
            RouteObjective(
                id: legacyDestinationID,
                nodeID: destinationNodeID,
                kind: .destination,
                sequenceIndex: 1,
                revealPolicy: "whenActive"
            )
        ]
    }
}

struct RouteObjectiveValidationIssue: Equatable {
    let code: String
    let message: String
    let objectiveID: String?
    let nodeID: String?

    init(code: String, message: String, objectiveID: String? = nil, nodeID: String? = nil) {
        self.code = code
        self.message = message
        self.objectiveID = objectiveID
        self.nodeID = nodeID
    }
}

private struct RouteObjectiveCodingKey: CodingKey, Hashable {
    let stringValue: String
    let intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        intValue = nil
    }

    init?(intValue: Int) {
        stringValue = String(intValue)
        self.intValue = intValue
    }

    static let id = required("id")
    static let nodeID = required("nodeID")
    static let kind = required("kind")
    static let sequenceIndex = required("sequenceIndex")
    static let revealPolicy = required("revealPolicy")
    static let displayMetadata = required("displayMetadata")

    static let knownKeys = [id, nodeID, kind, sequenceIndex, revealPolicy, displayMetadata]

    private static func required(_ value: String) -> RouteObjectiveCodingKey {
        RouteObjectiveCodingKey(stringValue: value)!
    }
}
