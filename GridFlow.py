import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, font, simpledialog
import json
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw, ImageGrab
import io
import base64
import math

# =============================================================================
# KÜTÜPHANE KONTROLLERİ
# =============================================================================
# PDF export için 'reportlab' kütüphanesi gereklidir.
# Eğer yüklü değilse program çökmez, sadece PDF özelliği devre dışı kalır.
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
    from reportlab.lib import colors
    from reportlab.graphics.shapes import Drawing, Line, Rect, Ellipse, Polygon
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# =============================================================================
# [AYAR] TEMA VE YAPILANDIRMA
# =============================================================================
# Uygulamanın renk paleti. Buradaki HEX kodlarını değiştirerek tasarımı özelleştirebilirsiniz.
THEME = {
    "bg_gradient_top": "#1a1a2e",    # Arka plan üst renk
    "bg_gradient_bottom": "#16213e", # Arka plan alt renk
    "menu_bg": "#0f3460",            # Menü çubuğu rengi
    "canvas_bg": "#2d2d44",          # Ana alan rengi
    "toolbar_bg": "#3c3c3c",         # Araç çubuğu rengi
    "editor_bg": "#2b2b2b",          # Editör penceresi arka planı
    "text_bg": "#ffffff",            # Kağıt rengi
    "text_fg": "#000000",            # Yazı rengi
    "btn_bg": "#555555",             # Buton arka planı
    "btn_fg": "white",               # Buton yazı rengi
    "accent": "#0078d7"              # Vurgu rengi (Mavi)
}

# Sayfa görünüm ayarları (A4 oranları)
PAGE_CONFIG = {
    "width": 210,
    "height": 297,
    "margin": 30
}

# =============================================================================
# SINIF: DrawingCanvas (Serbest Çizim Katmanı)
# =============================================================================
class DrawingCanvas(tk.Canvas):
    """
    Bu sınıf, yazı alanının üzerine şeffaf bir katman gibi yerleşir.
    Kalemle çizim, silgi ve basit şekil çizimleri burada yapılır.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="white", cursor="arrow", 
                        highlightthickness=0, **kwargs)
        
        # Çizim durumu değişkenleri
        self.drawing_enabled = False
        self.tool = "pen"       # Varsayılan araç: Kalem
        self.color = "#000000"  # Varsayılan renk: Siyah
        self.line_width = 2
        self.last_x = None
        self.last_y = None
        self.temp_item = None   # Çizim esnasındaki geçici şekil (önizleme için)
        
        # Mouse olaylarını bağla
        self.bind("<Button-1>", self.on_press)      # Tıklama
        self.bind("<B1-Motion>", self.on_drag)      # Sürükleme
        self.bind("<ButtonRelease-1>", self.on_release) # Bırakma
        
    def on_press(self, event):
        """Mouse tıklandığında başlangıç koordinatlarını al"""
        if not self.drawing_enabled:
            return
            
        self.last_x = event.x
        self.last_y = event.y
        
        # Eğer araç "Metin" ise direkt pencere açıp sor
        if self.tool == "text":
            text = simpledialog.askstring("Metin Ekle", "Metni girin:")
            if text:
                self.create_text(event.x, event.y, text=text, 
                               fill=self.color, font=("Arial", 14), 
                               anchor=tk.NW, tags="drawing")
    
    def on_drag(self, event):
        """Mouse sürüklendiğinde çizim yap"""
        if not self.drawing_enabled or self.last_x is None or self.last_y is None:
            return
            
        # Kalem aracı: Sürekli çizgi çizer
        if self.tool == "pen":
            self.create_line(self.last_x, self.last_y, event.x, event.y,
                           fill=self.color, width=self.line_width, 
                           capstyle=tk.ROUND, smooth=True, tags="drawing")
            self.last_x = event.x
            self.last_y = event.y
            
        # Silgi aracı: Arka plan renginde (beyaz) kalın çizgi çizer
        elif self.tool == "eraser":
            self.create_oval(event.x-10, event.y-10, event.x+10, event.y+10,
                           fill="white", outline="white", tags="drawing")
            
        # Şekil araçları: Sürüklerken geçici şekil gösterir (bırakınca sabitlenir)
        elif self.tool in ["line", "rectangle", "oval"]:
            if self.temp_item:
                self.delete(self.temp_item) # Önceki geçici şekli sil
            
            # Koordinatları hesapla
            x0 = min(self.last_x, event.x)
            y0 = min(self.last_y, event.y)
            x1 = max(self.last_x, event.x)
            y1 = max(self.last_y, event.y)
            
            if self.tool == "line":
                self.temp_item = self.create_line(
                    self.last_x, self.last_y, event.x, event.y,
                    fill=self.color, width=self.line_width, tags="temp")
            elif self.tool == "rectangle":
                self.temp_item = self.create_rectangle(
                    x0, y0, x1, y1,
                    outline=self.color, width=self.line_width, tags="temp")
            elif self.tool == "oval":
                self.temp_item = self.create_oval(
                    x0, y0, x1, y1,
                    outline=self.color, width=self.line_width, tags="temp")
    
    def on_release(self, event):
        """Mouse bırakıldığında şekli sabitle"""
        if not self.drawing_enabled:
            return
            
        if self.tool in ["line", "rectangle", "oval"] and self.last_x is not None and self.last_y is not None:
            if self.temp_item:
                self.delete(self.temp_item) # Geçiciyi sil ve gerçeği çiz
            
            x0 = min(self.last_x, event.x)
            y0 = min(self.last_y, event.y)
            x1 = max(self.last_x, event.x)
            y1 = max(self.last_y, event.y)
            
            if self.tool == "line":
                self.create_line(self.last_x, self.last_y, event.x, event.y,
                               fill=self.color, width=self.line_width, tags="drawing")
            elif self.tool == "rectangle":
                self.create_rectangle(x0, y0, x1, y1,
                                   outline=self.color, width=self.line_width, tags="drawing")
            elif self.tool == "oval":
                self.create_oval(x0, y0, x1, y1,
                              outline=self.color, width=self.line_width, tags="drawing")
            
            self.temp_item = None
        
        self.last_x = None
        self.last_y = None
    
    def clear_drawings(self):
        """Tüm çizimleri temizle"""
        self.delete("drawing")
        self.delete("temp")
    
    def toggle_drawing(self, enabled):
        """Çizim modunu aç/kapat ve imleci değiştir"""
        self.drawing_enabled = enabled
        if enabled:
            self.config(cursor="cross") # Çizim modu imleci
        else:
            self.config(cursor="")      # Normal imleç

    # Kaydetme işlemleri için çizimleri veriye dönüştürür
    def serialize_drawings(self):
        drawings = []
        for item in self.find_withtag("drawing"):
            item_type = self.type(item)
            coords = self.coords(item)
            options = self.itemconfigure(item)
            drawing_data = {
                "type": item_type,
                "coords": coords,
                "options": {k: options[k][4] for k in options if k not in ['tags']}
            }
            drawings.append(drawing_data)
        return drawings

    # Kaydedilen veriden çizimleri geri yükler
    def load_drawings(self, drawings):
        self.clear_drawings()
        for drawing in drawings:
            item_type = drawing["type"]
            coords = drawing["coords"]
            options = drawing["options"]
            options["tags"] = "drawing"
            if item_type == "line":
                self.create_line(coords, **options)
            elif item_type == "rectangle":
                self.create_rectangle(coords, **options)
            elif item_type == "oval":
                self.create_oval(coords, **options)
            elif item_type == "text":
                self.create_text(coords[:2], **options)

# =============================================================================
# SINIF: NoteEditor (Not Düzenleme Penceresi)
# =============================================================================
class NoteEditor(tk.Toplevel):
    """Gelişmiş Not Editörü - Hem metin hem çizim destekler"""
    def __init__(self, parent, page_id, initial_content="", callback=None):
        super().__init__(parent)
        
        self.page_id = page_id
        self.callback = callback
        self.title(f"Not Defteri - {page_id}")
        self.geometry("1100x900")
        self.configure(bg=THEME["editor_bg"])
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self._after_id = None
        self.modified = False
        
        # Çizim modu durumu
        self.drawing_mode = False
        
        # İçerik verilerini saklamak için listeler
        self.embedded_objects = []
        self.tables_data = []
        self.shapes_data = []
        self.images_data = []
        
        # Widget ile veri objesi arasındaki ilişkiyi tutar
        self.widget_to_obj = {}
        
        # Varsayılan yazı rengi
        self.text_color = "#000000"
        
        self.setup_ui()
        
        if initial_content:
            self.load_content(initial_content)
            
        self.center_window()
        
    def load_content(self, content):
        """İçeriği yükle (JSON'dan veya eski formattan)"""
        try:
            self.tables_data = content.get("tables", [])
            self.shapes_data = content.get("shapes", [])
            self.images_data = content.get("images", [])
            
            # 'dump' anahtarı varsa Tkinter text widget içeriğini detaylı yükler
            dump = content.get("dump", None)
            if dump:
                # Dump'tan yükle (Gelişmiş yükleme)
                for item in dump:
                    key = item[0]
                    val = item[1]
                    idx = item[2]
                    if key == 'text':
                        self.text_area.insert(idx, val)
                    elif key == 'tagon':
                        self.text_area.tag_add(val, idx)
                    elif key == 'tagoff':
                        self.text_area.tag_remove(val, idx)
                    elif key == 'mark':
                        self.text_area.mark_set(val, idx)
                    elif key == 'window':
                        # Gömülü nesneleri (Tablo, Şekil, Resim) tekrar oluştur
                        obj_type, obj_id = val.split(':')
                        obj_id = int(obj_id)
                        if obj_type == 'shape':
                            shape_data = self.shapes_data[obj_id]
                            shape_canvas = tk.Canvas(self.text_area, width=shape_data["width"], height=shape_data["height"],
                                                    bg="white", relief=tk.FLAT, bd=0, highlightthickness=0)
                            cx, cy = shape_data["width"] // 2, shape_data["height"] // 2
                            self._draw_shape_on_canvas(shape_canvas, shape_data["type"], cx, cy, shape_data["width"]-20, shape_data["height"]-20, shape_data["color"])
                            self.text_area.window_create(idx, window=shape_canvas, align=tk.CENTER)
                            widget_path = str(shape_canvas)
                            self.widget_to_obj[widget_path] = ('shape', obj_id)
                        elif obj_type == 'image':
                            img_data = self.images_data[obj_id]
                            img_bytes = base64.b64decode(img_data["base64"])
                            img = Image.open(io.BytesIO(img_bytes))
                            photo = ImageTk.PhotoImage(img)
                            label = tk.Label(self.text_area, image=photo, bg="white", relief=tk.FLAT, bd=0)
                            label.image = photo
                            self.text_area.window_create(idx, window=label, align=tk.CENTER)
                            widget_path = str(label)
                            self.widget_to_obj[widget_path] = ('image', obj_id)
                        elif obj_type == 'table':
                            table_content = self.tables_data[obj_id]
                            rows = len(table_content)
                            cols = len(table_content[0]) if rows > 0 else 0
                            table_frame = tk.Frame(self.text_area, bg="#ccc", relief=tk.FLAT, bd=0)
                            cells = []
                            for r in range(rows):
                                row_cells = []
                                for c in range(cols):
                                    cell = tk.Entry(table_frame, width=15, relief="solid", bd=1, 
                                                  font=("Calibri", 10), justify=tk.LEFT)
                                    cell.grid(row=r, column=c, padx=1, pady=1, sticky="nsew")
                                    cell.insert(0, table_content[r][c])
                                    row_cells.append(cell)
                                cells.append(row_cells)
                            self.tables_data[obj_id] = table_content
                            self.text_area.window_create(idx, window=table_frame, align=tk.BASELINE)
                            widget_path = str(table_frame)
                            self.widget_to_obj[widget_path] = ('table', obj_id)
            else:
                # Eski sürümden yükleme (Basit metin)
                text = content.get("text", "")
                if text:
                    self.text_area.insert("1.0", text)
                self.recreate_embedded_objects()
            
            # Serbest çizimleri yükle
            drawings = content.get("drawings", [])
            self.drawing_canvas.load_drawings(drawings)
            
        except Exception as e:
            messagebox.showerror("Yükleme Hatası", f"İçerik yüklenirken hata: {str(e)}")
            print(f"İçerik yükleme hatası: {e}")
            import traceback
            traceback.print_exc()
        
        self.update_status_lazy()
        
    def recreate_embedded_objects(self):
        """Basit yüklemede (dump yoksa) nesneleri sona ekler"""
        try:
            # Görselleri ekle
            for img_data in self.images_data:
                try:
                    img_bytes = base64.b64decode(img_data["base64"])
                    img = Image.open(io.BytesIO(img_bytes))
                    img.thumbnail((img_data["width"], img_data["height"]), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    label = tk.Label(self.text_area, image=photo, bg="white", relief=tk.FLAT, bd=0)
                    label.image = photo
                    
                    self.text_area.insert(tk.END, "\n")
                    self.text_area.window_create(tk.END, window=label, align=tk.CENTER)
                    self.text_area.insert(tk.END, "\n")
                except Exception as e:
                    print(f"Görsel yeniden oluşturma hatası: {e}")
            
            # Tabloları ekle
            for table_content in self.tables_data:
                if isinstance(table_content, list) and table_content:
                    rows = len(table_content)
                    cols = len(table_content[0]) if rows > 0 else 0
                    if rows > 0 and cols > 0:
                        table_frame = tk.Frame(self.text_area, bg="#ccc", relief=tk.FLAT, bd=0)
                        
                        cells = []
                        for r in range(rows):
                            row_cells = []
                            for c in range(cols):
                                cell = tk.Entry(table_frame, width=15, relief="solid", bd=1, 
                                              font=("Calibri", 10), justify=tk.LEFT)
                                cell.grid(row=r, column=c, padx=1, pady=1, sticky="nsew")
                                cell.insert(0, table_content[r][c])
                                row_cells.append(cell)
                            cells.append(row_cells)
                        
                        self.tables_data.append(table_content)
                        
                        self.text_area.insert(tk.END, "\n")
                        self.text_area.window_create(tk.END, window=table_frame, align=tk.BASELINE)
                        self.text_area.insert(tk.END, "\n")
            
            # Şekilleri ekle
            for shape_data in self.shapes_data:
                try:
                    shape_type = shape_data["type"]
                    shape_name = shape_data["name"]
                    width = shape_data["width"]
                    height = shape_data["height"]
                    color = shape_data["color"]
                    
                    shape_canvas = tk.Canvas(self.text_area, width=width, height=height,
                                            bg="white", relief=tk.FLAT, bd=0, highlightthickness=0)
                    
                    cx, cy = width // 2, height // 2
                    self._draw_shape_on_canvas(shape_canvas, shape_type, cx, cy, width-20, height-20, color)
                    
                    self.text_area.insert(tk.END, "\n")
                    self.text_area.window_create(tk.END, window=shape_canvas, align=tk.CENTER)
                    self.text_area.insert(tk.END, "\n")
                except Exception as e:
                    print(f"Şekil yeniden oluşturma hatası: {e}")
        except Exception as e:
            print(f"Embedded objects yeniden oluşturma hatası: {e}")
        
    def center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def setup_ui(self):
        self._create_menu()
        self._create_toolbar()
        self._create_editor_area()
        self._create_status_bar()
        self._bind_events()

    def _create_menu(self):
        """Üst menü çubuğunu oluşturur"""
        menubar = tk.Menu(self, bg=THEME["toolbar_bg"], fg="white")
        self.config(menu=menubar)
        
        # Dosya Menüsü
        file_menu = tk.Menu(menubar, tearoff=0, bg=THEME["toolbar_bg"], fg="white")
        menubar.add_cascade(label="Dosya", menu=file_menu)
        file_menu.add_command(label="Kaydet", command=self.save_note, accelerator="Ctrl+S")
        file_menu.add_command(label="PDF Olarak Kaydet", command=self.export_to_pdf, accelerator="Ctrl+P")
        file_menu.add_separator()
        file_menu.add_command(label="Kapat", command=self.close_editor)
        
        # Ekle Menüsü
        insert_menu = tk.Menu(menubar, tearoff=0, bg=THEME["toolbar_bg"], fg="white")
        menubar.add_cascade(label="Ekle", menu=insert_menu)
        insert_menu.add_command(label="📷 Görsel Ekle...", command=self.insert_image)
        insert_menu.add_separator()
        insert_menu.add_command(label="▦ Tablo Ekle...", command=self.insert_table_dialog)
        insert_menu.add_command(label="📐 Şekil Galerisi...", command=self.open_shape_gallery)
        
        # Çizim Menüsü
        draw_menu = tk.Menu(menubar, tearoff=0, bg=THEME["toolbar_bg"], fg="white")
        menubar.add_cascade(label="Çizim", menu=draw_menu)
        draw_menu.add_command(label="🎨 Çizim Modunu Aç/Kapat", command=self.toggle_drawing_mode)
        draw_menu.add_command(label="🗑️ Çizimleri Temizle", command=self.clear_all_drawings)
        
        # Ok Menüsü
        arrow_menu = tk.Menu(menubar, tearoff=0, bg=THEME["toolbar_bg"], fg="white")
        menubar.add_cascade(label="Ok", menu=arrow_menu)
        for text, symbol in [("Sağa", "→"), ("Sola", "←"), ("Yukarı", "↑"), 
                            ("Aşağı", "↓"), ("Kalın Sağa", "⇒"), ("Kalın Sola", "⇐")]:
            arrow_menu.add_command(label=f"{text} {symbol}", 
                                  command=lambda s=symbol: self.insert_text(s))

    def _create_toolbar(self):
        """Araç çubuğunu (Toolbar) oluşturur"""
        toolbar = tk.Frame(self, bg=THEME["toolbar_bg"], relief=tk.RAISED, bd=1)
        toolbar.grid(row=0, column=0, sticky="ew")
        
        # Satır 1: Dosya ve Medya Araçları
        row1 = tk.Frame(toolbar, bg=THEME["toolbar_bg"])
        row1.pack(fill=tk.X, padx=5, pady=2)
        
        self._add_btn(row1, "💾 Kaydet", self.save_note, width=10)
        self._add_btn(row1, "📄 PDF", self.export_to_pdf, width=10)
        
        tk.Frame(row1, width=20, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        self._add_btn(row1, "📷 Görsel", self.insert_image, width=10)
        
        tk.Frame(row1, width=10, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        self._add_btn(row1, "▦ Tablo", self.insert_table_dialog, width=8)
        self._add_btn(row1, "📐 Şekiller", self.open_shape_gallery, width=10)
        
        tk.Frame(row1, width=10, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        # Ok butonları
        for symbol in ["→", "←", "↑", "↓", "⇒"]:
            self._add_btn(row1, symbol, lambda s=symbol: self.insert_text(s), width=3)
        
        # Satır 2: Formatlama ve Çizim
        row2 = tk.Frame(toolbar, bg=THEME["toolbar_bg"])
        row2.pack(fill=tk.X, padx=5, pady=2)
        
        self.font_family = tk.StringVar(value="Calibri")
        ttk.Combobox(row2, textvariable=self.font_family, 
                    values=["Calibri", "Arial", "Times New Roman", "Courier New", "Verdana"], 
                    width=15, state="readonly").pack(side=tk.LEFT, padx=2)
        
        self.font_size = tk.IntVar(value=11)
        combo_size = ttk.Combobox(row2, textvariable=self.font_size, 
                                 values=[8,9,10,11,12,14,16,18,20,24,28,36,48], 
                                 width=4, state="readonly")
        combo_size.pack(side=tk.LEFT, padx=2)
        combo_size.bind("<<ComboboxSelected>>", self.apply_font)
        
        self.bold_var = tk.BooleanVar()
        self.italic_var = tk.BooleanVar()
        self.underline_var = tk.BooleanVar()
        
        tk.Frame(row2, width=10, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        self._add_checkbtn(row2, "B", self.bold_var, self.apply_font)
        self._add_checkbtn(row2, "I", self.italic_var, self.apply_font)
        self._add_checkbtn(row2, "U", self.underline_var, self.apply_font)
        
        tk.Frame(row2, width=10, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        # Yazı rengi
        tk.Label(row2, text="Renk:", bg=THEME["toolbar_bg"], fg="white").pack(side=tk.LEFT, padx=5)
        self.text_color_btn = tk.Button(row2, text="  A  ", width=3,
                                       bg=self.text_color, fg="white",
                                       command=self.choose_text_color, cursor="hand2")
        self.text_color_btn.pack(side=tk.LEFT, padx=2)
        
        tk.Frame(row2, width=10, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        self._add_btn(row2, "⬅", lambda: self.set_alignment("left"), width=3)
        self._add_btn(row2, "⬌", lambda: self.set_alignment("center"), width=3)
        self._add_btn(row2, "➡", lambda: self.set_alignment("right"), width=3)
        
        tk.Frame(row2, width=20, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        # Çizim kontrolleri
        self.drawing_mode_btn = tk.Button(row2, text="🎨 Çizim: KAPALI", 
                                         command=self.toggle_drawing_mode,
                                         bg=THEME["btn_bg"], fg="white", width=15,
                                         cursor="hand2")
        self.drawing_mode_btn.pack(side=tk.LEFT, padx=5)
        
        # Satır 3: Çizim Araçları (başlangıçta gizli)
        self.draw_toolbar = tk.Frame(toolbar, bg=THEME["toolbar_bg"])
        
        tk.Label(self.draw_toolbar, text="Araç:", bg=THEME["toolbar_bg"], 
                fg="white").pack(side=tk.LEFT, padx=5)
        
        self.draw_tool_var = tk.StringVar(value="pen")
        draw_tools = [
            ("✏️", "pen", "Kalem"),
            ("📏", "line", "Çizgi"),
            ("⬜", "rectangle", "Dikdörtgen"),
            ("⭕", "oval", "Oval"),
            ("🗑️", "eraser", "Silgi"),
            ("T", "text", "Metin")
        ]
        
        for emoji, value, tooltip in draw_tools:
            btn = tk.Radiobutton(self.draw_toolbar, text=emoji, 
                               variable=self.draw_tool_var, value=value,
                               bg=THEME["btn_bg"], fg="white",
                               selectcolor=THEME["accent"], indicatoron=False,
                               command=self.change_draw_tool, width=3)
            btn.pack(side=tk.LEFT, padx=1)
        
        tk.Frame(self.draw_toolbar, width=10, bg=THEME["toolbar_bg"]).pack(side=tk.LEFT)
        
        tk.Label(self.draw_toolbar, text="Renk:", bg=THEME["toolbar_bg"],
                fg="white").pack(side=tk.LEFT, padx=5)
        
        self.draw_color_btn = tk.Button(self.draw_toolbar, text="    ", width=4,
                                       bg="#000000", command=self.choose_draw_color,
                                       cursor="hand2")
        self.draw_color_btn.pack(side=tk.LEFT, padx=2)
        
        tk.Label(self.draw_toolbar, text="Kalınlık:", bg=THEME["toolbar_bg"],
                fg="white").pack(side=tk.LEFT, padx=5)
        
        self.draw_width_var = tk.IntVar(value=2)
        ttk.Spinbox(self.draw_toolbar, from_=1, to=20, textvariable=self.draw_width_var,
                   width=5, command=self.change_draw_width).pack(side=tk.LEFT, padx=2)
        
        tk.Button(self.draw_toolbar, text="🗑️ Temizle", command=self.clear_all_drawings,
                 bg=THEME["btn_bg"], fg="white", width=10).pack(side=tk.LEFT, padx=5)

    def _add_btn(self, parent, text, command, width=3):
        btn = tk.Button(parent, text=text, command=command, width=width, 
                        bg=THEME["btn_bg"], fg=THEME["btn_fg"], relief=tk.FLAT,
                        cursor="hand2", activebackground="#666666")
        btn.pack(side=tk.LEFT, padx=1, pady=1)

    def _add_checkbtn(self, parent, text, variable, command):
        cb = tk.Checkbutton(parent, text=text, variable=variable, command=command, width=3, 
                            bg=THEME["btn_bg"], fg=THEME["btn_fg"], selectcolor="#444", 
                            indicatoron=False, cursor="hand2")
        cb.pack(side=tk.LEFT, padx=1, pady=1)

    def _create_editor_area(self):
        """Metin ve çizim alanlarının bulunduğu ana frame'i oluşturur"""
        container = tk.Frame(self, bg="#4a4a4a")
        container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # A4 Kağıdı (Beyaz Alan)
        a4_frame = tk.Frame(container, bg="white", relief=tk.RAISED, bd=3)
        a4_frame.grid(row=0, column=0, sticky="nsew")
        a4_frame.grid_rowconfigure(0, weight=1)
        a4_frame.grid_columnconfigure(0, weight=1)
        
        # Metin Alanı (Text Widget)
        self.text_area = tk.Text(a4_frame, wrap=tk.WORD, undo=True, 
                                font=("Calibri", 11), bg="white", fg="black",
                                padx=60, pady=40, relief=tk.FLAT,
                                insertbackground="black")
        self.text_area.grid(row=0, column=0, sticky="nsew")
        
        # Kaydırma Çubuğu
        scrollbar = tk.Scrollbar(a4_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_area.config(yscrollcommand=scrollbar.set)
        
        # Çizim Katmanı (Overlay)
        # Bu frame, text alanının üzerine gelir ve DrawingCanvas'ı tutar
        self.drawing_frame = tk.Frame(a4_frame, bg="white")
        self.drawing_canvas = DrawingCanvas(self.drawing_frame)
        self.drawing_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Başlangıçta çizim katmanı gizlidir (.place kullanılmaz)

    def _create_status_bar(self):
        """Alt durum çubuğunu oluşturur"""
        status_frame = tk.Frame(self, bg=THEME["toolbar_bg"])
        status_frame.grid(row=2, column=0, sticky="ew")
        
        self.status_bar = tk.Label(status_frame, text="Hazır", anchor=tk.W, 
                                   bg=THEME["toolbar_bg"], fg="white", padx=10, pady=5)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        if PDF_AVAILABLE:
            tk.Label(status_frame, text="✓ PDF", bg=THEME["toolbar_bg"], 
                    fg="#00ff00", padx=10).pack(side=tk.RIGHT)

    def _bind_events(self):
        """Klavye kısayollarını tanımlar"""
        self.bind("<Control-s>", lambda e: self.save_note())
        self.bind("<Control-p>", lambda e: self.export_to_pdf())
        self.bind("<Control-d>", lambda e: self.toggle_drawing_mode())
        self.text_area.bind("<KeyRelease>", self.on_key_release)
        self.text_area.bind("<<Modified>>", self.on_modified)

    # === ÇİZİM MOD KONTROLÜ ===
    def toggle_drawing_mode(self):
        """Çizim modunu açar veya kapatır"""
        self.drawing_mode = not self.drawing_mode
        
        if self.drawing_mode:
            # Çizim modu AÇIK
            try:
                self.drawing_mode_btn.config(text="🎨 Çizim: AÇIK", bg="#00aa00")
                self.draw_toolbar.pack(fill=tk.X, padx=5, pady=2)
                self.drawing_canvas.toggle_drawing(True)
                
                # Çizim frame'ini text area üzerine yerleştir (Katmanı öne al)
                self.drawing_frame.place(x=0, y=0, relwidth=1, relheight=1)
                
                self.text_area.config(state=tk.DISABLED)  # Text area'yı devre dışı bırak
                if hasattr(self, 'status_bar'):
                    self.status_bar.config(text="Çizim modu AÇIK - Araç seçin ve çizin")
            except Exception as e:
                messagebox.showerror("Hata", f"Çizim modu açılamadı: {str(e)}")
                self.drawing_mode = False  # Geri al
        else:
            # Çizim modu KAPALI
            try:
                self.drawing_mode_btn.config(text="🎨 Çizim: KAPALI", bg=THEME["btn_bg"])
                self.draw_toolbar.pack_forget()
                self.drawing_canvas.toggle_drawing(False)
                
                # Çizim frame'ini gizle (Katmanı arkaya at)
                self.drawing_frame.place_forget()
                
                self.text_area.config(state=tk.NORMAL)  # Text area'yı etkinleştir
                if hasattr(self, 'status_bar'):
                    self.status_bar.config(text="Metin modu AÇIK - Yazı yazabilirsiniz")
            except Exception as e:
                messagebox.showerror("Hata", f"Çizim modu kapatılamadı: {str(e)}")
    
    def change_draw_tool(self):
        """Seçilen çizim aracını değiştirir"""
        self.drawing_canvas.tool = self.draw_tool_var.get()
        tool_names = {
            "pen": "Kalem", "line": "Çizgi", "rectangle": "Dikdörtgen",
            "oval": "Oval", "eraser": "Silgi", "text": "Metin"
        }
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=f"Araç: {tool_names.get(self.draw_tool_var.get())}")
    
    def choose_draw_color(self):
        """Çizim rengini seçer"""
        color = colorchooser.askcolor(title="Çizim Rengi Seç")
        if color[1]:
            self.draw_color_btn.config(bg=color[1])
            self.drawing_canvas.color = color[1]
    
    def change_draw_width(self):
        """Çizim kalınlığını değiştirir"""
        self.drawing_canvas.line_width = self.draw_width_var.get()
    
    def clear_all_drawings(self):
        """Tüm çizimleri temizler"""
        if messagebox.askyesno("Temizle", "Tüm çizimleri silmek istediğinizden emin misiniz?"):
            self.drawing_canvas.clear_drawings()
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text="Çizimler temizlendi")

    # === YAZI RENGİ ===
    def choose_text_color(self):
        """Yazı rengi seçimi ve uygulaması"""
        color = colorchooser.askcolor(title="Yazı Rengi Seç", initialcolor=self.text_color)
        if color[1]:
            self.text_color = color[1]
            self.text_color_btn.config(bg=color[1])
            
            # Seçili metne renk uygula
            try:
                self.text_area.tag_add("color", "sel.first", "sel.last")
                self.text_area.tag_config("color", foreground=color[1])
            except tk.TclError:
                # Seçim yoksa tüm metne uygula
                self.text_area.config(fg=color[1])

    # === GÖRSEL EKLEME ===
    def insert_image(self):
        """Dosyadan görsel seçip metin alanına ekler"""
        filename = filedialog.askopenfilename(
            title="Görsel Seç",
            filetypes=[
                ("Görsel Dosyaları", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        
        if filename:
            try:
                # Görseli yükle ve yeniden boyutlandır
                img = Image.open(filename)
                
                # Maksimum boyut
                max_width = 400
                max_height = 300
                
                # Oranı koru
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Base64'e çevir (Kaydetmek için)
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                # Label olarak ekle (Göstermek için)
                photo = ImageTk.PhotoImage(img)
                
                label = tk.Label(self.text_area, image=photo, bg="white", 
                               relief=tk.FLAT, bd=0)
                label.image = photo  # Referansı tut
                
                # Text alanına göm
                self.text_area.window_create(tk.INSERT, window=label, align=tk.CENTER)
                self.text_area.insert(tk.INSERT, "\n")
                
                # Veriyi kaydet
                self.images_data.append({
                    "base64": img_base64,
                    "width": img.width,
                    "height": img.height
                })
                
                self.modified = True
                self.update_status_lazy()
                
            except Exception as e:
                messagebox.showerror("Hata", f"Görsel yüklenemedi:\n{str(e)}")

    # === TABLO İŞLEMLERİ ===
    def insert_table_dialog(self):
        rows = simpledialog.askinteger("Tablo", "Satır sayısı:", minvalue=1, maxvalue=20, initialvalue=3)
        cols = simpledialog.askinteger("Tablo", "Sütun sayısı:", minvalue=1, maxvalue=10, initialvalue=3)
        
        if rows is not None and cols is not None:
            self.insert_table(rows, cols)

    def insert_table(self, rows, cols):
        """Metin içine düzenlenebilir tablo ekler"""
        table_frame = tk.Frame(self.text_area, bg="#ccc", bd=2, relief=tk.SOLID)
        
        cells = []
        cell_widgets = []
        for r in range(rows):
            row_cells = []
            for c in range(cols):
                cell = tk.Entry(table_frame, width=15, relief="solid", bd=1, 
                              font=("Calibri", 10), justify=tk.LEFT)
                cell.grid(row=r, column=c, padx=1, pady=1, sticky="nsew")
                row_cells.append(cell)
                cell_widgets.append(cell)
            cells.append(row_cells)
        
        table_id = len(self.tables_data)
        self.tables_data.append({
            "id": table_id,
            "rows": rows,
            "cols": cols,
            "cells": cells,
            "widgets": cell_widgets
        })
        
        self.text_area.window_create(tk.INSERT, window=table_frame, align=tk.BASELINE)
        self.text_area.insert(tk.INSERT, "\n")

    # === ŞEKİL GALERİSİ (Word Benzeri) ===
    def open_shape_gallery(self):
        """Word benzeri gelişmiş şekil galerisi penceresini açar"""
        try:
            gallery = tk.Toplevel(self)
            gallery.title("Şekil Galerisi")
            gallery.geometry("700x600")
            gallery.configure(bg=THEME["editor_bg"])
            
            # Başlık
            header = tk.Frame(gallery, bg=THEME["menu_bg"], height=50)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            tk.Label(header, text="📐 Şekil Galerisi - İstediğinizi Seçin", 
                    bg=THEME["menu_bg"], fg="white",
                    font=("Calibri", 14, "bold")).pack(pady=12)
            
            # Kategori seçimi
            cat_frame = tk.Frame(gallery, bg=THEME["toolbar_bg"])
            cat_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(cat_frame, text="Kategori:", bg=THEME["toolbar_bg"],
                    fg="white", font=("Calibri", 10, "bold")).pack(side=tk.LEFT, padx=5)
            
            category_var = tk.StringVar(value="basic")
            categories = [
                ("Temel Şekiller", "basic"),
                ("Oklar", "arrows"),
                ("Yıldızlar", "stars"),
                ("Çokgenler", "polygons"),
                ("Akış Diyagramı", "flowchart"),
                ("Banner/Etiket", "banners")
            ]
            
            for text, value in categories:
                tk.Radiobutton(cat_frame, text=text, variable=category_var,
                              value=value, bg=THEME["btn_bg"], fg="white",
                              selectcolor=THEME["accent"], indicatoron=False,
                              command=lambda: update_shapes()).pack(side=tk.LEFT, padx=2)
            
            # Şekiller container
            shapes_container = tk.Frame(gallery, bg=THEME["canvas_bg"])
            shapes_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Canvas ve scrollbar
            canvas = tk.Canvas(shapes_container, bg=THEME["canvas_bg"], highlightthickness=0)
            scrollbar = tk.Scrollbar(shapes_container, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=THEME["canvas_bg"])
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Şekil veritabanı (Tanımlar)
            shape_catalog = {
                "basic": [
                    ("rect", "Dikdörtgen", 150, 100),
                    ("square", "Kare", 120, 120),
                    ("oval", "Oval", 150, 100),
                    ("circle", "Daire", 120, 120),
                    ("triangle", "Üçgen", 130, 110),
                    ("diamond", "Baklava", 120, 120)
                ],
                "arrows": [
                    ("arrow_right", "Sağ Ok", 150, 60),
                    ("arrow_left", "Sol Ok", 150, 60),
                    ("arrow_up", "Yukarı Ok", 80, 120),
                    ("arrow_down", "Aşağı Ok", 80, 120),
                    ("arrow_double", "Çift Ok", 150, 60),
                    ("arrow_curved", "Eğri Ok", 130, 100)
                ],
                "stars": [
                    ("star_5", "5 Köşeli Yıldız", 120, 120),
                    ("star_6", "6 Köşeli Yıldız", 120, 120),
                    ("star_8", "8 Köşeli Yıldız", 120, 120),
                    ("star_burst", "Patlama", 130, 130)
                ],
                "polygons": [
                    ("pentagon", "Beşgen", 120, 120),
                    ("hexagon", "Altıgen", 130, 110),
                    ("octagon", "Sekizgen", 120, 120),
                    ("trapezoid", "Yamuk", 150, 100)
                ],
                "flowchart": [
                    ("process", "İşlem", 150, 80),
                    ("decision", "Karar", 130, 130),
                    ("data", "Veri", 150, 90),
                    ("start_end", "Başlat/Bitir", 140, 70),
                    ("document", "Döküman", 130, 110)
                ],
                "banners": [
                    ("ribbon", "Şerit", 180, 60),
                    ("badge", "Rozet", 110, 110),
                    ("label", "Etiket", 150, 70),
                    ("callout", "Açıklama Balonu", 150, 100)
                ]
            }
            
            def update_shapes():
                # Mevcut şekilleri temizle
                for widget in scrollable_frame.winfo_children():
                    widget.destroy()
                
                category = category_var.get()
                shapes = shape_catalog.get(category, [])
                
                row = 0
                col = 0
                for shape_id, shape_name, width, height in shapes:
                    # Şekil frame
                    shape_frame = tk.Frame(scrollable_frame, bg="white",
                                          relief=tk.RAISED, bd=2, width=180, height=180)
                    shape_frame.grid(row=row, column=col, padx=10, pady=10)
                    shape_frame.grid_propagate(False)
                    
                    # Önizleme canvas
                    preview = tk.Canvas(shape_frame, width=160, height=140,
                                      bg="white", highlightthickness=0)
                    preview.pack(pady=5)
                    
                    # Şekli çiz (önizleme)
                    self._draw_shape_preview(preview, shape_id, 80, 70, 60, 50)
                    
                    # İsim
                    tk.Label(shape_frame, text=shape_name, bg="white",
                            font=("Calibri", 9)).pack()
                    
                    # Ekle butonu
                    btn = tk.Button(shape_frame, text="Ekle", bg=THEME["accent"],
                                  fg="white", cursor="hand2",
                                  command=lambda s=shape_id, n=shape_name, w=width, h=height: 
                                          self.insert_advanced_shape(s, n, w, h, gallery))
                    btn.pack(pady=3)
                    
                    # Hover effect
                    def on_enter(e, f=shape_frame):
                        f.config(relief=tk.SOLID, bd=3)
                    def on_leave(e, f=shape_frame):
                        f.config(relief=tk.RAISED, bd=2)
                    
                    shape_frame.bind("<Enter>", on_enter)
                    shape_frame.bind("<Leave>", on_leave)
                    
                    col += 1
                    if col >= 3:
                        col = 0
                        row += 1
            
            update_shapes()
        except Exception as e:
            messagebox.showerror("Hata", f"Şekil galerisi açılamadı: {str(e)}")
    
    def _draw_shape_preview(self, canvas, shape_type, cx, cy, w, h):
        """Şekil önizlemesi çiz - Detaylı geometrik hesaplamalar"""
        color = THEME["accent"]
        
        if shape_type == "rect":
            canvas.create_rectangle(cx-w//2, cy-h//2, cx+w//2, cy+h//2,
                                   outline=color, width=2)
        elif shape_type == "square":
            canvas.create_rectangle(cx-w//2, cy-w//2, cx+w//2, cy+w//2,
                                   outline=color, width=2)
        elif shape_type == "oval":
            canvas.create_oval(cx-w//2, cy-h//2, cx+w//2, cy+h//2,
                              outline=color, width=2)
        elif shape_type == "circle":
            canvas.create_oval(cx-w//2, cy-w//2, cx+w//2, cy+w//2,
                              outline=color, width=2)
        elif shape_type == "triangle":
            canvas.create_polygon(cx, cy-h//2, cx-w//2, cy+h//2, cx+w//2, cy+h//2,
                                outline=color, fill="", width=2)
        elif shape_type == "diamond":
            canvas.create_polygon(cx, cy-h//2, cx+w//2, cy, cx, cy+h//2, cx-w//2, cy,
                                outline=color, fill="", width=2)
        elif shape_type == "arrow_right":
            # Basit ok
            canvas.create_line(cx-w//2, cy, cx+w//2-15, cy, fill=color, width=3, arrow=tk.LAST, arrowshape=(16,20,8))
        elif shape_type == "arrow_left":
            canvas.create_line(cx+w//2, cy, cx-w//2+15, cy, fill=color, width=3, arrow=tk.LAST, arrowshape=(16,20,8))
        elif shape_type == "arrow_up":
            canvas.create_line(cx, cy+h//2, cx, cy-h//2+15, fill=color, width=3, arrow=tk.LAST, arrowshape=(16,20,8))
        elif shape_type == "arrow_down":
            canvas.create_line(cx, cy-h//2, cx, cy+h//2-15, fill=color, width=3, arrow=tk.LAST, arrowshape=(16,20,8))
        elif shape_type == "star_5":
            # 5 köşeli yıldız hesaplaması
            import math
            points = []
            for i in range(10):
                angle = math.pi / 2 + (2 * math.pi * i / 10)
                r = w//2 if i % 2 == 0 else w//4
                x = cx + r * math.cos(angle)
                y = cy - r * math.sin(angle)
                points.extend([x, y])
            canvas.create_polygon(points, outline=color, fill="", width=2)
        elif shape_type == "pentagon":
            import math
            points = []
            for i in range(5):
                angle = math.pi / 2 + (2 * math.pi * i / 5)
                x = cx + w//2 * math.cos(angle)
                y = cy - w//2 * math.sin(angle)
                points.extend([x, y])
            canvas.create_polygon(points, outline=color, fill="", width=2)
        elif shape_type == "hexagon":
            import math
            points = []
            for i in range(6):
                angle = 2 * math.pi * i / 6
                x = cx + w//2 * math.cos(angle)
                y = cy + w//2 * math.sin(angle)
                points.extend([x, y])
            canvas.create_polygon(points, outline=color, fill="", width=2)
        else:
            # Varsayılan: dikdörtgen
            canvas.create_rectangle(cx-w//2, cy-h//2, cx+w//2, cy+h//2,
                                   outline=color, width=2)
    
    def insert_advanced_shape(self, shape_type, shape_name, width, height, gallery_window):
        """Gelişmiş şekil ekle"""
        shape_canvas = tk.Canvas(self.text_area, width=width, height=height,
                                bg="white", relief=tk.FLAT, bd=0, highlightthickness=0)
        
        color = THEME["accent"]
        cx, cy = width // 2, height // 2
        
        # Şekli çiz
        self._draw_shape_on_canvas(shape_canvas, shape_type, cx, cy, width-20, height-20, color)
        
        # Şekil verisini kaydet
        self.shapes_data.append({
            "type": shape_type,
            "name": shape_name,
            "width": width,
            "height": height,
            "color": color
        })
        
        # Text area'ya ekle
        self.text_area.window_create(tk.INSERT, window=shape_canvas, align=tk.CENTER)
        self.text_area.insert(tk.INSERT, " ")
        
        self.modified = True
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=f"'{shape_name}' eklendi")
        
        # Galeriyi kapat
        try:
            gallery_window.destroy()
        except:
            pass
    
    def _draw_shape_on_canvas(self, canvas, shape_type, cx, cy, w, h, color):
        """Canvas üzerine şekil çiz (Gerçek boyutlu çizim)"""
        try:
            import math
            
            if shape_type == "rect":
                canvas.create_rectangle(10, 10, w+10, h+10, outline=color, width=2)
            elif shape_type == "square":
                size = min(w, h)
                canvas.create_rectangle(10, 10, size+10, size+10, outline=color, width=2)
            elif shape_type == "oval":
                canvas.create_oval(10, 10, w+10, h+10, outline=color, width=2)
            elif shape_type == "circle":
                size = min(w, h)
                canvas.create_oval(10, 10, size+10, size+10, outline=color, width=2)
            elif shape_type == "triangle":
                canvas.create_polygon(cx, 10, 10, h+10, w+10, h+10,
                                    outline=color, fill="", width=2)
            elif shape_type == "diamond":
                canvas.create_polygon(cx, 10, w+10, cy, cx, h+10, 10, cy,
                                    outline=color, fill="", width=2)
            elif shape_type in ["arrow_right", "arrow_left", "arrow_up", "arrow_down"]:
                if shape_type == "arrow_right":
                    canvas.create_line(10, cy, w+10, cy, fill=color, width=4, arrow=tk.LAST, arrowshape=(20,25,10))
                elif shape_type == "arrow_left":
                    canvas.create_line(w+10, cy, 10, cy, fill=color, width=4, arrow=tk.LAST, arrowshape=(20,25,10))
                elif shape_type == "arrow_up":
                    canvas.create_line(cx, h+10, cx, 10, fill=color, width=4, arrow=tk.LAST, arrowshape=(20,25,10))
                elif shape_type == "arrow_down":
                    canvas.create_line(cx, 10, cx, h+10, fill=color, width=4, arrow=tk.LAST, arrowshape=(20,25,10))
            elif shape_type == "star_5":
                points = []
                for i in range(10):
                    angle = math.pi / 2 + (2 * math.pi * i / 10)
                    r = min(w, h) // 2 if i % 2 == 0 else min(w, h) // 4
                    x = cx + r * math.cos(angle)
                    y = cy - r * math.sin(angle)
                    points.extend([x, y])
                canvas.create_polygon(points, outline=color, fill="", width=2)
            elif shape_type == "pentagon":
                points = []
                for i in range(5):
                    angle = math.pi / 2 + (2 * math.pi * i / 5)
                    x = cx + min(w, h) // 2 * math.cos(angle)
                    y = cy - min(w, h) // 2 * math.sin(angle)
                    points.extend([x, y])
                canvas.create_polygon(points, outline=color, fill="", width=2)
            elif shape_type == "hexagon":
                points = []
                for i in range(6):
                    angle = 2 * math.pi * i / 6
                    x = cx + min(w, h) // 2 * math.cos(angle)
                    y = cy + min(w, h) // 2 * math.sin(angle)
                    points.extend([x, y])
                canvas.create_polygon(points, outline=color, fill="", width=2)
            elif shape_type == "process":
                canvas.create_rectangle(10, 10, w+10, h+10, outline=color, width=2)
            elif shape_type == "decision":
                canvas.create_polygon(cx, 10, w+10, cy, cx, h+10, 10, cy,
                                    outline=color, fill="", width=2)
            else:
                canvas.create_rectangle(10, 10, w+10, h+10, outline=color, width=2)
        except Exception as e:
            print(f"Şekil çizim hatası: {e}")

    # === ESKİ ŞEKİL METODLARI (Geriye uyumluluk) ===
    def insert_shape(self, shape_type):
        """Eski şekil ekleme (geriye uyumluluk için)"""
        # Yeni galeriyi aç
        self.open_shape_gallery()

    def insert_text(self, text):
        self.text_area.insert(tk.INSERT, text)
        self.text_area.focus_set()

    def set_alignment(self, align):
        tag_name = f"align_{align}"
        self.text_area.tag_configure(tag_name, justify=align)
        
        try:
            self.text_area.tag_add(tag_name, "sel.first", "sel.last")
        except tk.TclError:
            self.text_area.tag_add(tag_name, "insert linestart", "insert lineend")

    # =========================================================================
    # PDF DIŞA AKTARMA (ReportLab Kütüphanesi ile)
    # =========================================================================
    def export_to_pdf(self):
        """PDF'e aktar - Çizimlerle birlikte"""
        if not PDF_AVAILABLE:
            messagebox.showerror("Hata", 
                               "PDF özelliği için 'reportlab' ve 'Pillow' gerekli!\n\n"
                               "Kurmak için:\npip install reportlab Pillow")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("Tüm dosyalar", "*.*")],
            title="PDF Olarak Kaydet",
            initialfile=f"{self.page_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
        if not filename:
            return
        
        try:
            # Çizim canvas'ını yakala
            drawing_image = None
            if hasattr(self, 'drawing_canvas'):
                try:
                    drawing_image = self._capture_drawing_canvas()
                except Exception as e:
                    print(f"Çizim yakalama hatası: {e}")
            
            self._create_pdf(filename, drawing_image)
            messagebox.showinfo("Başarılı", f"PDF oluşturuldu:\n{filename}")
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text="PDF kaydedildi ✓")
        except Exception as e:
            messagebox.showerror("Hata", f"PDF oluşturulurken hata:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def _capture_drawing_canvas(self):
        """Çizim canvas'ını PIL Image olarak yakala"""
        try:
            items = self.drawing_canvas.find_withtag("drawing")
            if not items:
                return None
            
            canvas_width = self.drawing_canvas.winfo_width()
            canvas_height = self.drawing_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                return None
            
            from PIL import Image, ImageDraw, ImageFont
            image = Image.new('RGB', (canvas_width, canvas_height), 'white')
            draw = ImageDraw.Draw(image)
            
            for item in items:
                item_type = self.drawing_canvas.type(item)
                coords = self.drawing_canvas.coords(item)
                
                try:
                    if item_type == "line":
                        color = self.drawing_canvas.itemcget(item, "fill")
                        width = int(float(self.drawing_canvas.itemcget(item, "width")))
                        if len(coords) >= 4:
                            for i in range(0, len(coords)-2, 2):
                                draw.line([coords[i], coords[i+1], coords[i+2], coords[i+3]],
                                        fill=color, width=width)
                    
                    elif item_type == "rectangle":
                        color = self.drawing_canvas.itemcget(item, "outline")
                        width = int(float(self.drawing_canvas.itemcget(item, "width")))
                        if len(coords) >= 4:
                            draw.rectangle(coords, outline=color, width=width)
                    
                    elif item_type == "oval":
                        color = self.drawing_canvas.itemcget(item, "outline")
                        width = int(float(self.drawing_canvas.itemcget(item, "width")))
                        if len(coords) >= 4:
                            draw.ellipse(coords, outline=color, width=width)
                    
                    elif item_type == "polygon":
                        color = self.drawing_canvas.itemcget(item, "outline")
                        if len(coords) >= 6:
                            draw.polygon(coords, outline=color)
                    
                    elif item_type == "text":
                        text = self.drawing_canvas.itemcget(item, "text")
                        color = self.drawing_canvas.itemcget(item, "fill")
                        if len(coords) >= 2:
                            try:
                                fnt = ImageFont.truetype("arial.ttf", 14)
                            except:
                                fnt = ImageFont.load_default()
                            draw.text((coords[0], coords[1]), text, fill=color, font=fnt)
                
                except Exception as e:
                    print(f"Öğe çizim hatası ({item_type}): {e}")
                    continue
            
            return image
            
        except Exception as e:
            print(f"Canvas yakalama hatası: {e}")
            import traceback
            traceback.print_exc()
            return None


    def _create_pdf(self, filename, drawing_image=None):
        doc = SimpleDocTemplate(filename, pagesize=A4,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Başlık
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor(THEME["accent"]),
            spaceAfter=12,
            alignment=1
        )
        story.append(Paragraph(self.page_id, title_style))
        story.append(Spacer(1, 12))
        
        # Metin içeriği
        content = self.text_area.get("1.0", tk.END).strip()
        if content:
            for para in content.split('\n'):
                if para.strip():
                    para = para.replace('→', '&rarr;').replace('←', '&larr;')
                    para = para.replace('↑', '&uarr;').replace('↓', '&darr;')
                    para = para.replace('⇒', '&rArr;').replace('⇐', '&lArr;')
                    
                    try:
                        story.append(Paragraph(para, styles['Normal']))
                    except:
                        story.append(Paragraph(para.encode('ascii', 'ignore').decode(), styles['Normal']))
                else:
                    story.append(Spacer(1, 6))
        
        # Tablolar - Gelişmiş stil
        if self.tables_data:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Tablolar", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            for idx, table_data in enumerate(self.tables_data):
                try:
                    table_content = []
                    cells = table_data.get("cells", [])
                    
                    for row in cells:
                        row_data = []
                        for cell in row:
                            try:
                                cell_text = cell.get() if hasattr(cell, 'get') else str(cell)
                                row_data.append(cell_text if cell_text else " ")
                            except:
                                row_data.append(" ")
                        if row_data:
                            table_content.append(row_data)
                    
                    if table_content:
                        t = Table(table_content)
                        t.setStyle(TableStyle([
                            # Başlık satırı
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 11),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('TOPPADDING', (0, 0), (-1, 0), 12),
                            # Veri satırları
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 10),
                            ('GRID', (0, 0), (-1, -1), 1.5, colors.black),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                        ]))
                        story.append(t)
                        story.append(Spacer(1, 12))
                except Exception as e:
                    print(f"Tablo PDF ekleme hatası: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Şekiller - Vektörel çizim
        if self.shapes_data:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Şekiller ve Diyagramlar", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            for shape_data in self.shapes_data:
                try:
                    shape_type = shape_data.get("type", "rect")
                    w = shape_data.get("width", 150)
                    h = shape_data.get("height", 100)
                    color = colors.HexColor(shape_data.get("color", "#0078d7"))
                    
                    # Drawing oluştur
                    d = Drawing(w, h)
                    
                    cx = w / 2
                    cy = h / 2
                    
                    if shape_type == "rect":
                        d.add(Rect(10, 10, w - 20, h - 20, strokeColor=color, strokeWidth=2, fillColor=None))
                    elif shape_type == "square":
                        size = min(w, h) - 20
                        d.add(Rect(10, 10, size, size, strokeColor=color, strokeWidth=2, fillColor=None))
                    elif shape_type == "oval":
                        d.add(Ellipse(cx, cy, (w - 20)/2, (h - 20)/2, strokeColor=color, strokeWidth=2, fillColor=None))
                    elif shape_type == "circle":
                        size = min(w, h) - 20
                        d.add(Ellipse(cx, cy, size/2, size/2, strokeColor=color, strokeWidth=2, fillColor=None))
                    elif shape_type == "triangle":
                        points = [cx, 10, 10, h-10, w-10, h-10]
                        d.add(Polygon(points, strokeColor=color, strokeWidth=2, fillColor=None))
                    elif shape_type == "diamond":
                        points = [cx, 10, w-10, cy, cx, h-10, 10, cy]
                        d.add(Polygon(points, strokeColor=color, strokeWidth=2, fillColor=None))
                    elif shape_type == "arrow_right":
                        d.add(Line(10, cy, w-10, cy, strokeColor=color, strokeWidth=4))
                    # ... Diğer PDF çizimleri ...
                    
                    story.append(d)
                    story.append(Spacer(1, 6))
                except Exception as e:
                    print(f"Şekil PDF ekleme hatası: {e}")
        
        # Görseller
        if self.images_data:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Görseller", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            for img_data in self.images_data:
                try:
                    image_bytes = base64.b64decode(img_data["base64"])
                    img_buffer = io.BytesIO(image_bytes)
                    rl_img = RLImage(img_buffer, width=img_data["width"], 
                                    height=img_data["height"])
                    story.append(rl_img)
                    story.append(Spacer(1, 12))
                except Exception as e:
                    print(f"Görsel PDF'e eklenemedi: {e}")
        
        
        # ÇİZİMLER - YENİ BÖLÜM!
        if drawing_image is not None:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Çizimler", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            try:
                img_buffer = io.BytesIO()
                drawing_image.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                page_width = A4[0] - 144
                page_height = A4[1] - 144
                
                img_width = drawing_image.width
                img_height = drawing_image.height
                
                scale = min(page_width / img_width, page_height / img_height, 1.0)
                new_width = img_width * scale
                new_height = img_height * scale
                
                rl_img = RLImage(img_buffer, width=new_width, height=new_height)
                story.append(rl_img)
                story.append(Spacer(1, 12))
                
            except Exception as e:
                print(f"Çizim PDF'e eklenemedi: {e}")
                import traceback
                traceback.print_exc()
        
        doc.build(story)

    def apply_font(self, event=None):
        weight = "bold" if self.bold_var.get() else "normal"
        slant = "italic" if self.italic_var.get() else "roman"
        
        try:
            size = self.font_size.get()
            if not isinstance(size, int):
                size = 11
        except:
            size = 11
            self.font_size.set(11)
        
        try:
            font_tuple = (self.font_family.get(), size, weight, slant)
            self.text_area.configure(font=font_tuple)
        except Exception as e:
            print(f"Font hatası: {e}")

    def on_modified(self, event=None):
        if self.text_area.edit_modified():
            self.modified = True
            self.text_area.edit_modified(False)

    def on_key_release(self, event=None):
        """Tuş bırakıldığında - Debounced"""
        if self._after_id:
            self.after_cancel(self._after_id)
        # 500ms bekle, ardından güncelle (performans için)
        self._after_id = self.after(500, self.update_status_lazy)

    def update_status_lazy(self):
        """Durum çubuğunu güncelle - Optimize edilmiş"""
        if not hasattr(self, 'status_bar'):
            return
        
        try:
            content = self.text_area.get("1.0", tk.END)
            words = len(content.split())
            chars = len(content) - 1
            
            status_parts = [f"Karakter: {chars}", f"Kelime: {words}"]
            
            if self.images_data:
                status_parts.append(f"Görsel: {len(self.images_data)}")
            if self.tables_data:
                status_parts.append(f"Tablo: {len(self.tables_data)}")
            if self.shapes_data:
                status_parts.append(f"Şekil: {len(self.shapes_data)}")
            
            status = " | ".join(status_parts)
            self.status_bar.config(text=status)
        except Exception as e:
            print(f"Durum güncelleme hatası: {e}")

    def save_note(self):
        """Notu kaydet - Optimize edilmiş ve güvenli"""
        try:
            if self.callback:
                # Tablo içerikleri - Güvenli
                table_contents = []
                try:
                    for table_data in self.tables_data:
                        table_content = []
                        cells = table_data.get("cells", [])
                        for row in cells:
                            row_data = []
                            for cell in row:
                                try:
                                    cell_value = cell.get() if hasattr(cell, 'get') else str(cell)
                                    row_data.append(cell_value)
                                except:
                                    row_data.append("")
                            if row_data:
                                table_content.append(row_data)
                        if table_content:
                            table_contents.append(table_content)
                except Exception as e:
                    print(f"Tablo kaydetme hatası: {e}")
                    table_contents = []
                
                # Şekil verileri - JSON serializable yap
                shapes_safe = []
                try:
                    for shape in self.shapes_data:
                        shape_safe = {
                            "type": str(shape.get("type", "rect")),
                            "name": str(shape.get("name", "Şekil")),
                            "width": int(shape.get("width", 150)),
                            "height": int(shape.get("height", 100)),
                            "color": str(shape.get("color", "#0078d7"))
                        }
                        shapes_safe.append(shape_safe)
                except Exception as e:
                    print(f"Şekil kaydetme hatası: {e}")
                    shapes_safe = []
                
                # Görsel verileri - Güvenli
                images_safe = []
                try:
                    for img in self.images_data:
                        img_safe = {
                            "base64": str(img.get("base64", "")),
                            "width": int(img.get("width", 100)),
                            "height": int(img.get("height", 100))
                        }
                        images_safe.append(img_safe)
                except Exception as e:
                    print(f"Görsel kaydetme hatası: {e}")
                    images_safe = []
                
                # Kaydet
                save_data = {
                    "text": self.text_area.get("1.0", tk.END),
                    "tables": table_contents,
                    "shapes": shapes_safe,
                    "images": images_safe
                }
                
                self.callback(self.page_id, save_data)
            
            self.modified = False
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text="Kaydedildi ✓")
                self.after(2000, lambda: self.update_status_lazy())
                
        except Exception as e:
            print(f"Kaydetme hatası detayı: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Kaydetme Hatası", 
                               f"Not kaydedilirken hata oluştu:\n{str(e)}\n\n"
                               "Lütfen konsol çıktısını kontrol edin.")

    def close_editor(self):
        if self.modified:
            response = messagebox.askyesnocancel("Kaydet", "Değişiklikleri kaydetmek istiyor musunuz?")
            if response:
                self.save_note()
                self.destroy()
            elif response is False:
                self.destroy()
        else:
            self.destroy()

# =============================================================================
# SINIF: ModernGridApp (Ana Pencere)
# =============================================================================
class ModernGridApp:
    """Ana Uygulama - Sayfa Yönetimi"""
    def __init__(self, root):
        self.root = root
        self.root.title("GridFlow")
        self.root.geometry("1200x800")
        self.root.configure(bg=THEME["bg_gradient_top"])
        
        self.pages = {}
        self.current_page_id = 0
        self.open_editors = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Menü çubuğu
        menubar = tk.Frame(self.root, bg=THEME["menu_bg"], height=50)
        menubar.pack(side=tk.TOP, fill=tk.X)
        menubar.pack_propagate(False)
        
        self._create_menu_btn(menubar, "📄 Yeni Sayfa", self.create_new_page)
        self._create_menu_btn(menubar, "💾 Kaydet", self.save_project)
        self._create_menu_btn(menubar, "📂 Aç", self.load_project)
        self._create_menu_btn(menubar, "🗑️ Temizle", self.clear_all)
        
        self.page_label = tk.Label(menubar, text="Sayfa: 0", 
                                   bg=THEME["menu_bg"], fg="white", 
                                   font=("Calibri", 10, "bold"))
        self.page_label.pack(side=tk.RIGHT, padx=20)
        
        # PDF durum
        if PDF_AVAILABLE:
            tk.Label(menubar, text="✓ Tüm Özellikler", bg=THEME["menu_bg"], 
                    fg="#00ff00", font=("Calibri", 9)).pack(side=tk.RIGHT, padx=10)
        
        # Canvas
        container = tk.Frame(self.root, bg=THEME["canvas_bg"])
        container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(container, bg=THEME["canvas_bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Configure>", self.on_resize)
        
        self.root.bind("<Control-n>", lambda e: self.create_new_page())
        self.root.bind("<Control-s>", lambda e: self.save_project())
        
        self.show_welcome()

    def _create_menu_btn(self, parent, text, command):
        btn = tk.Button(parent, text=text, command=command, 
                       bg=THEME["menu_bg"], fg="white", 
                       relief=tk.FLAT, font=("Calibri", 10, "bold"), 
                       padx=15, cursor="hand2",
                       activebackground="#0a2647")
        btn.pack(side=tk.LEFT, padx=2)

    def show_welcome(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1200
        h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 800
        
        self.canvas.create_text(w/2, h/2 - 80, text="📝🎨", 
                              font=("Arial", 64), fill="#666")
        self.canvas.create_text(w/2, h/2, 
                              text="Not Defteri + Direkt Çizim", 
                              font=("Calibri", 24, "bold"), fill="#888")
        self.canvas.create_text(w/2, h/2 + 40, 
                              text="Yaz, çiz, renklendir - hepsi aynı sayfada!", 
                              font=("Calibri", 14), fill="#666")

    def create_new_page(self):
        """Yeni sayfa oluştur"""
        self.current_page_id += 1
        pid = f"Sayfa_{self.current_page_id}"
        self.pages[pid] = {
            "content": {
                "text": "",
                "tables": [],
                "shapes": [],
                "images": []
            },
            "title": pid
        }
        self.redraw_pages()
        self.open_editor(pid)
        self.update_page_count()

    def redraw_pages(self):
        self.canvas.delete("all")
        
        if not self.pages:
            self.show_welcome()
            return
        
        try:
            cw = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1200
            cols = max(1, cw // (PAGE_CONFIG["width"] + PAGE_CONFIG["margin"]))
            
            for idx, (pid, data) in enumerate(self.pages.items()):
                r, c = divmod(idx, cols)
                x = 50 + c * (PAGE_CONFIG["width"] + PAGE_CONFIG["margin"])
                y = 50 + r * (PAGE_CONFIG["height"] + PAGE_CONFIG["margin"])
                
                # Gölge
                self.canvas.create_rectangle(x+3, y+3, x+213, y+300, 
                                            fill="#333", outline="", tags=pid)
                
                # Kart
                self.canvas.create_rectangle(x, y, x+210, y+297, 
                                            fill="white", outline="#ccc", width=2,
                                            tags=(pid, "page"))
                
                # Başlık
                title = data.get("title", pid)
                self.canvas.create_text(x+105, y+20, text=f"📝 {title}", 
                                      font=("Calibri", 11, "bold"), tags=pid)
                
                # Önizleme
                try:
                    content_data = data.get("content", "")
                    preview_text = ""
                    
                    if isinstance(content_data, dict):
                        preview_text = content_data.get("text", "")
                    elif isinstance(content_data, str):
                        preview_text = content_data
                    else:
                        preview_text = str(content_data)
                    
                    preview = preview_text[:80].replace("\n", " ")
                    if len(preview_text) > 80:
                        preview += "..."
                    
                    if not preview.strip():
                        preview = "(Boş sayfa - Çizim yapabilirsiniz!)"
                    
                    self.canvas.create_text(x+10, y+50, text=preview, 
                                          font=("Calibri", 9), fill="#666",
                                          anchor=tk.NW, width=190, tags=pid)
                except Exception as e:
                    print(f"Önizleme hatası: {e}")
                
                # İkonlar
                try:
                    icon_x = x + 15
                    if isinstance(content_data, dict):
                        if content_data.get("images"):
                            self.canvas.create_text(icon_x, y+15, text="📷",
                                                  font=("Arial", 12), tags=pid)
                            icon_x += 20
                        if content_data.get("tables"):
                            self.canvas.create_text(icon_x, y+15, text="▦",
                                                  font=("Arial", 12), tags=pid)
                            icon_x += 20
                        if content_data.get("shapes"):
                            self.canvas.create_text(icon_x, y+15, text="📐",
                                                  font=("Arial", 12), tags=pid)
                except:
                    pass
                
                # Sil butonu
                delete_btn = self.canvas.create_text(x+195, y+280, text="❌",
                                                    font=("Arial", 12),
                                                    tags=(f"delete_{pid}", "delete"),
                                                    state=tk.HIDDEN)
                
                # Events
                self.canvas.tag_bind(pid, "<Button-1>", lambda e, p=pid: self.open_editor(p))
                self.canvas.tag_bind(pid, "<Enter>", lambda e, p=pid: self.on_hover(p, True))
                self.canvas.tag_bind(pid, "<Leave>", lambda e, p=pid: self.on_hover(p, False))
                self.canvas.tag_bind(f"delete_{pid}", "<Button-1>", lambda e, p=pid: self.delete_page(p))
            
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception as e:
            messagebox.showerror("Hata", f"Sayfa çizim hatası: {str(e)}")
            print(f"Sayfa çizim hatası: {e}")
            import traceback
            traceback.print_exc()

    def on_hover(self, pid, enter):
        try:
            items = self.canvas.find_withtag(pid)
            for item in items:
                if self.canvas.type(item) == "rectangle":
                    if enter:
                        self.canvas.itemconfig(item, outline=THEME["accent"], width=3)
                        self.canvas.itemconfig(f"delete_{pid}", state=tk.NORMAL)
                    else:
                        self.canvas.itemconfig(item, outline="#ccc", width=2)
                        self.canvas.itemconfig(f"delete_{pid}", state=tk.HIDDEN)
        except tk.TclError as e:
            print(f"Hover hatası: {e}")

    def open_editor(self, pid):
        """Not editörünü aç"""
        if pid in self.open_editors:
            try:
                self.open_editors[pid].lift()
                return
            except:
                del self.open_editors[pid]
        
        content = self.pages[pid].get("content", "")
        editor = NoteEditor(self.root, pid, content, self.save_callback)
        self.open_editors[pid] = editor
        
        def on_close():
            if pid in self.open_editors:
                del self.open_editors[pid]
        
        editor.protocol("WM_DELETE_WINDOW", lambda: (on_close(), editor.close_editor()))

    def save_callback(self, pid, content):
        """Not kaydetme callback"""
        if pid in self.pages:
            self.pages[pid]["content"] = content
            self.redraw_pages()

    def delete_page(self, pid):
        if messagebox.askyesno("Sil", f"{pid} sayfasını silmek istediğinizden emin misiniz?"):
            if pid in self.pages:
                del self.pages[pid]
            if pid in self.open_editors:
                try:
                    self.open_editors[pid].destroy()
                except:
                    pass
                del self.open_editors[pid]
            
            self.redraw_pages()
            self.update_page_count()

    def save_project(self):
        if not self.pages:
            messagebox.showinfo("Bilgi", "Kaydedilecek sayfa yok.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tüm dosyalar", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        "pages": self.pages,
                        "current_page_id": self.current_page_id
                    }, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Başarılı", "Proje kaydedildi!")
            except Exception as e:
                messagebox.showerror("Hata", f"Kaydetme hatası:\n{str(e)}")

    def load_project(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Tüm dosyalar", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                loaded_pages = data.get("pages", {})
                
                for page_id, page_data in loaded_pages.items():
                    content = page_data.get("content", "")
                    
                    if isinstance(content, str):
                        loaded_pages[page_id]["content"] = {
                            "text": content,
                            "tables": [],
                            "shapes": [],
                            "images": []
                        }
                    elif isinstance(content, dict):
                        if "images" not in content:
                            content["images"] = []
                        
                    else:
                        loaded_pages[page_id]["content"] = {
                            "text": str(content),
                            "tables": [],
                            "shapes": [],
                            "images": []
                        }
                
                self.pages = loaded_pages
                self.current_page_id = data.get("current_page_id", len(loaded_pages))
                
                self.redraw_pages()
                self.update_page_count()
                messagebox.showinfo("Başarılı", "Proje yüklendi!")
            except Exception as e:
                messagebox.showerror("Hata", f"Yükleme hatası:\n{str(e)}")
                import traceback
                traceback.print_exc()

    def clear_all(self):
        if not self.pages:
            messagebox.showinfo("Bilgi", "Zaten boş.")
            return
        
        if messagebox.askyesno("Temizle", "Tüm sayfaları silmek istediğinizden emin misiniz?"):
            self.pages.clear()
            
            for editor in list(self.open_editors.values()):
                try:
                    editor.destroy()
                except:
                    pass
            self.open_editors.clear()
            
            self.current_page_id = 0
            self.redraw_pages()
            self.update_page_count()

    def update_page_count(self):
        self.page_label.config(text=f"Sayfa: {len(self.pages)}")

    def on_resize(self, event):
        self.redraw_pages()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernGridApp(root)
    root.mainloop()
