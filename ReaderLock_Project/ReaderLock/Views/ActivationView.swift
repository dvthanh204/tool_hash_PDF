import SwiftUI

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
            
            Text("Thiết bị của bạn là: \(MachineID.get())")
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
