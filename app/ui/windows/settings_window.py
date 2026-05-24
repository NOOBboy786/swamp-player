from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QLabel, QButtonGroup
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter

from app.ui.widgets import RetroButton
from app.ui.windows.history_window import draw_retro_bevel

class SettingsModal(QDialog):
    def __init__(self, master):
        super().__init__()
        self.master = master
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(300, 200)
        self.setStyleSheet(f"background-color: {self.master.bg_color}; color: {self.master.accent_color}; font-family: Consolas;")
        
        self._init_ui()
        
    def _init_ui(self):
        vbox = QVBoxLayout(self)
        
        lbl_title = QLabel("SETTINGS")
        lbl_title.setStyleSheet(f"font-weight: bold; color: {self.master.accent_color};")
        vbox.addWidget(lbl_title, alignment=Qt.AlignCenter)
        
        # Theme Toggle
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme Mode:"))
        self.rb_dark = QRadioButton("Dark Mode")
        self.rb_white = QRadioButton("White Mode")
        
        if self.master.theme_mode == 'white':
            self.rb_white.setChecked(True)
        else:
            self.rb_dark.setChecked(True)
            
        theme_bg = QButtonGroup(self)
        theme_bg.addButton(self.rb_dark)
        theme_bg.addButton(self.rb_white)
        
        self.rb_dark.toggled.connect(self._on_theme_changed)
        
        theme_layout.addWidget(self.rb_dark)
        theme_layout.addWidget(self.rb_white)
        vbox.addLayout(theme_layout)
        
        # Accent Color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Accent Color:"))
        
        colors = [
            ('#00FF00', 'Green'),
            ('#FFB000', 'Amber'),
            ('#00FFFF', 'Cyan'),
            ('#FF00FF', 'Purple'),
            ('#FFFFFF', 'White')
        ]
        
        for hex_code, name in colors:
            btn = RetroButton("", self)
            btn.setFixedSize(20, 20)
            btn.setStyleSheet(f"background-color: {hex_code}; border: 1px solid #555;")
            btn.clicked.connect(lambda checked=False, c=hex_code: self._on_color_changed(c))
            color_layout.addWidget(btn)
            
        vbox.addLayout(color_layout)
        
        # Close
        btn_close = RetroButton("CLOSE", self)
        btn_close.clicked.connect(self.accept)
        vbox.addWidget(btn_close, alignment=Qt.AlignCenter)

    def paintEvent(self, event):
        draw_retro_bevel(QPainter(self), self.rect(), True)
        
    def _on_theme_changed(self):
        mode = 'dark' if self.rb_dark.isChecked() else 'white'
        self.master.db.set_config('theme_mode', mode)
        self.master.apply_theme(mode, self.master.accent_color)
        
    def _on_color_changed(self, color_hex):
        self.master.db.set_config('accent_color', color_hex)
        self.master.apply_theme(self.master.theme_mode, color_hex)
