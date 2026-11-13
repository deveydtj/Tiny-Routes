import Foundation

struct MultiVanLevelRepository {
    private let bundle: Bundle

    init(bundle: Bundle = .main) {
        self.bundle = bundle
    }

    /// Returns an empty array when no prototype resources are bundled.
    /// Throws `LevelRepositoryError` for unreadable or malformed prototype files.
    func loadAllLevels() throws -> [MultiVanLevel] {
        try load(prefix: "level_")
    }

    /// Boards on trial: playable internally, never part of the campaign. They
    /// keep their own IDs, so a win here records no progress and earns nothing.
    func loadExperimentLevels() throws -> [MultiVanLevel] {
        try load(prefix: Self.experimentPrefix)
    }

    static let experimentPrefix = "experiment_"

    private func load(prefix: String) throws -> [MultiVanLevel] {
        let urls = bundle.urls(forResourcesWithExtension: "json", subdirectory: "PrototypeLevels") ?? []
        let decoder = JSONDecoder()
        return try urls.filter { $0.lastPathComponent.hasPrefix(prefix) }.map { url in
            let id = url.deletingPathExtension().lastPathComponent
            let data: Data
            do {
                data = try Data(contentsOf: url)
            } catch {
                throw LevelRepositoryError.readFailed(id: id, underlying: error)
            }
            do {
                return try decoder.decode(MultiVanLevel.self, from: data)
            } catch {
                throw LevelRepositoryError.decodingFailed(id: id, underlying: error)
            }
        }.sorted { $0.id < $1.id }
    }
}
