import Foundation

/// Describes the data needed to load and run a single puzzle level.
struct LevelData: Identifiable, Codable {
    var schemaVersion: Int?
    var rules: LevelRules?
    let id: String
    var name: String
    var graph: RouteGraph
    var startNodeID: String
    var packageNodeID: String
    var destinationNodeID: String
    var timeLimitSeconds: Int
    var parTaps: Int
    var tutorialMessage: String?
    var objectives: [RouteObjective]?

    /// Rules used by runtime callers. Missing rules retain decode-and-replay
    /// compatibility for archived version-1 levels; production is version 2 only.
    var effectiveRules: LevelRules {
        rules ?? .legacyDefaults
    }

    /// Schema-1/2 package fields are exposed as ordered objectives internally,
    /// while schema-3 documents keep their authored objective sequence.
    var effectiveObjectives: [RouteObjective] {
        guard (schemaVersion ?? 1) >= 3 else {
            return RouteObjective.legacySequence(
                packageNodeID: packageNodeID,
                destinationNodeID: destinationNodeID
            )
        }
        return objectives ?? []
    }

    func validateObjectives() -> [RouteObjectiveValidationIssue] {
        let version = schemaVersion ?? 1
        guard version >= 3 else {
            guard objectives != nil else { return [] }
            return [RouteObjectiveValidationIssue(
                code: "objectives_require_schema_3",
                message: "The objectives field requires schemaVersion 3 or newer."
            )]
        }
        guard let objectives, !objectives.isEmpty else {
            return [RouteObjectiveValidationIssue(
                code: "schema_3_objectives_required",
                message: "Schema 3 levels must define at least one objective."
            )]
        }

        var issues: [RouteObjectiveValidationIssue] = []
        let nodeIDs = Set(graph.nodes.map(\.id))
        let groupedIDs = Dictionary(grouping: objectives.map(\.id), by: { $0 })

        for objective in objectives {
            if objective.id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                issues.append(RouteObjectiveValidationIssue(
                    code: "empty_objective_id",
                    message: "Objective IDs must not be empty.",
                    objectiveID: objective.id
                ))
            }
            if !nodeIDs.contains(objective.nodeID) {
                issues.append(RouteObjectiveValidationIssue(
                    code: "objective_node_not_found",
                    message: "Objective '\(objective.id)' references missing node '\(objective.nodeID)'.",
                    objectiveID: objective.id,
                    nodeID: objective.nodeID
                ))
            }
        }

        for objectiveID in groupedIDs.filter({ $0.value.count > 1 }).keys.sorted() {
            issues.append(RouteObjectiveValidationIssue(
                code: "duplicate_objective_id",
                message: "Objective ID '\(objectiveID)' is used more than once.",
                objectiveID: objectiveID
            ))
        }

        if objectives.map(\.sequenceIndex).sorted() != Array(0..<objectives.count) {
            issues.append(RouteObjectiveValidationIssue(
                code: "noncontiguous_objective_sequence_indices",
                message: "Objective sequenceIndex values must be contiguous and start at 0."
            ))
        }
        for (expectedIndex, objective) in objectives.enumerated()
            where objective.sequenceIndex != expectedIndex {
            issues.append(RouteObjectiveValidationIssue(
                code: "objective_array_order_mismatch",
                message: "Objective '\(objective.id)' must appear at sequence index \(objective.sequenceIndex).",
                objectiveID: objective.id
            ))
        }

        let terminals = objectives.filter { $0.kind == .destination }
        if terminals.count != 1 {
            issues.append(RouteObjectiveValidationIssue(
                code: "invalid_terminal_objective_count",
                message: "Schema 3 levels must define exactly one destination objective."
            ))
        } else if let terminal = terminals.first {
            if terminal.sequenceIndex != objectives.count - 1 {
                issues.append(RouteObjectiveValidationIssue(
                    code: "terminal_objective_not_final",
                    message: "Destination objective '\(terminal.id)' must be the final objective.",
                    objectiveID: terminal.id,
                    nodeID: terminal.nodeID
                ))
            }
            if terminal.nodeID != destinationNodeID {
                issues.append(RouteObjectiveValidationIssue(
                    code: "legacy_destination_objective_conflict",
                    message: "destinationNodeID must match the schema 3 destination objective nodeID.",
                    objectiveID: terminal.id,
                    nodeID: terminal.nodeID
                ))
            }
        }

        if let pickup = objectives
            .filter({ $0.kind == .pickup })
            .min(by: { $0.sequenceIndex < $1.sequenceIndex }),
           pickup.nodeID != packageNodeID {
            issues.append(RouteObjectiveValidationIssue(
                code: "legacy_package_objective_conflict",
                message: "packageNodeID must match the first schema 3 pickup objective nodeID.",
                objectiveID: pickup.id,
                nodeID: pickup.nodeID
            ))
        }

        return issues
    }

    init(
        schemaVersion: Int? = nil,
        rules: LevelRules? = nil,
        id: String,
        name: String,
        graph: RouteGraph,
        startNodeID: String,
        packageNodeID: String,
        destinationNodeID: String,
        timeLimitSeconds: Int,
        parTaps: Int,
        tutorialMessage: String? = nil,
        objectives: [RouteObjective]? = nil
    ) {
        self.schemaVersion = schemaVersion
        self.rules = rules
        self.id = id
        self.name = name
        self.graph = graph
        self.startNodeID = startNodeID
        self.packageNodeID = packageNodeID
        self.destinationNodeID = destinationNodeID
        self.timeLimitSeconds = timeLimitSeconds
        self.parTaps = parTaps
        self.tutorialMessage = tutorialMessage
        self.objectives = objectives
    }
}
