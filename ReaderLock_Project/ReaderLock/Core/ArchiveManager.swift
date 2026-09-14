import Foundation


struct ArchivedPDF: Hashable {
    let name: String
    let data: Data
}

struct ArchiveManager {
    // Đọc hoàn toàn trên RAM
    static func extractInMemory(zipData: Data) -> (pdfs: [ArchivedPDF], revocations: [String]) {
        var pdfs: [ArchivedPDF] = []
        var revocations: [String] = []
        
        guard let archive = Archive(data: zipData, accessMode: .read) else {
            return (pdfs, revocations)
        }
        
        for entry in archive {
            var entryData = Data()
            do {
                _ = try archive.extract(entry) { data in
                    entryData.append(data)
                }
                
                if entry.path == "revocations.json" {
                    if let revList = try? JSONDecoder().decode([String].self, from: entryData) {
                        revocations = revList
                    }
                } else if entry.path.hasSuffix(".pdf") {
                    pdfs.append(ArchivedPDF(name: entry.path, data: entryData))
                }
            } catch {
                print("Lỗi giải nén file in-memory: \(error)")
            }
        }
        
        return (pdfs, revocations)
    }
}
