import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QFrame, 
                             QToolButton, QComboBox, QScrollArea, QTextEdit, 
                             QStatusBar, QFileDialog, QAction, QColorDialog, QMessageBox)
from PyQt5.QtCore import Qt, QSize, QFile, QTextStream
from PyQt5.QtGui import QFont, QIcon, QTextCharFormat, QColor, QTextCursor, QPageSize, QTextDocument

class FunctionalWord(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Word Klonu (Fonksiyonel MVP)")
        self.setGeometry(100, 100, 1200, 850)
        
        # --- STİL TANIMLARI (Dark Mode) ---
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { color: white; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
            QTabWidget::pane { border: 0; background-color: #2b2b2b; }
            QTabBar::tab { background: #2b2b2b; color: #d0d0d0; padding: 8px 15px; border: none; }
            QTabBar::tab:selected { background: #444444; font-weight: bold; border-bottom: 2px solid #2b579a; }
            QToolButton { background-color: transparent; border: none; padding: 5px; }
            QToolButton:hover { background-color: #3e3e3e; border-radius: 3px; }
            QToolButton:checked { background-color: #505050; }
            QComboBox { background-color: #333; border: 1px solid #555; padding: 2px; }
            QTextEdit { selection-background-color: #0078d7; }
        """)

        self.current_font_size = 11
        self.current_font_family = "Calibri"

        # Arayüz Kurulumu
        self.init_ui()
        
    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Şerit (Ribbon)
        self.init_ribbon()
        
        # 2. Editör Alanı
        self.init_editor()
        
        # 3. Durum Çubuğu
        self.init_statusbar()

    def init_ribbon(self):
        self.tabs = QTabWidget()
        self.tabs.setFixedHeight(130)
        
        # Sekmeler
        self.tab_home = QWidget()
        self.tab_file = QWidget()
        
        self.tabs.addTab(self.tab_file, "Dosya")
        self.tabs.addTab(self.tab_home, "Giriş")
        self.tabs.addTab(QWidget(), "Ekle") # Boş görsel sekmeler
        self.tabs.addTab(QWidget(), "Tasarım")
        
        self.setup_file_tab()
        self.setup_home_tab()
        
        self.tabs.setCurrentIndex(1) # Başlangıçta "Giriş" sekmesi açık olsun
        self.main_layout.addWidget(self.tabs)

    def setup_file_tab(self):
        layout = QHBoxLayout(self.tab_file)
        layout.setAlignment(Qt.AlignLeft)
        
        # Kaydet Butonu
        btn_save = self.create_action_btn("Kaydet", self.save_file)
        btn_open = self.create_action_btn("Aç", self.open_file)
        btn_pdf = self.create_action_btn("PDF Yap", self.export_pdf)
        
        layout.addWidget(btn_save)
        layout.addWidget(btn_open)
        layout.addWidget(btn_pdf)

    def setup_home_tab(self):
        layout = QHBoxLayout(self.tab_home)
        layout.setAlignment(Qt.AlignLeft)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)

        # -- GRUP: YAZI TİPİ --
        font_group = QFrame()
        font_layout = QVBoxLayout(font_group)
        
        # Üst Satır: Font Seçimi ve Boyut
        font_top = QHBoxLayout()
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Calibri", "Arial", "Times New Roman", "Segoe UI", "Verdana"])
        self.font_combo.currentTextChanged.connect(self.change_font_family)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems([str(s) for s in range(8, 73, 2)])
        self.size_combo.setCurrentText("11")
        self.size_combo.currentTextChanged.connect(self.change_font_size)
        
        font_top.addWidget(self.font_combo)
        font_top.addWidget(self.size_combo)
        
        # Alt Satır: B, I, U, Renk
        font_bot = QHBoxLayout()
        
        self.btn_bold = self.create_toggle_btn("K", self.toggle_bold, bold=True)
        self.btn_italic = self.create_toggle_btn("T", self.toggle_italic, italic=True)
        self.btn_underline = self.create_toggle_btn("A", self.toggle_underline, underline=True)
        
        btn_color = QToolButton()
        btn_color.setText("Renk")
        btn_color.clicked.connect(self.change_color)
        btn_color.setStyleSheet("color: #ff5555; font-weight: bold;")
        
        font_bot.addWidget(self.btn_bold)
        font_bot.addWidget(self.btn_italic)
        font_bot.addWidget(self.btn_underline)
        font_bot.addWidget(btn_color)
        
        font_layout.addLayout(font_top)
        font_layout.addLayout(font_bot)
        layout.addWidget(font_group)
        
        # -- GRUP: PARAGRAF --
        para_group = QFrame()
        para_layout = QHBoxLayout(para_group)
        
        btn_left = self.create_action_btn("Sol", lambda: self.editor.setAlignment(Qt.AlignLeft))
        btn_center = self.create_action_btn("Orta", lambda: self.editor.setAlignment(Qt.AlignCenter))
        btn_right = self.create_action_btn("Sağ", lambda: self.editor.setAlignment(Qt.AlignRight))
        
        para_layout.addWidget(btn_left)
        para_layout.addWidget(btn_center)
        para_layout.addWidget(btn_right)
        
        layout.addWidget(para_group)
        layout.addStretch()

    def init_editor(self):
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet("background-color: #121212; border: none;")
        self.scroll.setWidgetResizable(True)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignHCenter)
        content_layout.setContentsMargins(0, 20, 0, 20)
        
        # Kağıt Görünümü
        self.editor = QTextEdit()
        self.editor.setFixedSize(816, 1056) # A4 Piksel (96 DPI)
        self.editor.setStyleSheet("""
            background-color: white; 
            color: black; 
            border: 1px solid #ccc;
            padding: 50px;
            font-family: 'Calibri';
            font-size: 11pt;
        """)
        
        # Editör değiştiğinde UI'ı güncelle (İmleç takibi)
        self.editor.cursorPositionChanged.connect(self.update_format_ui)
        
        content_layout.addWidget(self.editor)
        self.scroll.setWidget(content)
        self.main_layout.addWidget(self.scroll)

    def init_statusbar(self):
        self.status = QStatusBar()
        self.status.setStyleSheet("background-color: #1e1e1e; color: #ccc; border-top: 1px solid #333;")
        self.setStatusBar(self.status)

    # --- YARDIMCI METODLAR ---
    def create_action_btn(self, text, func):
        btn = QToolButton()
        btn.setText(text)
        btn.clicked.connect(func)
        return btn

    def create_toggle_btn(self, text, func, bold=False, italic=False, underline=False):
        btn = QToolButton()
        btn.setText(text)
        btn.setCheckable(True)
        btn.clicked.connect(func)
        
        font = QFont()
        font.setBold(bold)
        font.setItalic(italic)
        font.setUnderline(underline)
        btn.setFont(font)
        return btn

    # --- FONKSİYONEL MANTIK (LOGIC LAYER) ---
    
    def toggle_bold(self):
        if not self.editor.hasFocus(): self.editor.setFocus()
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if self.btn_bold.isChecked() else QFont.Normal)
        self.editor.textCursor().mergeCharFormat(fmt)

    def toggle_italic(self):
        if not self.editor.hasFocus(): self.editor.setFocus()
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.btn_italic.isChecked())
        self.editor.textCursor().mergeCharFormat(fmt)

    def toggle_underline(self):
        if not self.editor.hasFocus(): self.editor.setFocus()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.btn_underline.isChecked())
        self.editor.textCursor().mergeCharFormat(fmt)

    def change_font_family(self, font_name):
        self.editor.setFontFamily(font_name)
        self.editor.setFocus()

    def change_font_size(self, size):
        self.editor.setFontPointSize(float(size))
        self.editor.setFocus()

    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.editor.setTextColor(color)

    def update_format_ui(self):
        # İmleç hareket ettikçe ribbon'daki butonları güncelle
        # Örneğin kalın bir yazıya tıklarsan "K" butonu yansın.
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        
        self.btn_bold.setChecked(fmt.fontWeight() == QFont.Bold)
        self.btn_italic.setChecked(fmt.fontItalic())
        self.btn_underline.setChecked(fmt.fontUnderline())

    # --- DOSYA İŞLEMLERİ ---
    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Kaydet", "", "HTML Dosyası (*.html);;Metin Dosyası (*.txt)")
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                if filename.endswith('.html'):
                    f.write(self.editor.toHtml())
                else:
                    f.write(self.editor.toPlainText())
            self.status.showMessage(f"Kaydedildi: {filename}")

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Aç", "", "HTML Dosyası (*.html);;Metin Dosyası (*.txt)")
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                if filename.endswith('.html'):
                    self.editor.setHtml(f.read())
                else:
                    self.editor.setPlainText(f.read())

    def export_pdf(self):
        filename, _ = QFileDialog.getSaveFileName(self, "PDF Olarak Kaydet", "", "PDF Dosyası (*.pdf)")
        if filename:
            printer = QTextDocument(self.editor.toHtml())
            # Burada PDF yazdırma işlemi için QPrinter gerekebilir ama 
            # basitlik adına sadece mesaj veriyorum, PyQt5.QtPrintSupport gerekir.
            QMessageBox.information(self, "Bilgi", "PDF Dışa Aktarma modülü için 'QtPrintSupport' eklenmelidir.\nŞimdilik HTML kaydedebilirsiniz.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FunctionalWord()
    window.show()
    sys.exit(app.exec_())