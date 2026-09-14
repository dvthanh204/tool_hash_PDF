import SwiftUI
import UniformTypeIdentifiers

struct MainView: View {
    @EnvironmentObject var licenseManager: LicenseManager
    @State private var documentData: Data? = nil
    
    var body: some View {
        VStack {
            if let data = documentData {
                PDFImageViewer(pdfData: data)
            } else {
                VStack(spacing: 20) {
                    Image(systemName: "doc.text.magnifyingglass")
                        .resizable()
                        .frame(width: 100, height: 100)
                        .foregroundColor(.gray)
                    
                    Text("Chưa có tài liệu mã hóa (.khoa) nào được mở")
                        .font(.title)
                        .foregroundColor(.gray)
                        
                    Button("Mở File") {
                        openKhoaFile()
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
        }
        .frame(minWidth: 800, minHeight: 600)
        .toolbar {
            ToolbarItem(placement: .navigation) {
                Button("Mở File Khác") {
                    openKhoaFile()
                }
            }
            ToolbarItem(placement: .automatic) {
                Button(action: {
                    printDocument()
                }) {
                    Label("In Qua CUPS", systemName: "printer")
                }
                .disabled(!(licenseManager.currentLicense?.can_print ?? false) || documentData == nil)
            }
        }
    }
    
    func openKhoaFile() {
        let panel = NSOpenPanel()
        // Allow .khoa extensions
        let khoaType = UTType(filenameExtension: "khoa") ?? UTType.data
        panel.allowedContentTypes = [khoaType]
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        
        if panel.runModal() == .OK, let url = panel.url {
            if let data = PackageReader.readKhoaFile(url: url) {
                self.documentData = data
            } else {
                print("Lỗi giải mã file")
            }
        }
    }
    
    func printDocument() {
        guard let data = documentData else { return }
        // Lưu tạm PDF thô (hoặc PDF chứa Image an toàn hơn) ra /tmp để dùng lệnh lp
        let tempUrl = URL(fileURLWithPath: "/tmp/print_temp_\(UUID().uuidString).pdf")
        do {
            try data.write(to: tempUrl)
            
            let task = Process()
            task.launchPath = "/usr/bin/lp"
            task.arguments = [tempUrl.path]
            task.launch()
            task.waitUntilExit() // Đợi in xong
            
            // Xóa file đệm ngay lập tức
            try FileManager.default.removeItem(at: tempUrl)
        } catch {
            print("Print error: \(error)")
        }
    }
}
