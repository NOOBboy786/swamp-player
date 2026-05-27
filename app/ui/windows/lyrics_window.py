import requests
import re
import threading
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter

from app.ui.widgets import RetroDisplayLabel, RetroButton
from app.ui.windows.history_window import draw_retro_bevel
from app.ui.snapping import apply_magnetic_snap

class LyricsWindow(QWidget):
    lyrics_fetched_signal = Signal(list)
    lyrics_error_signal = Signal(str)

    def __init__(self, master):
        super().__init__()
        self.master = master
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setFixedSize(350, 400)
        
        self.lbl_title = RetroDisplayLabel(" SYNCED LYRICS", self)
        self.lbl_title.setGeometry(0, 0, 325, 20)
        self.lbl_title.setStyleSheet("background: transparent; color: #888;")
        
        self.btn_close = RetroButton("X", self)
        self.btn_close.setGeometry(330, 2, 20, 16)
        self.btn_close.clicked.connect(self.hide)
        
        self.list_lyrics = QListWidget(self)
        self.list_lyrics.setGeometry(10, 25, 330, 365)
        self.list_lyrics.setStyleSheet("""
            QListWidget {
                background-color: #050505;
                color: #555;
                border: 1px solid #333;
                outline: 0;
            }
            QListWidget::item {
                padding: 5px;
            }
        """)
        font = QFont("Consolas", 10)
        self.list_lyrics.setFont(font)
        self.list_lyrics.setWordWrap(True)
        self.list_lyrics.setSelectionMode(QAbstractItemView.NoSelection)
        
        self.drag_pos = None
        self.lyrics_data = [] # List of tuples: (time_sec, text, QListWidgetItem)
        self.current_track_id = None
        
        self.master.update_lyrics_time_signal.connect(self.update_lyrics_sync)
        self.lyrics_fetched_signal.connect(self._render_lyrics)
        self.lyrics_error_signal.connect(self._set_lyrics_error)

    def paintEvent(self, event):
        draw_retro_bevel(QPainter(self), self.rect(), True)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            apply_magnetic_snap(self, self.master)
            event.accept()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self.master, 'trigger_save_layout'): self.master.trigger_save_layout()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self.master, 'trigger_save_layout'): self.master.trigger_save_layout()
        self._check_for_new_track()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self.master, 'trigger_save_layout'): self.master.trigger_save_layout()

    def _check_for_new_track(self):
        if not self.isVisible(): return
        track = getattr(self.master, 'current_track', None)
        if not track: return
        
        track_id = track.get('id')
        if track_id == self.current_track_id: return
        self.current_track_id = track_id
        
        self.list_lyrics.clear()
        self.lyrics_data = []
        item = QListWidgetItem("Fetching lyrics from LRCLIB...")
        item.setTextAlignment(Qt.AlignCenter)
        self.list_lyrics.addItem(item)
        
        threading.Thread(target=self._fetch_lyrics_worker, args=(track,), daemon=True).start()

    def _fetch_lyrics_worker(self, track):
        try:
            params = {
                'track_name': track.get('title', ''),
                'artist_name': track.get('artist', '')
            }
            if track.get('album') and track.get('album') != 'Unknown Album':
                params['album_name'] = track.get('album')
                
            response = requests.get("https://lrclib.net/api/get", params=params, timeout=5)
            if response.status_code != 200:
                self.lyrics_error_signal.emit("Lyrics not found.")
                return
                
            data = response.json()
            synced = data.get('syncedLyrics')
            if not synced:
                self.lyrics_error_signal.emit("No synced lyrics available.")
                return
                
            # Parse LRC
            parsed = []
            for line in synced.split('\n'):
                m = re.match(r'\[(\d{2}):(\d{2}\.\d{2,3})\](.*)', line)
                if m:
                    time_sec = int(m.group(1)) * 60 + float(m.group(2))
                    text = m.group(3).strip()
                    if text: # Skip empty lines
                        parsed.append((time_sec, text))
                        
            if not parsed:
                self.lyrics_error_signal.emit("Failed to parse synced lyrics.")
                return
                
            self.lyrics_fetched_signal.emit(parsed)
            
        except Exception as e:
            print(f"LRCLIB Error: {e}")
            self.lyrics_error_signal.emit("Network error fetching lyrics.")

    def _set_lyrics_error(self, msg):
        self.list_lyrics.clear()
        self.lyrics_data = []
        item = QListWidgetItem(msg)
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QColor(150, 50, 50))
        self.list_lyrics.addItem(item)

    def _render_lyrics(self, parsed_lines):
        self.list_lyrics.clear()
        self.lyrics_data = []
        for time_sec, text in parsed_lines:
            item = QListWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(85, 85, 85)) # Dim initially
            self.list_lyrics.addItem(item)
            self.lyrics_data.append((time_sec, text, item))

    def update_lyrics_sync(self, current_time_sec):
        if not self.isVisible() or not self.lyrics_data: return
        
        # Find active line
        active_idx = -1
        for i, (time_sec, _, _) in enumerate(self.lyrics_data):
            if current_time_sec >= time_sec:
                active_idx = i
            else:
                break
                
        if active_idx != -1:
            for i, (_, _, item) in enumerate(self.lyrics_data):
                if i == active_idx:
                    item.setForeground(QColor(0, 255, 0)) # Highlight green
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    self.list_lyrics.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                else:
                    item.setForeground(QColor(85, 85, 85))
                    font = item.font()
                    font.setBold(False)
                    item.setFont(font)

