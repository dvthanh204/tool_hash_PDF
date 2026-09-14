import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import hashlib
import base64
import os
import json
import zipfile
import shutil
import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SECRET_SALT = "MY_SUPER_SECRET_2026"
AES_KEY = hashlib.sha256(SECRET_SALT.encode()).digest()

def generate_key_for_client(machine_id, version=1, days=0):
    if days <= 0:
        expiry_str = "PERM"
    else:
        exp_date = datetime.datetime.now() + datetime.timedelta(days=days)
        expiry_str = exp_date.strftime("%y%m%d")
        
    raw = f"{machine_id}_{version}_{expiry_str}_{SECRET_SALT}"
    code_hash = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
    return f"V{version}-{expiry_str}-{code_hash}"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AuthorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ReaderLock Admin (macOS Target)")
        self.geometry("900x600")
        self.configure(fg_color="#0F172A")
        self.load_revocations()

        # Grid layout for Sidebar and Content
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, fg_color="#1E293B", width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        ctk.CTkLabel(self.sidebar_frame, text="🛡 SLIDELOCK", font=ctk.CTkFont(family="Inter", size=22, weight="bold"), text_color="#38BDF8").pack(pady=(30, 5))
        ctk.CTkLabel(self.sidebar_frame, text="macOS PDF DRM Panel", font=ctk.CTkFont(family="Inter", size=12), text_color="#94A3B8").pack(pady=(0, 30))
        
        self.nav_btns = []
        def nav_btn(text, cmd):
            btn = ctk.CTkButton(self.sidebar_frame, text=text, font=ctk.CTkFont(family="Inter", size=14, weight="bold"), fg_color="transparent", text_color="#CBD5E1", hover_color="#334155", anchor="w", height=45, corner_radius=8, command=cmd)
            btn.pack(pady=5, padx=20, fill="x")
            self.nav_btns.append(btn)
            return btn
            
        nav_btn("📦 1. Đóng Gói (Mã Hóa)", lambda: self.select_menu("tab1"))
        nav_btn("🔑 2. Cấp Key Mới", lambda: self.select_menu("tab2"))
        nav_btn("🔒 3. Danh Sách Đen", lambda: self.select_menu("tab3"))
        nav_btn("🔓 4. Gỡ Lệnh Cấm", lambda: self.select_menu("tab4"))
        
        # --- MAIN CONTENT ---
        self.main_frame = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        self.frames = {}
        for tab in ["tab1", "tab2", "tab3", "tab4"]:
            self.frames[tab] = ctk.CTkFrame(self.main_frame, fg_color="transparent")

        self.init_tab1()
        self.init_tab2()
        self.init_tab3()
        self.init_tab4()
        
        self.select_menu("tab1")

    def select_menu(self, menu_id):
        for btn in self.nav_btns:
            btn.configure(fg_color="transparent", text_color="#CBD5E1")
            
        idx = ["tab1", "tab2", "tab3", "tab4"].index(menu_id)
        self.nav_btns[idx].configure(fg_color="#38BDF8", text_color="#0F172A")
        
        for f in self.frames.values():
            f.pack_forget()
        self.frames[menu_id].pack(fill="both", expand=True)

    def load_revocations(self):
        self.revocations = {}
        if os.path.exists("revocations.json"):
            try:
                with open("revocations.json", "r") as f:
                    self.revocations = json.load(f)
            except: pass
                
    def save_revocations(self):
        with open("revocations.json", "w") as f:
            json.dump(self.revocations, f)

    def build_card(self, parent, title, desc):
        card = ctk.CTkFrame(parent, fg_color="#1E293B", corner_radius=16, border_width=1, border_color="#334155")
        card.pack(fill="both", expand=True, pady=10)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family="Inter", size=20, weight="bold"), text_color="#F8FAFC").pack(pady=(30, 5), anchor="w", padx=40)
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(family="Inter", size=13), text_color="#94A3B8").pack(pady=(0, 20), anchor="w", padx=40)
        return card

    # === TAB 1: MÃ HÓA ===
    def init_tab1(self):
        card = self.build_card(self.frames["tab1"], "Đóng Gói Bài Giảng (macOS Target)", "Mã hóa và nhúng DRM vào các file PDF (chạy cho Xcode App).")
        self.filepath_var = tk.StringVar()
        entry_file = ctk.CTkEntry(card, textvariable=self.filepath_var, height=45, placeholder_text="Chọn đường dẫn file .pdf...", font=ctk.CTkFont(family="Inter", size=13), fg_color="#0F172A", border_color="#475569")
        entry_file.pack(padx=40, fill="x", pady=10)
        
        btn_browse = ctk.CTkButton(card, text="📂 Duyệt PDF", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), command=self.browse_file, fg_color="#334155", hover_color="#475569", height=40)
        btn_browse.pack(padx=40, anchor="e")

        btn_build = ctk.CTkButton(card, text="🛡 KHỞI TẠO macOS APP", fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(family="Inter", size=15, weight="bold"), text_color="white", command=self.build_mac_app, height=50)
        btn_build.pack(pady=40, padx=40, fill="x")
        
        self.status_lbl = ctk.CTkLabel(card, text="", text_color="#3B82F6", font=ctk.CTkFont(family="Inter", size=13))
        self.status_lbl.pack()

    def browse_file(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if files: self.filepath_var.set(";".join(files))

    def build_mac_app(self):
        input_files = self.filepath_var.get().split(';')
        if not input_files or not input_files[0] or not os.path.exists(input_files[0]):
            messagebox.showerror("Lỗi", "Hãy chọn ít nhất 1 file PDF!")
            return

        self.status_lbl.configure(text="Đang xử lý gói tin an mật Crypto...", text_color="#10B981")
        self.update()
        
        try:
            # 1. Zip toàn bộ PDF và revocations.json vào RAM
            import io
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("revocations.json", json.dumps(self.revocations))
                for idx, pdf in enumerate(input_files):
                    if os.path.exists(pdf):
                        with open(pdf, "rb") as f:
                            zf.writestr(f"tailieu_{idx+1}_{os.path.basename(pdf)}", f.read())
            zip_data = mem_zip.getvalue()
            
            # 2. Mã hóa bằng AES-GCM (Để macOS CryptoKit có thể đọc được)
            aesgcm = AESGCM(AES_KEY)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, zip_data, None)
            final_crypto_payload = nonce + ciphertext
            
            with open("tailieu.khoa", "wb") as f: 
                f.write(final_crypto_payload)
            
            # 3. Gắn vào App macOS
            app_dir = "ReaderLock.app"
            if not os.path.exists(app_dir):
                messagebox.showerror("Lỗi Cấu Trúc", "Không tìm thấy thư mục 'ReaderLock.app' được tải về từ bản build Github Actions.")
                return
                
            res_dir = os.path.join(app_dir, "Contents", "Resources")
            os.makedirs(res_dir, exist_ok=True)
            shutil.copy("tailieu.khoa", os.path.join(res_dir, "tailieu.khoa"))
            os.remove("tailieu.khoa")
            
            # 4. Tạo file ZIP trên thư mục dist để xuất hàng
            os.makedirs("dist", exist_ok=True)
            base_zip_name = 'macOS_KhoaHoc_MultiFiles.zip' if len(input_files) > 1 else f"macOS_KhoaHoc_{os.path.splitext(os.path.basename(input_files[0]))[0]}.zip"
            out_zip = os.path.join("dist", base_zip_name)
            
            counter = 2
            while os.path.exists(out_zip):
                suffix = "MultiFiles" if len(input_files) > 1 else os.path.splitext(os.path.basename(input_files[0]))[0]
                out_zip = os.path.join("dist", f"macOS_KhoaHoc_{suffix}{counter}.zip")
                counter += 1

            with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(app_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, ".")
                        zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                        if "Contents/MacOS/" in arcname.replace("\\", "/"):
                            zinfo.external_attr = 0x81ED0000 | 0o755 << 16
                        else:
                            zinfo.external_attr = 0x81B40000 | 0o644 << 16
                        with open(file_path, "rb") as f:
                            zf.writestr(zinfo, f.read())
                            
            self.status_lbl.configure(text="Mã hóa THÀNH CÔNG!")
            messagebox.showinfo("Thành Công", f"Đã đóng gói xong xuôi qua:\n{out_zip}\n\n(Mang file .zip này gửi cho khách macOS)")

        except Exception as e:
            messagebox.showerror("Lỗi Build", f"Có lỗi xảy ra: {e}")
            self.status_lbl.configure(text="Build thất bại!", text_color="#EF4444")

    # === TAB 2: CẤP KEY ===
    def init_tab2(self):
        card = self.build_card(self.frames["tab2"], "Cấp Mật Khẩu macOS Mới", "Tạo mã truy cập an toàn cấp cho Học viên macOS.")
        self.issue_mid_var = tk.StringVar()
        ctk.CTkEntry(card, textvariable=self.issue_mid_var, height=45, placeholder_text="Nhập Machine ID (của khách macOS) vào đây...", font=ctk.CTkFont(family="Inter", size=14), fg_color="#0F172A", border_color="#475569").pack(pady=10, padx=40, fill="x")
        self.issue_expiry_var = tk.StringVar(value="Vĩnh viễn")
        ctk.CTkOptionMenu(card, variable=self.issue_expiry_var, values=["Vĩnh viễn", "7 Ngày", "30 Ngày", "365 Ngày"], font=ctk.CTkFont(family="Inter", size=13), height=40, fg_color="#334155", button_color="#475569").pack(pady=5, padx=40, anchor="w")
        
        ctk.CTkButton(card, text="🔑 TẠO MẬT KHẨU", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), fg_color="#2563EB", hover_color="#1D4ED8", command=self.do_issue, height=45).pack(pady=25, padx=40, fill="x")
        
        self.issue_pwd_var = tk.StringVar()
        ctk.CTkEntry(card, textvariable=self.issue_pwd_var, height=50, font=ctk.CTkFont(family="Consolas", size=16), justify='center', state='readonly', fg_color="#0F172A", text_color="#10B981", border_color="#10B981").pack(pady=10, padx=40, fill="x")

    def do_issue(self):
        mid = self.issue_mid_var.get().strip()
        if not mid: return
        days = {"7 Ngày": 7, "30 Ngày": 30, "365 Ngày": 365, "Vĩnh viễn": 0}.get(self.issue_expiry_var.get(), 0)
        v = self.revocations.get(mid, 0) + 1
        self.issue_pwd_var.set(generate_key_for_client(mid, version=v, days=days))

    # === TAB 3: DANH SÁCH ĐEN ===
    def init_tab3(self):
        card = self.build_card(self.frames["tab3"], "Thu Hồi Từ Xa (Danh Sách Đen)", "Đưa một ID vào sổ đen để khóa cứng thiết bị ở các bản PDF sau.")
        self.revoke_mid_var = tk.StringVar()
        ctk.CTkEntry(card, textvariable=self.revoke_mid_var, height=45, placeholder_text="Nhập Machine ID cần CẤM...", font=ctk.CTkFont(family="Inter", size=14), fg_color="#0F172A", text_color="#EF4444", border_color="#475569").pack(pady=10, padx=40, fill="x")
        
        def run_revoke():
            m = self.revoke_mid_var.get().strip()
            if not m: return
            self.revocations[m] = self.revocations.get(m, 0) + 1
            self.save_revocations()
            messagebox.showinfo("HOÀN TẤT", "Đã chặn. Khách này sẽ không thể dùng mật khẩu cũ để mở bản xuất App tiếp theo!")
            
        ctk.CTkButton(card, text="🔒 CHẶN MÁY NÀY", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), fg_color="#EF4444", hover_color="#DC2626", text_color="white", command=run_revoke, height=45).pack(pady=25, padx=40, fill="x")

    # === TAB 4: CẤP LẠI MÃ ===
    def init_tab4(self):
        card = self.build_card(self.frames["tab4"], "Gỡ Cấm & Cấp Lại Phục Hồi", "Cấp một mật khẩu version mới hoàn toàn để thả cửa cho máy.")
        self.reissue_mid_var = tk.StringVar()
        ctk.CTkEntry(card, textvariable=self.reissue_mid_var, height=45, placeholder_text="Nhập Machine ID cần Gỡ Băng...", font=ctk.CTkFont(family="Inter", size=14), fg_color="#0F172A", border_color="#475569").pack(pady=10, padx=40, fill="x")
        self.reissue_pwd_var = tk.StringVar()
        
        def run_unrevoke():
            m = self.reissue_mid_var.get().strip()
            if not m: return
            new_v = self.revocations.get(m, 0) + 1
            self.reissue_pwd_var.set(generate_key_for_client(m, version=new_v, days=0))
            
        ctk.CTkButton(card, text="🔓 GỠ KHÓA & SINH MÃ MỚI", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), fg_color="#F59E0B", hover_color="#D97706", text_color="white", command=run_unrevoke, height=45).pack(pady=25, padx=40, fill="x")
        ctk.CTkEntry(card, textvariable=self.reissue_pwd_var, height=50, font=ctk.CTkFont(family="Consolas", size=16), justify='center', state='readonly', fg_color="#0F172A", text_color="#F59E0B", border_color="#F59E0B").pack(pady=10, padx=40, fill="x")

if __name__ == "__main__":
    app = AuthorApp()
    app.mainloop()
