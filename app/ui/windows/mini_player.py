import os
from PySide6.QtWidgets import QWidget, QApplication, QLabel
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor

from app.ui.widgets import RetroButton, RetroDisplayLabel
from app.ui.windows.history_window import draw_retro_bevel

class MiniPlayerWindow(QWidget):
    def __init__(self, master):
        super().__init__()
        self.master = master
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setFixedSize(200, 60)
        
        self.lbl_title = RetroDisplayLabel(" SWAMP MINI", self)
        self.lbl_title.setGeometry(0, 0, 200, 20)
        self.lbl_title.setStyleSheet("background: transparent; color: #888;")
        
        self.lbl_track = RetroDisplayLabel("READY", self)
        self.lbl_track.setGeometry(10, 25, 180, 20)
        self.lbl_track.setStyleSheet("background: transparent; color: #0f0; font-size: 10px;")
        
        # Playback Controls
        self.btn_prev = RetroButton("<<", self)
        self.btn_prev.setGeometry(45, 45, 30, 15)
        self.btn_prev.clicked.connect(self.master._play_prev)
        
        self.btn_play = RetroButton(">", self)
        self.btn_play.setGeometry(85, 45, 30, 15)
        self.btn_play.clicked.connect(self.master._play_pause_toggle)
        
        self.btn_next = RetroButton(">>", self)
        self.btn_next.setGeometry(125, 45, 30, 15)
        self.btn_next.clicked.connect(self.master._play_next)
        
        self.master.update_display_signal.connect(self._update_track_title)

    def _update_track_title(self, text):
        # We only want to show the track title when playing, not the state updates
        if text.startswith("PLAYING:") or "..." not in text:
            # We can just extract the current track from master directly
            if getattr(self.master, 'current_track', None):
                title = self.master.current_track.get('title', 'Unknown')
                artist = self.master.current_track.get('artist', 'Unknown')
                self.lbl_track.setText(f"{artist} - {title}")
            else:
                self.lbl_track.setText(text)

    def paintEvent(self, event):
        draw_retro_bevel(QPainter(self), self.rect(), True)
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.hide()
            self.master.showNormal()
            self.master.raise_()
            self.master.activateWindow()

    def show_and_snap(self):
        screen = QApplication.primaryScreen().availableGeometry()
        # Bottom Right snap
        x = screen.width() - self.width()
        y = screen.height() - self.height()
        self.move(x, y)
        self.show()
