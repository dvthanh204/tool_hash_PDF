import os

base_dir = r"d:\code\python\too_hash_PDF_macOS\ReaderLock_Project\ReaderLock"

swift_files = {
"Core/CryptoManager.swift": """import Foundation
import CryptoKit

struct CryptoManager {
    static let secretSalt = "MY_SUPER_SECRET_2026"
    
    static func getAESKey() -> SymmetricKey {
        let digest = SHA256.hash(data: Data(secretSalt.utf8))
        return SymmetricKey(data: Data(digest))
    }
    
    static func verifyLicense(key: String, machineID: String) -> (isValid: Bool, message: String, version: Int) {
        let parts = key.split(separator: "-").map { String($0) }
        
        // V1-PERM-HASH
        guard parts.count == 3, parts[0].hasPrefix("V") else {
            return (false, "Mật khẩu không đúng định dạng!", 0)
        }
        
        let versionStr = parts[0].dropFirst()
        guard let version = Int(versionStr) else {
            return (false, "Phiên bản không hợp lệ!", 0)
        }
        
        let expiryStr = parts[1]
        let codeHash = parts[2]
        
        let raw = "\\(machineID)_\\(version)_\\(expiryStr)_\\(secretSalt)"
        let expectedHash = SHA256.hash(data: Data(raw.utf8))
            .map { String(format: "%02x", $0) }.joined().prefix(8).uppercased()
            
        if codeHash != expectedHash {
            return (false, "Mật khẩu không hợp lệ cho PC này!", 0)
        }
        
        if expiryStr != "PERM" {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyMMdd"
            formatter.timeZone = TimeZone.current
            
            if let expDate = formatter.date(from: expiryStr) {
                let calendar = Calendar.current
                if let endOfDay = calendar.date(bySettingHour: 23, minute: 59, second: 59, of: expDate) {
                    if Date() > endOfDay {
                        return (false, "Mật khẩu này ĐÃ HẾT HẠN SỬ DỤNG!", 0)
                    }
                }
            } else {
                return (false, "Lỗi đọc thời hạn.", 0)
            }
        }
        
        // Kiểm tra version local cache nếu có
        let savedVersion = UserDefaults.standard.integer(forKey: "LicenseVersion")
        if version < savedVersion {
            return (false, "Mật khẩu (V\\(version)) ĐÃ BỊ THU HỒI. Hãy dùng mã tối thiểu V\\(savedVersion).", 0)
        }
        
        return (true, "Hợp lệ", version)
    }
    
    static func decryptPayload(data: Data) -> Data? {
        do {
            let key = getAESKey()
            let sealedBox = try AES.GCM.SealedBox(combined: data)
            let decryptedData = try AES.GCM.open(sealedBox, using: key)
            return decryptedData
        } catch {
            print("Lỗi giải mã: \\(error)")
            return nil
        }
    }
}
""",

"Core/MachineID.swift": """import Foundation
import IOKit
import CryptoKit

struct MachineID {
    static func get() -> String {
        var serialNumber: String = "DEFAULT_PC"
        let platformExpert = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOPlatformExpertDevice"))
        
        if platformExpert != 0 {
            if let serial = IORegistryEntryCreateCFProperty(platformExpert, kIOPlatformSerialNumberKey as CFString, kCFAllocatorDefault, 0)?.takeUnretainedValue() as? String {
                serialNumber = serial
            }
            IOObjectRelease(platformExpert)
        }
        
        let digest = Insecure.MD5.hash(data: Data(serialNumber.utf8))
        let hexString = digest.map { String(format: "%02x", $0) }.joined()
        
        return "MAC-" + String(hexString.prefix(12)).uppercased()
    }
}
""",

"Core/ArchiveManager.swift": """import Foundation

struct ArchivedPDF: Hashable {
    let name: String
    let data: Data
}

struct ArchiveManager {
    static func extractInMemory(zipData: Data) -> (pdfs: [ArchivedPDF], revocations: [String: Int]) {
        var pdfs: [ArchivedPDF] = []
        var revocations: [String: Int] = [:]
        
        guard let archive = try? Archive(data: zipData, accessMode: .read) else {
            return (pdfs, revocations)
        }
        
        for entry in archive {
            var entryData = Data()
            do {
                _ = try archive.extract(entry) { data in
                    entryData.append(data)
                }
                
                if entry.path == "revocations.json" {
                    if let revDict = try? JSONDecoder().decode([String: Int].self, from: entryData) {
                        revocations = revDict
                    }
                } else if entry.path.hasSuffix(".pdf") {
                    pdfs.append(ArchivedPDF(name: entry.path, data: entryData))
                }
            } catch {
                print("Lỗi giải nén: \\(error)")
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
    @State private var message: String = ""
    @State private var showError = false
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "lock.laptopcomputer")
                .resizable()
                .scaledToFit()
                .frame(width: 80, height: 80)
                .foregroundColor(.blue)
            
            Text("TRÌNH MỞ BÀI GIẢNG PDF")
                .font(.title)
                .bold()
            
            Text("Thiết bị của bạn là: \\(MachineID.get())")
                .font(.headline)
                .foregroundColor(.red)
                .textSelection(.enabled)
            
            Text("Hãy nhập Mã kích hoạt vào đây:")
            TextField("Nhập Key V1-PERM-XXX...", text: $licenseKey)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .frame(width: 400)
            
            Button("🔒 MỞ BÀI GIẢNG") {
                let trimmedKey = licenseKey.trimmingCharacters(in: .whitespacesAndNewlines)
                let check = CryptoManager.verifyLicense(key: trimmedKey, machineID: MachineID.get())
                
                if check.isValid {
                    UserDefaults.standard.set(trimmedKey, forKey: "LicenseKey")
                    UserDefaults.standard.set(check.version, forKey: "LicenseVersion")
                    isActivated = true
                } else {
                    message = check.message
                    showError = true
                }
            }
            .buttonStyle(.borderedProminent)
            .alert("Lỗi Bản Quyền", isPresented: $showError) {
                Button("OK", role: .cancel) { }
            } message: {
                Text(message)
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
    @State private var banMessage = ""
    
    var body: some View {
        HStack(spacing: 0) {
            List(pdfs, id: \\.name, selection: $selectedPDF) { pdf in
                Text(pdf.name).tag(pdf)
            }
            .listStyle(SidebarListStyle())
            .frame(width: 250)
            
            if isBanned {
                VStack {
                    Image(systemName: "hand.raised.slash.fill")
                        .resizable().frame(width: 100, height: 100).foregroundColor(.red)
                    Text("BẢN QUYỀN ĐÃ BỊ THU HỒI")
                        .font(.title).padding()
                    Text(banMessage)
                        .foregroundColor(.gray)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                if let pdf = selectedPDF {
                    ProtectedPDFViewer(pdfData: pdf.data)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text("Vui lòng chọn bài giảng bên trái").frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .onAppear { loadBundleData() }
    }
    
    func loadBundleData() {
        guard let url = Bundle.main.url(forResource: "tailieu", withExtension: "khoa") else {
            return
        }
        do {
            let encryptedData = try Data(contentsOf: url)
            if let decryptedZip = CryptoManager.decryptPayload(data: encryptedData) {
                let archiveData = ArchiveManager.extractInMemory(zipData: decryptedZip)
                let myMid = MachineID.get()
                
                let savedVersion = UserDefaults.standard.integer(forKey: "LicenseVersion")
                if let bannedVersion = archiveData.revocations[myMid] {
                    if savedVersion <= bannedVersion {
                        UserDefaults.standard.removeObject(forKey: "LicenseKey")
                        self.banMessage = "Mật khẩu cho thiết bị này đã bị xóa và thu hồi."
                        self.isBanned = true
                        return
                    }
                }
                
                self.pdfs = archiveData.pdfs.sorted(by: { $0.name < $1.name })
                self.selectedPDF = self.pdfs.first
            }
        } catch { }
    }
}
"""
}

for file_path, content in swift_files.items():
    full_path = os.path.join(base_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Cấu trúc Swift mới tại {base_dir} đã được cập nhật thành công!")
