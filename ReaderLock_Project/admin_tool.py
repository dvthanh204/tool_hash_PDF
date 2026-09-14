import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import io
import zipfile
import shutil
import base64
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Static Key (32 bytes)
SECRET_KEY = b'12345678901234567890123456789012'

class AdminTool(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ReaderLock DRM Admin (macOS Target)")
        self.geometry("900x600")
        ctk.set_appearance_mode("dark")
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="Admin DRM", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=20, padx=20)
        
        self.btn_pack = ctk.CTkButton(self.sidebar, text="Mã Hóa & Khởi Tạo App", command=lambda: self.show_frame("pack"))
        self.btn_pack.pack(pady=10, padx=20)
        self.btn_key = ctk.CTkButton(self.sidebar, text="Cấp Key Cứng", command=lambda: self.show_frame("key"))
        self.btn_key.pack(pady=10, padx=20)
        self.btn_revoke = ctk.CTkButton(self.sidebar, text="Khóa Máy (Revoke)", command=lambda: self.show_frame("revoke"), fg_color="#9e2a2b")
        self.btn_revoke.pack(pady=10, padx=20)
        self.btn_unrevoke = ctk.CTkButton(self.sidebar, text="Ân Xá Máy", command=lambda: self.show_frame("unrevoke"), fg_color="#5390d9")
        self.btn_unrevoke.pack(pady=10, padx=20)
        
        # Main containers
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        self.frames = {}
        self.setup_pack_frame()
        self.setup_key_frame()
        self.setup_revoke_frame()
        self.setup_unrevoke_frame()
        
        self.show_frame("pack")
        
        # Data path
        self.revocations_path = "revocations.json"
        if not os.path.exists(self.revocations_path):
            with open(self.revocations_path, "w") as f:
                json.dump([], f)

    def show_frame(self, name):
        for f in self.frames.values(): f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        
    def setup_pack_frame(self):
        frm = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["pack"] = frm
        
        self.pdf_list = []
        
        ctk.CTkLabel(frm, text="Đóng gói App - Mã Hóa File (.khoa)", font=("Arial", 18, "bold")).pack(pady=10)
        
        self.lbl_files = ctk.CTkLabel(frm, text="Chưa chọn file PDF nào.")
        self.lbl_files.pack(pady=10)
        
        ctk.CTkButton(frm, text="Duyệt File PDF", command=self.browse_pdfs).pack(pady=10)
        
        btn_start = ctk.CTkButton(frm, text="KHỞI TẠO APP ZIP", command=self.build_app, fg_color="#2b9348", height=50)
        btn_start.pack(pady=30)
        
    def browse_pdfs(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if files:
            self.pdf_list = list(files)
            self.lbl_files.configure(text=f"Đã chọn {len(self.pdf_list)} file PDF.")
            
    def build_app(self):
        if not self.pdf_list:
            messagebox.showerror("Lỗi", "Hãy chọn ít nhất 1 file PDF!")
            return
            
        try:
            # 1. Nén pdf và revocations.json vào BytesIO
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists(self.revocations_path):
                    with open(self.revocations_path, "r") as f: data = f.read()
                    zf.writestr("revocations.json", data)
                else:
                    zf.writestr("revocations.json", "[]")
                    
                for idx, pdf in enumerate(self.pdf_list):
                    with open(pdf, "rb") as f:
                        zf.writestr(f"tailieu_{idx+1}_{os.path.basename(pdf)}", f.read())
            
            zip_data = mem_zip.getvalue()
            
            # 2. Mã hóa AES-GCM 256
            aesgcm = AESGCM(SECRET_KEY)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, zip_data, None)
            final_crypto_payload = nonce + ciphertext
            
            # 3. Tạo file tailieu.khoa
            with open("tailieu.khoa", "wb") as f: f.write(final_crypto_payload)
            
            # 4. Inject vào App
            app_dir = "ReaderLock.app"
            if not os.path.exists(app_dir):
                # Tạo giả lập nếu chưa có
                os.makedirs(os.path.join(app_dir, "Contents", "Resources"), exist_ok=True)
                os.makedirs(os.path.join(app_dir, "Contents", "MacOS"), exist_ok=True)
                with open(os.path.join(app_dir, "Contents", "MacOS", "ReaderLock"), "w") as f: f.write("Dummy")
                
            res_dir = os.path.join(app_dir, "Contents", "Resources")
            os.makedirs(res_dir, exist_ok=True)
            shutil.copy("tailieu.khoa", os.path.join(res_dir, "tailieu.khoa"))
            
            # 5. Build Final ZIP App
            out_zip = "ReaderLock_Mac.zip"
            with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(app_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, ".")
                        zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                        
                        if "Contents/MacOS/" in arcname.replace("\\", "/"):
                            # 0x81ED = 0o100755
                            zinfo.external_attr = 0x81ED0000 | 0o755 << 16
                        else:
                            # 0x81B4 = 0o100644
                            zinfo.external_attr = 0x81B40000 | 0o644 << 16
                            
                        with open(file_path, "rb") as f:
                            zf.writestr(zinfo, f.read())
                            
            messagebox.showinfo("Hoàn Thành", f"Tạo app thành công: {out_zip}\n(Đã cấp quyền thực thi cho file bên trong).")
        except Exception as e:
            messagebox.showerror("Lỗi Zip", str(e))
            
    def setup_key_frame(self):
        frm = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["key"] = frm
        
        ctk.CTkLabel(frm, text="Cấp Key cho Machine ID", font=("Arial", 18, "bold")).pack(pady=10)
        self.entry_mid = ctk.CTkEntry(frm, width=300, placeholder_text="Nhập IOPlatformSerialNumber (Machine ID)")
        self.entry_mid.pack(pady=10)
        
        ctk.CTkButton(frm, text="Sinh License Key", command=self.gen_key).pack(pady=10)
        
        self.txt_key = ctk.CTkTextbox(frm, height=100, width=400)
        self.txt_key.pack(pady=20)
        
    def gen_key(self):
        mid = self.entry_mid.get().strip()
        if not mid: return
        h = hmac.new(SECRET_KEY, mid.encode('utf-8'), hashlib.sha256)
        key_str = base64.b64encode(h.digest()).decode('utf-8')
        self.txt_key.delete("0.0", "end")
        self.txt_key.insert("0.0", key_str)
        
    def setup_revoke_frame(self):
        frm = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["revoke"] = frm
        
        ctk.CTkLabel(frm, text="Khóa Máy (Ghi đè vào revocations.json)", font=("Arial", 18, "bold"), text_color="#d00000").pack(pady=10)
        self.entry_rev = ctk.CTkEntry(frm, width=300, placeholder_text="Machine ID cần khóa")
        self.entry_rev.pack(pady=10)
        
        ctk.CTkButton(frm, text="Khóa Thiết Bị", command=self.revoke_mid, fg_color="#d00000").pack(pady=10)
        
    def revoke_mid(self):
        mid = self.entry_rev.get().strip()
        if not mid: return
        with open(self.revocations_path, "r") as f:
            data = json.load(f)
        if mid not in data:
            data.append(mid)
            with open(self.revocations_path, "w") as f:
                json.dump(data, f)
            messagebox.showinfo("OK", f"Đã khóa máy: {mid}")
        else:
            messagebox.showinfo("Lỗi", "Máy này đã bị khóa từ trước!")
            
    def setup_unrevoke_frame(self):
        frm = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["unrevoke"] = frm
        
        ctk.CTkLabel(frm, text="Ân Xá (Xóa khỏi Blacklist)", font=("Arial", 18, "bold")).pack(pady=10)
        self.entry_unv = ctk.CTkEntry(frm, width=300, placeholder_text="Machine ID muốn ân xá")
        self.entry_unv.pack(pady=10)
        
        ctk.CTkButton(frm, text="Ân Xá", command=self.unrevoke_mid, fg_color="#5390d9").pack(pady=10)
        
    def unrevoke_mid(self):
        mid = self.entry_unv.get().strip()
        if not mid: return
        with open(self.revocations_path, "r") as f:
            data = json.load(f)
        if mid in data:
            data.remove(mid)
            with open(self.revocations_path, "w") as f:
                json.dump(data, f)
                
            h = hmac.new(SECRET_KEY, mid.encode('utf-8'), hashlib.sha256)
            key_str = base64.b64encode(h.digest()).decode('utf-8')
            messagebox.showinfo("Đã Ân Xá", f"Thiết bị đã được thả.\nLicense Key của họ là:\n{key_str}")
        else:
            messagebox.showinfo("Lỗi", "Không tìm thấy trong danh sách chặn!")

if __name__ == "__main__":
    app = AdminTool()
    app.mainloop()
