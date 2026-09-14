import os

base_dir = r"d:\code\python\too_hash_PDF_macOS\ReaderLock_Project\ReaderLock"

contents = {
"App/ReaderLockApp.swift": """import SwiftUI

@main
struct ReaderLockApp: App {
    @State private var isActivated: Bool = false
    
    var body: some Scene {
        WindowGroup {
            if isActivated {
                MainView()
                    .onAppear {
                        // Kỹ thuật Anti-Screen Capture (Chống quay phim / chụp ảnh)
                        if let window = NSApplication.shared.windows.first {
                            window.sharingType = .none
                        }
                    }
            } else {
                ActivationView(isActivated: $isActivated)
                    .onAppear {
                        // Kiểm tra License xem đã có trong UserDefaults chưa
                        if let key = UserDefaults.standard.string(forKey: "LicenseKey"),
                           CryptoManager.verifyLicense(key: key) {
                            self.isActivated = true
                        }
                    }
            }
        }
        // Vô hiệu hóa một số tính năng trong Menu hệ thống
        .commands {
            CommandGroup(replacing: .printItem) { }     // No Print
            CommandGroup(replacing: .saveItem) { }      // No Export / Save
        }
    }
}
""",

"Core/MachineID.swift": """import Foundation
import IOKit

struct MachineID {
    static func get() -> String {
        var serialNumber: String = "UNKNOWN"
        let platformExpert = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOPlatformExpertDevice"))
        
        if platformExpert != 0 {
            if let serial = IORegistryEntryCreateCFProperty(platformExpert, kIOPlatformSerialNumberKey as CFString, kCFAllocatorDefault, 0)?.takeUnretainedValue() as? String {
                serialNumber = serial
            }
            IOObjectRelease(platformExpert)
        }
        return serialNumber
    }
}
""",

"Core/CryptoManager.swift": """import Foundation
import CryptoKit

struct CryptoManager {
    static let staticKey = "12345678901234567890123456789012"
    
    static func verifyLicense(key: String) -> Bool {
        let mid = MachineID.get()
        let symmetricKey = SymmetricKey(data: Data(staticKey.utf8))
        
        // HMAC-SHA256 băm Machine ID
        let signature = HMAC<SHA256>.authenticationCode(for: Data(mid.utf8), using: symmetricKey)
        let signatureBase64 = Data(signature).base64EncodedString()
        
        return signatureBase64 == key
    }
    
    static func decryptPayload(data: Data) -> Data? {
        do {
            let key = SymmetricKey(data: Data(staticKey.utf8))
            // CryptoKit tự động phân tách phần Nonce 12-byte khởi đầu từ Combined Data
            let sealedBox = try AES.GCM.SealedBox(combined: data)
            let decryptedData = try AES.GCM.open(sealedBox, using: key)
            return decryptedData
        } catch {
            print("Lỗi giải mã AES-GCM: \\(error)")
            return nil
        }
    }
}
""",

"Core/ArchiveManager.swift": """import Foundation
import ZIPFoundation // Yêu cầu tích hợp thư viện này qua Swift Package Manager (SPM)

struct ArchivedPDF {
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
                print("Lỗi giải nén file in-memory: \\(error)")
            }
        }
        
        return (pdfs, revocations)
    }
}
""",

"Views/ActivationView.swift": """import SwiftUI

struct ActivationView: View {
    @Binding var isActivated: Bool
    @State private var licenseKey: String = ""
    @State private var showError = false
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "lock.laptopcomputer")
                .resizable()
                .scaledToFit()
                .frame(width: 80, height: 80)
                .foregroundColor(.blue)
            
            Text("Kích Hoạt Tài Liệu")
                .font(.title)
                .bold()
            
            Text("Máy của bạn là: \\(MachineID.get())")
                .font(.headline)
                .foregroundColor(.red)
                .textSelection(.enabled) // Cho phép copy mã thiết bị gửi Admin
            
            Text("Hãy nhập Key vào đây:")
            TextField("License Key...", text: $licenseKey)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .frame(width: 400)
            
            Button("KÍCH HOẠT") {
                let trimmedKey = licenseKey.trimmingCharacters(in: .whitespacesAndNewlines)
                if CryptoManager.verifyLicense(key: trimmedKey) {
                    UserDefaults.standard.set(trimmedKey, forKey: "LicenseKey")
                    isActivated = true
                } else {
                    showError = true
                }
            }
            .buttonStyle(.borderedProminent)
            .alert("Lỗi Kích Hoạt", isPresented: $showError) {
                Button("OK", role: .cancel) { }
            } message: {
                Text("License Key không đúng với máy này!")
            }
        }
        .frame(width: 600, height: 400)
    }
}
""",

"Views/MainView.swift": """import SwiftUI

struct MainView: View {
    @State private var pdfs: [ArchivedPDF] = []
    @State private var selectedPDF: ArchivedPDF?
    @State private var isBanned = false
    
    var body: some View {
        HStack(spacing: 0) {
            // Sidebar Menu
            List(pdfs, id: \\.name, selection: $selectedPDF) { pdf in
                Text(pdf.name)
                    .tag(pdf)
            }
            .listStyle(SidebarListStyle())
            .frame(width: 200)
            
            // Content
            if isBanned {
                VStack {
                    Image(systemName: "xmark.octagon.fill")
                        .resizable().frame(width: 100, height: 100).foregroundColor(.red)
                    Text("Thiết bị này đã bị Admin khóa quyền truy cập!")
                        .font(.title).padding()
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                if let pdf = selectedPDF {
                    ProtectedPDFViewer(pdfData: pdf.data)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text("Vui lòng chọn PDF ở menu bên trái")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .onAppear {
            loadBundleData()
        }
    }
    
    func loadBundleData() {
        guard let url = Bundle.main.url(forResource: "tailieu", withExtension: "khoa") else {
            print("Không tìm thấy file tailieu.khoa")
            return
        }
        
        do {
            let encryptedData = try Data(contentsOf: url)
            if let decryptedZip = CryptoManager.decryptPayload(data: encryptedData) {
                let archiveData = ArchiveManager.extractInMemory(zipData: decryptedZip)
                let myMid = MachineID.get()
                
                if archiveData.revocations.contains(myMid) {
                    self.isBanned = true
                } else {
                    self.pdfs = archiveData.pdfs
                    self.selectedPDF = archiveData.pdfs.first
                }
            }
        } catch {
            print("Lỗi đọc file bundle: \\(error)")
        }
    }
}
""",

"Views/ProtectedPDFView.swift": """import SwiftUI
import PDFKit

// Ép vô hiệu hóa hoàn toàn Text Selection / Right Click menu
class SecurePDFView: PDFView {
    override func copy(_ sender: Any?) { } // Huỷ lệnh copy phím tắt
    override func menu(for event: NSEvent) -> NSMenu? { return nil } // Huỷ Right Click Options Menu
    override var acceptsFirstResponder: Bool { return false } // Không cho trỏ chuột Text
}

struct ProtectedPDFViewer: NSViewRepresentable {
    let pdfData: Data
    
    func makeNSView(context: Context) -> SecurePDFView {
        let pdfView = SecurePDFView()
        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        if let doc = PDFDocument(data: pdfData) {
            pdfView.document = doc
        }
        return pdfView
    }
    
    func updateNSView(_ nsView: SecurePDFView, context: Context) {
        if let doc = PDFDocument(data: pdfData) {
            nsView.document = doc
        }
    }
}
"""
}

for file_path, content in contents.items():
    full_path = os.path.join(base_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Cấu trúc Swift tại {base_dir} đã được tạo!")
