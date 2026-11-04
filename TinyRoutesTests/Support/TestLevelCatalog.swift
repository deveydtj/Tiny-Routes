import Foundation
@testable import TinyRoutes

struct TestLevelCatalog {
    private let decoder = JSONDecoder()

    func loadLevel(levelID: String, from directory: URL) throws -> LevelData {
        let url = directory.appendingPathComponent("\(levelID).json")
        let data = try Data(contentsOf: url)
        return try decoder.decode(LevelData.self, from: data)
    }
}
