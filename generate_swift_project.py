import os

base_dir = r"d:\code\python\too_hash_PDF_macOS"

contents = {
"PDFLock/App/PDFLockApp.swift": """import SwiftUI

@main
struct PDFLockApp: App {
    @StateObject private var licenseManager = LicenseManager()

    var body: some Scene {
        WindowGroup {
            if licenseManager.isActivated {
                MainView()
                    .environmentObject(licenseManager)
                    // Core Anti-Capture: Chống quay phim/chụp ảnh màn hình (AppKit)
                    .onAppear {
                        if let window = NSApplication.shared.windows.first {
                            window.sharingType = .none
                        }
                    }
            } else {
                ActivationView()
                    .environmentObject(licenseManager)
            }
        }
        .windowStyle(HiddenTitleBarWindowStyle())
    }
}
""",

"PDFLock/Crypto/AESManager.swift": """import Foundation
import CryptoKit

class AESManager {
    // Shared Master Key (Chuẩn 32 ký tự = 256 bits). Phải khớp với author_app.py!
    static let shared = AESManager()
    let keyString = "12345678901234567890123456789012"
    
    func decrypt(data: Data) throws -> Data {
        let key = SymmetricKey(data: keyString.data(using: .utf8)!)
        let sealedBox = try AES.GCM.SealedBox(combined: data)
        let decryptedData = try AES.GCM.open(sealedBox, using: key)
        return decryptedData
    }
}
""",

"PDFLock/License/License.swift": """import Foundation

struct License: Codable {
    let machine_id: String
    let expiry: String
    let can_print: Bool
    
    var isValid: Bool {
        if machine_id != MachineID.get() { return false }
        if expiry != "PERMANENT" {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            if let expDate = formatter.date(from: expiry) {
                if Date() > expDate { return false }
            } else {
                return false
            }
        }
        return true
    }
}
""",

"PDFLock/License/MachineID.swift": """import Foundation
import CryptoKit

struct MachineID {
    static func get() -> String {
        let task = Process()
        task.launchPath = "/usr/sbin/ioreg"
        task.arguments = ["-rd1", "-c", "IOPlatformExpertDevice"]
        
        let pipe = Pipe()
        task.standardOutput = pipe
        task.launch()
        task.waitUntilExit()
        
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: data, encoding: .utf8) {
            let lines = output.components(separatedBy: .newlines)
            for line in lines {
                if line.contains("IOPlatformUUID") {
                    let parts = line.components(separatedBy: "\\\"")
                    if parts.count >= 4 {
                        let uuid = parts[3]
                        let hash = SHA256.hash(data: Data(uuid.utf8))
                        let hashString = hash.compactMap { String(format: "%02x", $0.byte) }.joined()
                        return "MAC-" + String(hashString.prefix(10)).uppercased()
                    }
                }
            }
        }
        return "UNKNOWN-MAC-ID"
    }
}

extension UInt8 {
    var byte: UInt8 { return self }
}
""",

"PDFLock/License/LicenseManager.swift": """import Foundation
import SwiftUI

class LicenseManager: ObservableObject {
    @Published var isActivated: Bool = false
    @Published var currentLicense: License?
    
    init() {
        checkSavedLicense()
    }
    
    func checkSavedLicense() {
        if let keyStr = KeychainManager.load(key: "PDFLockLicense"),
           let license = parseKey(keyStr) {
            if license.isValid {
                self.currentLicense = license
                self.isActivated = true
            }
        }
    }
    
    func activate(with keyStr: String) -> Bool {
        if let license = parseKey(keyStr), license.isValid {
            KeychainManager.save(key: "PDFLockLicense", data: keyStr)
            self.currentLicense = license
            self.isActivated = true
            return true
        }
        return false
    }
    
    private func parseKey(_ keyStr: String) -> License? {
        guard let data = Data(base64Encoded: keyStr) else { return nil }
        do {
            let decrypted = try AESManager.shared.decrypt(data: data)
            let license = try JSONDecoder().decode(License.self, from: decrypted)
            return license
        } catch {
            return nil
        }
    }
}
""",

"PDFLock/Storage/KeychainManager.swift": """import Foundation
import Security

class KeychainManager {
    class func save(key: String, data: String) {
        let dataFromString = data.data(using: .utf8)!
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: dataFromString
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    class func load(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: kCFBooleanTrue!,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)
        
        if status == noErr, let data = dataTypeRef as? Data {
            return String(data: data, encoding: .utf8)
        }
        return nil
    }
}
""",

"PDFLock/Package/PackageReader.swift": """import Foundation

class PackageReader {
    static func readKhoaFile(url: URL) -> Data? {
        do {
            let encryptedData = try Data(contentsOf: url)
            let decryptedData = try AESManager.shared.decrypt(data: encryptedData)
            return decryptedData
        } catch {
            return nil
        }
    }
}
""",

"PDFLock/Presentation/PDFImageViewer.swift": """import SwiftUI
import PDFKit

struct PDFImageViewer: View {
    let pdfData: Data
    @State private var images: [NSImage] = []
    
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(0..<images.count, id: \\.self) { index in
                    Image(nsImage: images[index])
                        .resizable()
                        .scaledToFit()
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .shadow(radius: 4)
                        .padding(.horizontal)
                        // Anti-copying is naturally enforced because it's rendered to NSImage!
                }
            }
            .padding(.vertical)
        }
        .onAppear {
            renderPDF()
        }
    }
    
    func renderPDF() {
        // Vẽ toàn bộ PDF thành NSImage nằm chết trên RAM. Không thể copy text!
        guard let document = PDFDocument(data: pdfData) else { return }
        var tempImages: [NSImage] = []
        
        for i in 0..<document.pageCount {
            if let page = document.page(at: i) {
                let pageRect = page.bounds(for: .mediaBox)
                let scale: CGFloat = 2.0 // Render 2x phân giải để nét
                let scaledRect = CGRect(x: 0, y: 0, width: pageRect.width * scale, height: pageRect.height * scale)
                
                let nsImage = NSImage(size: scaledRect.size)
                nsImage.lockFocus()
                if let context = NSGraphicsContext.current?.cgContext {
                    context.setFillColor(NSColor.white.cgColor)
                    context.fill(scaledRect)
                    
                    context.saveGState()
                    context.translateBy(x: 0.0, y: scaledRect.size.height)
                    context.scaleBy(x: scale, y: -scale)
                    page.draw(with: .mediaBox, to: context)
                    context.restoreGState()
                }
                nsImage.unlockFocus()
                tempImages.append(nsImage)
            }
        }
        self.images = tempImages
    }
}
""",

"PDFLock/Views/ActivationView.swift": """import SwiftUI

struct ActivationView: View {
    @EnvironmentObject var licenseManager: LicenseManager
    @State private var licenseKey: String = ""
    @State private var showError = false
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "lock.shield")
                .resizable()
                .frame(width: 80, height: 80)
                .foregroundColor(.blue)
            
            Text("PDFLock DRM Kích Hoạt (Bản Swift macOS)")
                .font(.largeTitle)
                .bold()
            
            Text("Machine ID Apple của bạn:")
            Text(MachineID.get())
                .font(.title2)
                .bold()
                .foregroundColor(.red)
                .textSelection(.enabled) // Cho phép copy cái ID này để dán
            
            SecureField("Nhập License Key", text: $licenseKey)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .frame(width: 400)
                .padding(.top, 10)
            
            Button("KÍCH HOẠT") {
                if !licenseManager.activate(with: licenseKey.trimmingCharacters(in: .whitespacesAndNewlines)) {
                    showError = true
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .alert("Lỗi", isPresented: $showError) {
                Button("OK", role: .cancel) { }
            } message: {
                Text("License Key không hợp lệ, không đúng thiết bị hoặc đã hết hạn!")
            }
        }
        .frame(width: 600, height: 400)
    }
}
""",

"PDFLock/Views/MainView.swift": """import SwiftUI
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
        let tempUrl = URL(fileURLWithPath: "/tmp/print_temp_\\(UUID().uuidString).pdf")
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
            print("Print error: \\(error)")
        }
    }
}
""",

"PDFLockAdmin/AdminApp.swift": """import SwiftUI

@main
struct AdminApp: App {
    var body: some Scene {
        WindowGroup {
            LicenseGeneratorView()
        }
    }
}

struct LicenseGeneratorView: View {
    var body: some View {
        Text("Admin Tool Swift (Nếu muốn xài UI Swift)")
            .padding()
        // Implement giống hệt author_app.py
    }
}
""",

"author_app.py": """import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Khóa Master (32 bytes = 256 bits) cho thuật toán AES-GCM (KHỚP HOÀN TOÀN VỚI MÃ NGUỒN CryptoKit SWIFT BÊN KIA)
MASTER_KEY = b'12345678901234567890123456789012' 

class AdminAppSwiftBridge(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDFLock Admin Python (Đóng gói cho macOS Swift)")
        self.geometry("750x650")
        
        # UI
        self.btn_build = ctk.CTkButton(self, text="CHỌN & MÃ HÓA PDF (.khoa)", command=self.encrypt_files)
        self.btn_build.pack(pady=20)
        
        self.lbl = ctk.CTkLabel(self, text="Machine ID của Mac (VD: MAC-XXXX):")
        self.lbl.pack()
        self.entry_mid = ctk.CTkEntry(self, width=250)
        self.entry_mid.pack(pady=5)
        
        self.chk_print_var = tk.BooleanVar(value=False)
        self.chk_print = ctk.CTkCheckBox(self, text="Cho phép IN", variable=self.chk_print_var)
        self.chk_print.pack(pady=10)
        
        self.btn_key = ctk.CTkButton(self, text="TẠO LICENSE KEY", command=self.gen_key, fg_color="green")
        self.btn_key.pack(pady=20)
        
        self.txt_out = ctk.CTkTextbox(self, height=120, width=500)
        self.txt_out.pack(pady=20)
        
    def encrypt_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if not files: return
        aesgcm = AESGCM(MASTER_KEY)
        for f in files:
            with open(f, "rb") as fd: data = fd.read()
            # CryptoKit AES.GCM.SealedBox(combined:) nhận 12 bytes nonce ở đầu + ciphertext + 16 bytes tag ở cuối
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            combined = nonce + ciphertext 
            
            out_file = f.replace(".pdf", ".khoa")
            with open(out_file, "wb") as fd: fd.write(combined)
        messagebox.showinfo("OK", f"Đã mã hóa {len(files)} file PDF sang đuôi .khoa")
            
    def gen_key(self):
        mid = self.entry_mid.get().strip()
        if not mid:
            messagebox.showerror("Lỗi", "Vui lòng nhập Machine ID!")
            return
            
        aesgcm = AESGCM(MASTER_KEY)
        license_data = {
            "machine_id": mid, 
            "expiry": "PERMANENT", 
            "can_print": self.chk_print_var.get()
        }
        data_json = json.dumps(license_data).encode('utf-8')
        
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data_json, None)
        combined = nonce + ciphertext
        
        # Encode Base64 xuất dạng text cho khách
        b64 = base64.b64encode(combined).decode('utf-8')
        self.txt_out.delete("0.0", "end")
        self.txt_out.insert("0.0", b64)

if __name__ == "__main__":
    app = AdminAppSwiftBridge()
    app.mainloop()
"""
}

for file_path, content in contents.items():
    full_path = os.path.join(base_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Cấu trúc thư mục Swift Native và {len(contents)} files đã được khởi tạo thành công!")
