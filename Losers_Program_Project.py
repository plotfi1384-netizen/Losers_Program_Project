import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import sqlite3
import os
import hashlib
import binascii
import secrets
import random
import sys

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from googletrans import Translator
except Exception:
    Translator = None

try:
    import pyperclip
except Exception:
    pyperclip = None

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def hash_password(password: str, salt: bytes = None):
    """Returns (hash_hex, salt_hex). Uses PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150_000)
    return binascii.hexlify(dk).decode("ascii"), binascii.hexlify(salt).decode("ascii")


def verify_password(stored_hash_hex: str, stored_salt_hex: str, provided_password: str):
    salt = binascii.unhexlify(stored_salt_hex.encode("ascii"))
    new_hash_hex, _ = hash_password(provided_password, salt)
    return secrets.compare_digest(new_hash_hex, stored_hash_hex)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pw_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


class RoundedButton(tk.Canvas):
    def __init__(self, master, text="", radius=12, padding=10, command=None, bg="#ddd", fg="#000", font=None, **kwargs):
        super().__init__(master, highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.radius = radius
        self.padding = padding
        self.bg = bg
        self.fg = fg
        self.font = font or ("Tahoma", 11, "bold")
        self.bind("<Button-1>", lambda e: self._on_click())
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))
        self.draw()

    def draw(self):
        self.delete("all")
        t = self.create_text(0, 0, text=self.text, font=self.font, anchor="nw")
        bbox = self.bbox(t) or (0, 0, 80, 20)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        self.delete(t)
        w = tw + self.padding * 2
        h = th + self.padding * 2
        self.config(width=w, height=h)
        r = max(4, self.radius)
        points = [
            r, 0, w-r, 0, w, 0, w, r, w, r, w, h-r, w, h, w -
            r, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0, r, 0
        ]
        self.create_polygon(points, smooth=True, fill=self.bg, outline="")
        self.create_text(w/2, h/2, text=self.text,
                         font=self.font, fill=self.fg)

    def _on_click(self):
        if callable(self.command):
            self.command()


class Mascot(tk.Canvas):
    def __init__(self, master, width=120, height=120, bg=None, **kwargs):
        super().__init__(master, width=width, height=height,
                         highlightthickness=0, bg=bg if bg else master["bg"], **kwargs)
        self.w = width
        self.h = height
        self.eyes_open = True
        self.draw_face()

    def draw_face(self):
        self.delete("all")
        w, h = self.w, self.h
        self.create_oval(6, 6, w-6, h-6, fill="#222", outline="")
        self.create_arc(-20, h//2, w+20, h+40, start=0,
                        extent=180, fill="#111", outline="")
        cx_l = w*0.37
        cx_r = w*0.63
        cy = h*0.45
        ew = w*0.16
        eh = h*0.08
        if self.eyes_open:
            self.create_oval(cx_l-ew, cy-eh, cx_l+ew, cy +
                             eh, fill="white", outline="")
            self.create_oval(cx_r-ew, cy-eh, cx_r+ew, cy +
                             eh, fill="white", outline="")
            self.create_oval(cx_l - (ew*0.25), cy - (eh*0.25), cx_l +
                             (ew*0.25), cy + (eh*0.4), fill="black", outline="")
            self.create_oval(cx_r - (ew*0.25), cy - (eh*0.25), cx_r +
                             (ew*0.25), cy + (eh*0.4), fill="black", outline="")
        else:
            self.create_line(cx_l-ew, cy, cx_l+ew, cy,
                             fill="white", width=3, capstyle="round")
            self.create_line(cx_r-ew, cy, cx_r+ew, cy,
                             fill="white", width=3, capstyle="round")

    def set_open(self, v: bool):
        self.eyes_open = v
        self.draw_face()


class LotteryApp:
    def __init__(self, master):
        self.master = master
        master.title("قرعه‌کشی بازنده‌ها")
        master.geometry("820x560")
        self.names = []
        self.filename = None
        self.create_ui()

    def create_ui(self):
        f = tk.Frame(self.master, bg="#f7fbff")
        f.pack(fill="both", expand=True, padx=12, pady=12)

        left = tk.Frame(f, bg="white")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = tk.Frame(f, bg="#f0f8ff", width=300)
        right.pack(side="right", fill="y")

        lbl = tk.Label(left, text="لیست شرکت‌کننده‌ها",
                       bg="white", font=("Tahoma", 12, "bold"))
        lbl.pack(anchor="nw", pady=(8, 4), padx=8)

        self.listbox = tk.Listbox(left, font=("Tahoma", 11))
        self.listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        lbl_file = tk.Label(right, text="فایل اسامی (.txt):", bg=right["bg"])
        lbl_file.pack(anchor="n", pady=(12, 4))
        frm_file = tk.Frame(right, bg=right["bg"])
        frm_file.pack(fill="x", padx=8)
        self.lbl_filename = tk.Label(
            frm_file, text="فایلی انتخاب نشده", bg=right["bg"], anchor="w")
        self.lbl_filename.pack(side="left", fill="x", expand=True)
        tk.Button(frm_file, text="انتخاب فایل",
                  command=self.browse_file).pack(side="right", padx=4)

        lbl_num = tk.Label(right, text="تعداد برنده:", bg=right["bg"])
        lbl_num.pack(anchor="n", pady=(10, 4))
        self.entry_num = tk.Entry(right, width=8)
        self.entry_num.pack(anchor="n")

        self.lbl_error = tk.Label(right, text="", fg="red", bg=right["bg"])
        self.lbl_error.pack(anchor="n", pady=(6, 0))

        tk.Button(right, text="شروع قرعه‌کشی",
                  command=self.start_lottery).pack(anchor="n", pady=12)

        self.status = tk.Label(
            right, text="آماده", anchor="w", bg=right["bg"], font=("Tahoma", 9, "italic"))
        self.status.pack(side="bottom", fill="x", padx=6, pady=6)

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="انتخاب فایل اسامی", filetypes=[("Text files", "*.txt")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
        except Exception:
            try:
                with open(path, "r", encoding="cp1256") as f:
                    lines = [ln.strip() for ln in f if ln.strip()]
            except Exception as e:
                messagebox.showerror("خطا", f"خواندن فایل انجام نشد:\n{e}")
                return
        if not lines:
            messagebox.showwarning("هشدار", "فایل انتخاب‌شده هیچ اسمی ندارد.")
            return
        self.names = lines
        self.filename = path
        self.lbl_filename.config(text=os.path.basename(path))
        self.populate_listbox()
        self.status.config(text=f"{len(self.names)} شرکت‌کننده بارگذاری شد")
        self.lbl_error.config(text="")

    def populate_listbox(self):
        self.listbox.delete(0, tk.END)
        for n in self.names:
            self.listbox.insert(tk.END, n)

    def start_lottery(self):
        if not self.names:
            messagebox.showwarning("هشدار", "ابتدا فایل اسامی را انتخاب کنید.")
            return
        num_text = self.entry_num.get().strip()
        if not num_text.isdigit():
            self.lbl_error.config(text="عدد معتبر وارد کنید")
            return
        num = int(num_text)
        if num <= 0:
            self.lbl_error.config(text="عدد بزرگتر از صفر وارد کنید")
            return
        if num > len(self.names):
            self.lbl_error.config(text="عدد از تعداد شرکت‌کننده‌ها بیشتر است")
            return
        self.lbl_error.config(text="")
        self.status.config(text="در حال قرعه‌کشی...")
        total = 3.0
        interval = 0.06
        iterations = int(total / interval)
        self._animate(iterations, num, interval)

    def _animate(self, it, winners_count, interval):
        if it <= 0:
            winners = random.sample(self.names, winners_count)
            self.status.config(text="قرعه‌کشی تمام شد")
            self.show_winners(winners)
            return
        idx = random.randrange(len(self.names))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        color_cycle = ["#ff9aa2", "#ffd1dc", "#cde7ff", "#ffdac1"]
        self.listbox.config(
            selectbackground=color_cycle[it % len(color_cycle)])
        self.master.after(int(interval * 1000),
                          lambda: self._animate(it-1, winners_count, interval))

    def show_winners(self, winners):
        win = tk.Toplevel(self.master)
        win.title("نتیجه قرعه‌کشی")
        win.geometry("420x320")
        tk.Label(win, text="برنده‌ها:", font=(
            "Tahoma", 14, "bold")).pack(pady=8)
        txt = tk.Text(win, height=10, width=40)
        txt.pack(padx=8, pady=6)
        for i, w in enumerate(winners, start=1):
            txt.insert(tk.END, f"{i}. {w}\n")
        txt.config(state="disabled")
        tk.Button(win, text="بستن", command=win.destroy).pack(pady=6)


def is_mostly_english(text):
    import re
    if not text:
        return False
    en = len(re.findall(r'[A-Za-z]', text))
    fa = len(re.findall(r'[\u0600-\u06FF]', text))
    return en > fa


class ImageToTextApp:
    def __init__(self, master):
        self.master = master
        master.title("عکس به متن")
        master.geometry("900x700")
        self.current_image = None
        self.current_text = ""
        self.translator = Translator() if Translator else None
        self.create_ui()

    def create_ui(self):
        f = tk.Frame(self.master)
        f.pack(fill="both", expand=True, padx=8, pady=8)

        topbar = tk.Frame(f, bg="#eeeeee")
        topbar.pack(fill="x")
        tk.Button(topbar, text="بازگشت", command=self.master.destroy).pack(
            side="left", padx=6, pady=6)
        tk.Label(topbar, text="آپلود عکس و استخراج متن", font=(
            "Tahoma", 12, "bold"), bg=topbar["bg"]).pack(side="left", padx=10)

        content = tk.Frame(f)
        content.pack(fill="both", expand=True, pady=8)

        left = tk.Frame(content, width=360)
        left.pack(side="left", fill="y", padx=6)
        right = tk.Frame(content)
        right.pack(side="right", fill="both", expand=True, padx=6)

        self.preview_label = tk.Label(
            left, text="تصویر انتخاب نشده", bd=1, relief="sunken", width=40, height=20)
        self.preview_label.pack(padx=6, pady=6)

        tk.Button(left, text="انتخاب تصویر",
                  command=self.choose_image).pack(pady=6)
        self.lbl_status = tk.Label(left, text="آماده")
        self.lbl_status.pack(pady=6)

        tk.Label(right, text="متن استخراج‌شده:", font=(
            "Tahoma", 11, "bold")).pack(anchor="nw")
        self.txt_result = ScrolledText(
            right, wrap="word", font=("Tahoma", 11), height=20)
        self.txt_result.pack(fill="both", expand=True, padx=6, pady=6)

        frm = tk.Frame(right)
        frm.pack(fill="x", pady=6)
        tk.Button(frm, text="کپی متن", command=self.copy_text).pack(
            side="left", padx=6)

    def choose_image(self):
        path = filedialog.askopenfilename(title="انتخاب تصویر", filetypes=[(
            "Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"), ("All files", "*.*")])
        if not path:
            self.lbl_status.config(text="فایلی انتخاب نشد")
            return
        try:
            img = Image.open(path)
        except FileNotFoundError:
            messagebox.showerror("خطا", "فایل پیدا نشد.")
            return
        except UnidentifiedImageError:
            messagebox.showerror(
                "خطا", "فرمت تصویر پشتیبانی نمی‌شود یا فایل خراب است.")
            return
        except Exception as e:
            messagebox.showerror("خطا", f"خطا هنگام باز کردن تصویر:\n{e}")
            return

        self.current_image = img
        preview = img.copy()
        preview.thumbnail((360, 360))
        tkimg = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=tkimg, text="")
        self.preview_label.image = tkimg

        self.do_ocr(img)

    def do_ocr(self, pil_image):
        self.lbl_status.config(text="در حال استخراج متن با OCR...")
        self.txt_result.delete("1.0", tk.END)
        self.current_text = ""
        if pytesseract is None:
            messagebox.showerror(
                "خطا", "pytesseract نصب نیست یا tesseract در PATH نیست. OCR قابل اجرا نیست.")
            self.lbl_status.config(text="خطا: pytesseract نصب نیست")
            return
        try:
            img = pil_image.convert("RGB")
            raw = pytesseract.image_to_string(img, lang=None)
        except Exception as e:
            messagebox.showerror("خطا در OCR", f"خطا هنگام اجرای OCR:\n{e}")
            self.lbl_status.config(text="خطا در OCR")
            return
        if not raw.strip():
            self.lbl_status.config(text="هیچ متنی استخراج نشد.")
            messagebox.showinfo(
                "نتیجه", "متنی استخراج نشد. سعی کن عکس واضح‌تر باشه.")
            return
        self.current_text = raw.strip()
        self.txt_result.insert(tk.END, self.current_text)
        self.lbl_status.config(text="متن استخراج شد.")
        if is_mostly_english(self.current_text) and self.translator is not None:
            wants = messagebox.askyesno(
                "تشخیص زبان", "متن بیشتر به انگلیسی شبیه است. می‌خواهید ترجمه شود؟")
            if wants:
                self.translate_text(self.current_text, src='en', dest='fa')

    def translate_text(self, text, src='en', dest='fa'):
        if self.translator is None:
            messagebox.showerror("خطا", "ماژول googletrans نصب نیست.")
            return
        self.lbl_status.config(text="در حال ترجمه...")
        try:
            translator = Translator()
            res = translator.translate(text, src=src, dest=dest)
            translated = res.text
        except Exception as e:
            messagebox.showerror("خطا در ترجمه", f"ترجمه انجام نشد:\n{e}")
            self.lbl_status.config(text="خطا در ترجمه")
            return
        full = f"--- متن اصلی ---\n{text}\n\n--- ترجمه ({src}→{dest}) ---\n{translated}"
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert(tk.END, full)
        self.lbl_status.config(text="ترجمه انجام شد")

    def copy_text(self):
        txt = self.txt_result.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showinfo("کپی", "متنی برای کپی وجود ندارد.")
            return
        if pyperclip is None:
            try:
                self.master.clipboard_clear()
                self.master.clipboard_append(txt)
                messagebox.showinfo("کپی", "متن در کلیپ‌بورد قرار گرفت.")
            except Exception as e:
                messagebox.showerror("خطا", f"کپی انجام نشد:\n{e}")
            return
        try:
            pyperclip.copy(txt)
            messagebox.showinfo("کپی", "متن در کلیپ‌بورد قرار گرفت.")
        except Exception as e:
            messagebox.showerror("خطا", f"کپی انجام نشد:\n{e}")

    def save_text(self):
        txt = self.txt_result.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showinfo("ذخیره", "هیچ متنی برای ذخیره وجود ندارد.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[
                                            ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            messagebox.showinfo("ذخیره", "ذخیره با موفقیت انجام شد.")
        except Exception as e:
            messagebox.showerror("خطا", f"ذخیره انجام نشد:\n{e}")


class BazandehaApp:
    def __init__(self, root):
        self.root = root
        root.title("برنامه بازنده‌ها - ورود")
        root.geometry("960x640")
        root.minsize(820, 560)

        self.bg_image = None
        self.bg_photo = None

        self.frame_login = tk.Frame(root, bg="#f0f4f8")
        self.frame_login.pack(fill="both", expand=True)

        self.create_login_ui()

    def create_login_ui(self):
        f = self.frame_login

        self.canvas = tk.Canvas(f, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        self.container = tk.Frame(self.canvas, bg=self.canvas["bg"])
        self.win_id = self.canvas.create_window(
            0, 0, anchor="nw", window=self.container)

        self.btn_register = RoundedButton(self.container, text="ثبت نام", radius=12, padding=8,
                                          bg="#ffd24d", fg="#000", command=self.open_register, font=("Tahoma", 11, "bold"))
        self.btn_register.grid(row=0, column=0, sticky="nw", padx=18, pady=18)

        title = tk.Label(self.container, text="ورود به برنامه بازنده‌ها", font=(
            "B Nazanin", 28, "bold"), bg=self.container["bg"])
        title.grid(row=0, column=1, pady=18, padx=8)

        center = tk.Frame(self.container, bg=self.container["bg"])
        center.grid(row=1, column=0, columnspan=3, pady=6, padx=6)

        self.mascot = Mascot(center, width=150, height=150,
                             bg=self.container["bg"])
        self.mascot.grid(row=0, column=0, rowspan=2, padx=18, pady=10)

        entry_frame = tk.Frame(center, bg=self.container["bg"])
        entry_frame.grid(row=0, column=1, sticky="n")

        tk.Label(entry_frame, text="نام کاربری:", bg=self.container["bg"]).grid(
            row=0, column=0, sticky="w", padx=(0, 6))
        self.entry_username = tk.Entry(entry_frame, font=(
            "Tahoma", 12), bd=0, relief="flat", width=30, bg="white")
        self.entry_username.grid(row=1, column=0, pady=(0, 8))
        self.entry_username.bind(
            "<FocusIn>", lambda e: self.mascot.set_open(True))

        tk.Label(entry_frame, text="رمز عبور:", bg=self.container["bg"]).grid(
            row=2, column=0, sticky="w")
        pw_row = tk.Frame(entry_frame, bg=self.container["bg"])
        pw_row.grid(row=3, column=0, pady=(0, 8), sticky="w")
        self.entry_password = tk.Entry(pw_row, font=(
            "Tahoma", 12), bd=0, relief="flat", width=28, bg="white", show="*")
        self.entry_password.pack(side="left")
        self.entry_password.bind(
            "<FocusIn>", lambda e: self.mascot.set_open(False))
        self.entry_password.bind(
            "<FocusOut>", lambda e: self.mascot.set_open(True))

        self.show_pw = False

        def toggle_show():
            self.show_pw = not self.show_pw
            if self.show_pw:
                self.entry_password.config(show="")
                btn_show.config(text="مخفی کن")
            else:
                self.entry_password.config(show="*")
                btn_show.config(text="نمایش")
        btn_show = tk.Button(pw_row, text="نمایش",
                             command=toggle_show, font=("Tahoma", 9))
        btn_show.pack(side="left", padx=(6, 0))

        self.lbl_error = tk.Label(
            entry_frame, text="", fg="red", bg=self.container["bg"], font=("Tahoma", 10))
        self.lbl_error.grid(row=4, column=0, sticky="w", pady=(0, 8))

        lbl_forgot = tk.Label(entry_frame, text="آیا رمز عبور خود را فراموش کرده‌اید؟",
                              fg="blue", bg=self.container["bg"], cursor="hand2")
        lbl_forgot.grid(row=5, column=0, sticky="w")
        lbl_forgot.bind(
            "<Button-1>", lambda e: messagebox.showinfo("فراموشی رمز", "می‌خواستی فراموش نکنی 😉"))

        self.btn_login = RoundedButton(entry_frame, text="ورود", radius=12, padding=8,
                                       bg="#67c23a", fg="#fff", command=self.attempt_login, font=("Tahoma", 11, "bold"))
        self.btn_login.grid(row=6, column=0, pady=(14, 0), sticky="w")

    def _on_resize(self, event):
        w = event.width
        h = event.height
        try:
            self.canvas.coords(self.win_id, w/2 -
                               self.container.winfo_reqwidth()/2, h/6)
        except Exception:
            pass
        if self.bg_image is not None:
            self._draw_bg(w, h)

    def choose_bg(self):
        path = filedialog.askopenfilename(title="انتخاب تصویر پس‌زمینه", filetypes=[(
            "Image files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")])
        if not path:
            return
        self.load_bg(path)

    def open_register(self):
        RegisterWindow(self.root)

    def attempt_login(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get()
        if not username or not password:
            self.lbl_error.config(text="لطفاً نام کاربری و رمز را وارد کنید.")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT pw_hash, salt FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        if row is None:
            self.lbl_error.config(text="این نام کاربری وجود ندارد.")
            return
        pw_hash, salt = row
        ok = verify_password(pw_hash, salt, password)
        if not ok:
            self.lbl_error.config(text="رمز عبور نادرست است.")
            return

        self.lbl_error.config(text="")
        messagebox.showinfo("ورود موفق", f"خوش آمدید، {username} !")
        self.frame_login.pack_forget()
        MainApp(self.root, username)


class RegisterWindow(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.title("ثبت نام")
        self.geometry("420x320")
        self.resizable(False, False)
        self.configure(bg="#f7f7f7")
        tk.Label(self, text="ثبت نام در برنامه بازنده‌ها", font=(
            "B Nazanin", 16, "bold"), bg=self["bg"]).pack(pady=(12, 6))
        frm = tk.Frame(self, bg=self["bg"])
        frm.pack(pady=6, padx=12, fill="x")

        tk.Label(frm, text="نام کاربری:", bg=self["bg"]).grid(
            row=0, column=0, sticky="w")
        self.entry_user = tk.Entry(frm, width=30, bg="white", bd=1)
        self.entry_user.grid(row=1, column=0, pady=(4, 10))

        tk.Label(frm, text="رمز عبور:", bg=self["bg"]).grid(
            row=2, column=0, sticky="w")
        self.entry_pw = tk.Entry(frm, width=30, show="*", bg="white", bd=1)
        self.entry_pw.grid(row=3, column=0, pady=(4, 8))

        tk.Label(frm, text="تکرار رمز:", bg=self["bg"]).grid(
            row=4, column=0, sticky="w")
        self.entry_pw2 = tk.Entry(frm, width=30, show="*", bg="white", bd=1)
        self.entry_pw2.grid(row=5, column=0, pady=(4, 8))

        self.lbl_msg = tk.Label(self, text="", fg="red", bg=self["bg"])
        self.lbl_msg.pack()

        btns = tk.Frame(self, bg=self["bg"])
        btns.pack(pady=8)
        tk.Button(btns, text="ثبت نام", bg="#ffd24d",
                  command=self.register_user).pack(side="left", padx=8)
        tk.Button(btns, text="انصراف", command=self.destroy).pack(side="left")

    def register_user(self):
        u = self.entry_user.get().strip()
        p = self.entry_pw.get()
        p2 = self.entry_pw2.get()
        if not u or not p or not p2:
            self.lbl_msg.config(text="لطفاً همهٔ فیلدها را پر کنید.")
            return
        if p != p2:
            self.lbl_msg.config(text="رمزها مطابقت ندارند.")
            return
        if len(p) < 6:
            self.lbl_msg.config(text="رمز باید حداقل 6 کاراکتر باشد.")
            return
        h, s = hash_password(p)
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, pw_hash, salt) VALUES (?, ?, ?)", (u, h, s))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            self.lbl_msg.config(text="این نام کاربری قبلاً ثبت شده است.")
            return
        except Exception as e:
            self.lbl_msg.config(text=f"خطا در ثبت‌نام: {e}")
            return
        messagebox.showinfo(
            "ثبت نام موفق", "ثبت نام با موفقیت انجام شد. حالا می‌توانید وارد شوید.")
        self.destroy()


class MainApp(tk.Frame):
    def __init__(self, root, username):
        super().__init__(root, bg="#e9f3ff")
        self.root = root
        self.username = username
        self.pack(fill="both", expand=True)
        self.create_ui()

    def create_ui(self):
        top = tk.Frame(self, bg=self["bg"])
        top.pack(fill="x", pady=18)
        tk.Label(top, text=f"به برنامه بازنده‌ها خوش آمدید، {self.username}!", font=(
            "B Nazanin", 18, "bold"), bg=self["bg"]).pack()

        center = tk.Frame(self, bg=self["bg"])
        center.pack(expand=True)

        btn1 = RoundedButton(center, text="قرعه‌کشی بازنده‌ها", bg="#ffffff", fg="#000",
                             radius=16, padding=12, font=("Tahoma", 13, "bold"), command=self.open_lottery)
        btn1.pack(pady=12)
        btn2 = RoundedButton(center, text="عکس به متن", bg="#ffffff", fg="#000", radius=16, padding=12, font=(
            "Tahoma", 13, "bold"), command=self.open_imagetotext)
        btn2.pack(pady=12)

        tk.Button(self, text="خروج", command=self.logout).pack(
            side="bottom", pady=16)

    def logout(self):
        self.pack_forget()
        self.root.title("برنامه بازنده‌ها - ورود")
        BazandehaApp(self.root)

    def open_lottery(self):
        win = tk.Toplevel(self.root)
        LotteryApp(win)

    def open_imagetotext(self):
        win = tk.Toplevel(self.root)
        ImageToTextApp(win)


if __name__ == "__main__":
    root = tk.Tk()
    app = BazandehaApp(root)
    root.mainloop()