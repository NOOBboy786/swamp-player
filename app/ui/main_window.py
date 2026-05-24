import os
import threading
import requests
from PySide6.QtWidgets import QWidget, QLabel, QDialog
from PySide6.QtGui import QPainter, QMouseEvent, QPixmap, QImage, QColor, QIcon
from PySide6.QtCore import Qt, QPoint, Signal

from app.ui.widgets import RetroButton, RetroDisplayLabel, RetroSlider
from app.backend.mpv_controller import MPVController
from app.backend.yt_streamer import YouTubeStreamer
from app.backend.itunes_api import iTunesAPI
from app.database.db import Database
from app.backend.mpv_downloader import ensure_mpv_installed
from app.backend.smtc import SMTCController

from app.ui.windows.history_window import HistoryWindow, draw_retro_bevel
from app.ui.windows.search_queue_window import SearchQueueWindow
from app.ui.windows.playlist_contents_window import PlaylistAndContentsWindow

from app.ui.snapping import apply_magnetic_snap
from app.ui.widgets import RetroMessageBox

class CavemanPlayer(QWidget):
    update_display_signal = Signal(str)
    update_art_signal = Signal(bytes)
    autoplay_track_signal = Signal(dict)
    
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        
        ensure_mpv_installed(self.base_dir)
        
        from app.backend.thumbnails import ThumbnailManager
        self.thumb_mgr = ThumbnailManager.get_instance(self.base_dir)
        
        self.mpv = MPVController(self.base_dir)
        self.yt = YouTubeStreamer()
        self.itunes = iTunesAPI()
        self.db = Database(self.base_dir)
        
        self.search_results = []
        self.queue = []
        self.current_queue_idx = -1
        self.current_track = None
        self.is_autoplay_mode = False
        self.repeat_mode = self.db.get_config('repeat_mode', 0)
        
        try:
            self.smtc = SMTCController()
            self.smtc.signals.play_pause.connect(self._play_pause_toggle)
            self.smtc.signals.next_track.connect(self._play_next)
            self.smtc.signals.prev_track.connect(self._play_prev)
        except Exception as e:
            print(f"SMTC Init failed: {e}")
            self.smtc = None
        
        self.theme_mode = self.db.get_config('theme_mode', 'dark')
        self.accent_color = self.db.get_config('accent_color', '#00FF00')
        self.bg_color = '#050505' if self.theme_mode == 'dark' else '#DDDDDD'
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(350, 150)
        
        import sys
        icon_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else self.base_dir
        self.setWindowIcon(QIcon(os.path.join(icon_dir, 'icon.ico')))
        
        self.drag_pos = QPoint()
        
        self.update_display_signal.connect(lambda txt: self.lbl_display.setText(txt))
        self.update_art_signal.connect(self._set_artwork)
        self.autoplay_track_signal.connect(self._on_autoplay_track)
        
        self.mpv.signals.time_pos_changed.connect(self._update_time, Qt.QueuedConnection)
        self.mpv.signals.duration_changed.connect(self._update_duration, Qt.QueuedConnection)
        self.mpv.signals.eof_reached.connect(self._on_eof, Qt.QueuedConnection)
        
        self.apply_theme(self.theme_mode, self.accent_color)
        
        self._init_ui()
        
        from PySide6.QtCore import QTimer
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_window_positions)
        
        # Instantiate secondary windows
        self.search_queue_window = SearchQueueWindow(self)
        self.playlist_contents_window = PlaylistAndContentsWindow(self)
        self.history_window = HistoryWindow(self)
        
        self.queue_window = self.search_queue_window
        
        self._load_window_positions()
        
        self.mpv.start()
        self.mpv.set_volume(50)
        
    def _load_window_positions(self):
        pos_config = self.db.get_config('window_positions')
        if pos_config:
            # Restore Positions
            if 'main' in pos_config: self.move(*pos_config['main'])
            if 'search' in pos_config: self.search_queue_window.move(*pos_config['search'])
            if 'playlist_contents' in pos_config: self.playlist_contents_window.move(*pos_config['playlist_contents'])
            if 'history' in pos_config: self.history_window.move(*pos_config['history'])
            
            # Restore Sizes
            if 'search_size' in pos_config: self.search_queue_window.resize(*pos_config['search_size'])
            if 'playlist_contents_size' in pos_config: self.playlist_contents_window.resize(*pos_config['playlist_contents_size'])
            if 'history_size' in pos_config: self.history_window.resize(*pos_config['history_size'])
            
            # Restore Visibility
            if not pos_config.get('search_visible', True): self.search_queue_window.hide()
            if pos_config.get('playlist_contents_visible', False): self.playlist_contents_window.show()
            if pos_config.get('history_visible', False): self.history_window.show()
        else:
            # Default Layout
            self.search_queue_window.show()
        
    def _init_ui(self):
        self.lbl_title = RetroDisplayLabel(" SWAMP PLAYER", self)
        self.lbl_title.setGeometry(0, 0, 325, 20)
        self.lbl_title.setStyleSheet("background: transparent; color: #888;")
        
        self.btn_close = RetroButton("X", self)
        self.btn_close.setGeometry(330, 2, 20, 16)
        self.btn_close.clicked.connect(self.close)
        
        self.btn_pin = RetroButton("📌", self)
        self.btn_pin.setGeometry(308, 2, 20, 16)
        self.btn_pin.clicked.connect(self._toggle_pin)
        self.is_pinned = False
        
        self.btn_settings = RetroButton("⚙", self)
        self.btn_settings.setGeometry(286, 2, 20, 16)
        self.btn_settings.clicked.connect(self._open_settings)
        
        # Album Art
        self.lbl_art = QLabel(self)
        self.lbl_art.setGeometry(10, 25, 80, 80)
        self.lbl_art.setStyleSheet("background-color: #050505; border: 1px solid #333;")
        self.lbl_art.setScaledContents(True)
        self.lbl_art.setAlignment(Qt.AlignCenter)
        self.lbl_art.setText("NO ART")
        
        self.lbl_display = RetroDisplayLabel("READY", self)
        self.lbl_display.setGeometry(100, 25, 240, 40)
        
        self.lbl_time = RetroDisplayLabel("00:00", self)
        self.lbl_time.setGeometry(100, 70, 60, 20)
        
        self.lbl_duration = RetroDisplayLabel("00:00", self)
        self.lbl_duration.setGeometry(280, 70, 60, 20)
        self.lbl_duration.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.seek_bar = RetroSlider(self)
        self.seek_bar.setGeometry(100, 95, 240, 15)
        self.seek_bar.setMaximum(1)
        self.seek_bar.valueChanged.connect(self._on_seek)
        
        # Playback Controls
        self.btn_prev = RetroButton("<<", self)
        self.btn_prev.setGeometry(10, 115, 25, 25)
        self.btn_prev.clicked.connect(self._play_prev)
        
        self.btn_play = RetroButton(">", self)
        self.btn_play.setGeometry(40, 115, 25, 25)
        self.btn_play.clicked.connect(self._play_pause_toggle)
        
        self.btn_pause = RetroButton("II", self)
        self.btn_pause.setGeometry(70, 115, 25, 25)
        self.btn_pause.clicked.connect(self.mpv.pause)
        
        self.btn_stop = RetroButton("■", self)
        self.btn_stop.setGeometry(100, 115, 25, 25)
        self.btn_stop.clicked.connect(self.mpv.stop)
        
        self.btn_next = RetroButton(">>", self)
        self.btn_next.setGeometry(130, 115, 25, 25)
        self.btn_next.clicked.connect(self._play_next)
        
        # Toggles
        self.btn_repeat = RetroButton("↻", self)
        self.btn_repeat.setGeometry(160, 115, 25, 25)
        self.btn_repeat.clicked.connect(self._toggle_repeat)
        
        self.btn_search = RetroButton("🔍", self)
        self.btn_search.setGeometry(190, 115, 25, 25)
        self.btn_search.clicked.connect(self._toggle_search_window)
        
        self.btn_pl = RetroButton("♫", self)
        self.btn_pl.setGeometry(220, 115, 25, 25)
        self.btn_pl.clicked.connect(self._toggle_playlist_window)
        
        self.btn_hist = RetroButton("🕘", self)
        self.btn_hist.setGeometry(250, 115, 25, 25)
        self.btn_hist.clicked.connect(self._toggle_history_window)
        
        self.vol_slider = RetroSlider(self)
        self.vol_slider.setGeometry(280, 120, 60, 15)
        self.vol_slider.setMaximum(100)
        self.vol_slider.setValue(50)
        self.vol_slider.valueChanged.connect(self.mpv.set_volume)

    def paintEvent(self, event):
        draw_retro_bevel(QPainter(self), self.rect(), True)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            apply_magnetic_snap(self, self)
            event.accept()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'trigger_save_layout'): self.trigger_save_layout()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'trigger_save_layout'): self.trigger_save_layout()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, 'trigger_save_layout'): self.trigger_save_layout()

    def _toggle_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        modes = ["↻", "↻1", "↻A"]
        self.btn_repeat.setText(modes[self.repeat_mode])
        if self.repeat_mode == 0:
            self.btn_repeat.setStyleSheet("color: #0f0;")
        else:
            self.btn_repeat.setStyleSheet("color: #fff; background-color: #004400;")

    def _toggle_search_window(self):
        if self.search_queue_window.isVisible(): self.search_queue_window.hide()
        else: self.search_queue_window.show()

    def _toggle_playlist_window(self):
        if self.playlist_contents_window.isVisible(): self.playlist_contents_window.hide()
        else: self.playlist_contents_window.show()
        
    def _toggle_history_window(self):
        if self.history_window.isVisible(): self.history_window.hide()
        else: self.history_window.show()

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.btn_pin.setStyleSheet("color: #fff; background-color: #004400;")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.btn_pin.setStyleSheet("")
        self.show()

    def _open_settings(self):
        from app.ui.windows.settings_window import SettingsModal
        modal = SettingsModal(self)
        modal.exec()

    def apply_theme(self, mode, accent_color):
        self.theme_mode = mode
        self.accent_color = accent_color
        self.bg_color = '#050505' if mode == 'dark' else '#DDDDDD'
        
        global_style = f"""
            QWidget {{
                background-color: {self.bg_color};
                color: {self.accent_color};
            }}
            QListWidget, QTreeWidget {{
                background-color: {self.bg_color};
                color: {self.accent_color};
                border: 2px solid #333;
            }}
            QListWidget::item:selected, QTreeWidget::item:selected {{
                background-color: #004400;
                color: #fff;
            }}
            QLabel {{
                color: {self.accent_color};
            }}
            QPushButton {{
                background-color: #222;
                color: {self.accent_color};
                border: 1px solid #444;
            }}
            QPushButton:hover {{
                background-color: #333;
            }}
            QLineEdit {{
                background-color: {self.bg_color};
                color: {self.accent_color};
                border: 1px solid #444;
            }}
        """
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(global_style)
        
        # Trigger re-paints for custom drawn widgets
        self.update()
        if hasattr(self, 'search_queue_window'):
            self.search_queue_window.update()
            self.history_window.update()
            self.playlist_contents_window.update()

    def load_and_play(self, track):
        if not getattr(self, 'current_track', None) or self.current_track.get('id') != track.get('id'):
            self.db.add_to_history(track)
            self.history_window.refresh_history()
            
        self.current_track = track
        display_title = f"{track['artist']} - {track['title']}"
        self.update_display_signal.emit(f"LOADING: {display_title[:20]}...")
        self.seek_bar.setValue(0)
        self.lbl_art.setText("...")
        self.lbl_art.setPixmap(QPixmap())
        
        if self.smtc:
            self.smtc.update_metadata(track)
        
        def fetch_and_play():
            query = f"{track['artist']} {track['title']}"
            url = self.yt.get_stream_url(query)
            if url:
                self.mpv.play(url)
                if self.smtc: self.smtc.set_playback_status(True)
                self.update_display_signal.emit(f"PLAYING: {display_title}")
            else:
                self.update_display_signal.emit("ERROR: STREAM NOT FOUND")
                return
                
            art_url = track.get('artwork_url')
            if art_url:
                try:
                    res = requests.get(art_url, timeout=5)
                    if res.status_code == 200:
                        self.update_art_signal.emit(res.content)
                except:
                    pass
        threading.Thread(target=fetch_and_play, daemon=True).start()

    def _play_full_album(self, album_id):
        self.update_display_signal.emit("LOADING ALBUM...")
        
        def fetch_and_play():
            tracks = self.itunes.get_album_tracks(album_id)
            if not tracks:
                self.update_display_signal.emit("ERROR: ALBUM NOT FOUND")
                return
            
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._apply_album_tracks(tracks))
            
        import threading
        threading.Thread(target=fetch_and_play, daemon=True).start()

    def _apply_album_tracks(self, tracks):
        self.queue_window.clear_all_items()
        for track in tracks:
            self.queue.append(track)
        if not self.queue: return
        self.current_queue_idx = 0
        self.is_autoplay_mode = True
        self.search_queue_window.update_queue_signal.emit()
        first_track = self.queue[0]
        self.load_and_play(first_track)

    def _set_artwork(self, image_data):
        img = QImage()
        img.loadFromData(image_data)
        pixmap = QPixmap(img)
        
        # Center-crop to a 1:1 square
        min_dim = min(pixmap.width(), pixmap.height())
        x = (pixmap.width() - min_dim) // 2
        y = (pixmap.height() - min_dim) // 2
        
        cropped_pixmap = pixmap.copy(x, y, min_dim, min_dim)
        scaled_pixmap = cropped_pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_art.setPixmap(scaled_pixmap)
        
        if self.smtc and hasattr(self, 'current_track') and self.current_track:
            smtc_thumb_path = os.path.join(self.base_dir, "app", "cache", "smtc_thumb.jpg")
            scaled_pixmap.save(smtc_thumb_path, "JPG")
            self.smtc.update_metadata(self.current_track, smtc_thumb_path)

    def _play_prev(self, manual=True):
        if manual: self.is_autoplay_mode = False
        if self.current_queue_idx > 0:
            self.current_queue_idx -= 1
            self.search_queue_window.update_queue_signal.emit()
            self.load_and_play(self.queue[self.current_queue_idx])
            
    def _play_next(self, manual=True):
        if manual: self.is_autoplay_mode = False
        if self.current_queue_idx < len(self.queue) - 1:
            self.current_queue_idx += 1
            self.search_queue_window.update_queue_signal.emit()
            self.load_and_play(self.queue[self.current_queue_idx])
        else:
            self._trigger_autoplay()
            
    def _play_pause_toggle(self):
        if self.queue and self.mpv.get_time_pos() == 0:
            self.is_autoplay_mode = False
            if self.current_queue_idx == -1: self.current_queue_idx = 0
            self.load_and_play(self.queue[self.current_queue_idx])
            self.search_queue_window.update_queue_signal.emit()
        else:
            self.mpv.pause()
            if self.smtc:
                # If mpv is paused, its time_pos doesn't change, but we need to track status.
                # mpv.pause is a toggle in MPVController.
                pass # Actually we should just set it based on current state.
            
        if self.smtc:
            # We don't have direct access to self.mpv.mpv.pause cleanly, but we can assume.
            # It's better to update status. We will toggle it since we just called toggle.
            try:
                is_paused = self.mpv.mpv.pause
                self.smtc.set_playback_status(not is_paused)
            except:
                pass

    def _on_eof(self):
        if self.repeat_mode == 1:
            # Repeat One
            if self.current_queue_idx >= 0 and self.current_queue_idx < len(self.queue):
                self.load_and_play(self.queue[self.current_queue_idx])
        elif self.repeat_mode == 2:
            # Repeat All
            if self.current_queue_idx < len(self.queue) - 1:
                self._play_next(manual=False)
            elif self.queue:
                self.current_queue_idx = 0
                self.search_queue_window.update_queue_signal.emit()
                self.load_and_play(self.queue[self.current_queue_idx])
        else:
            # Off (Autoplay kicks in if queue ends)
            self._play_next(manual=False)

    def _trigger_autoplay(self):
        if self.current_queue_idx < 0 or not self.queue: return
        last_track = self.queue[self.current_queue_idx]
        artist = last_track['artist']
        
        if not self.is_autoplay_mode:
            # Show Autoplay Modal
            modal = AutoplayModal(self, artist, parent=self)
            # Position modal centered near main window
            modal.move(self.pos().x() + 35, self.pos().y() + 20)
            modal.exec()
            
            if modal.result_action == "loop":
                self.repeat_mode = 2 # Repeat All
                self.btn_repeat.setText("↻A")
                self.btn_repeat.setStyleSheet("color: #fff; background-color: #004400;")
                self.current_queue_idx = 0
                self.search_queue_window.update_queue_signal.emit()
                self.load_and_play(self.queue[0])
                return
            elif modal.result_action == "autoplay":
                self.is_autoplay_mode = True
            else:
                return
            
        self.update_display_signal.emit(f"AUTOPLAY: {artist}...")
        
        def fetch_related():
            results = self.itunes.get_related_tracks(artist, limit=5)
            if results:
                recent_ids = {t['id'] for t in self.queue[-10:]}
                new_tracks = [t for t in results if t['id'] not in recent_ids]
                if not new_tracks: new_tracks = results
                
                next_track = new_tracks[0]
                self.autoplay_track_signal.emit(next_track)
            else:
                self.update_display_signal.emit("AUTOPLAY FAILED")
        threading.Thread(target=fetch_related, daemon=True).start()

    def _on_autoplay_track(self, next_track):
        self.queue.append(next_track)
        self.search_queue_window.update_queue_signal.emit()
        self.current_queue_idx += 1
        self.load_and_play(next_track)
        


    def _update_duration(self, value):
        self.seek_bar.setMaximum(int(value))
        mins, secs = divmod(int(value), 60)
        self.lbl_duration.setText(f"{mins:02d}:{secs:02d}")

    def _update_time(self, value):
        if not self.seek_bar.is_dragging:
            self.seek_bar.setValue(int(value))
        mins, secs = divmod(int(value), 60)
        self.lbl_time.setText(f"{mins:02d}:{secs:02d}")
        
    def _on_seek(self, value):
        if self.seek_bar.is_dragging:
            self.mpv.seek(value)
            
    def trigger_save_layout(self):
        if hasattr(self, 'save_timer') and hasattr(self, 'search_queue_window'):
            self.save_timer.start(500)

    def save_window_positions(self):
        if not hasattr(self, 'search_queue_window'): return
        self.db.set_config('window_positions', {
            'main': [self.pos().x(), self.pos().y()],
            'search': [self.search_queue_window.pos().x(), self.search_queue_window.pos().y()],
            'playlist_contents': [self.playlist_contents_window.pos().x(), self.playlist_contents_window.pos().y()],
            'history': [self.history_window.pos().x(), self.history_window.pos().y()],
            
            'search_size': [self.search_queue_window.width(), self.search_queue_window.height()],
            'playlist_contents_size': [self.playlist_contents_window.width(), self.playlist_contents_window.height()],
            'history_size': [self.history_window.width(), self.history_window.height()],
            
            'search_visible': self.search_queue_window.isVisible(),
            'playlist_contents_visible': self.playlist_contents_window.isVisible(),
            'history_visible': self.history_window.isVisible()
        })

    def closeEvent(self, event):
        self.db.set_config('repeat_mode', self.repeat_mode)
        self.save_window_positions()
        
        # Aggressive quit
        try:
            self.mpv.shutdown()
        except:
            pass
            
        self.search_queue_window.close()
        self.playlist_contents_window.close()
        self.history_window.close()
        event.accept()
        
        import sys
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
        sys.exit(0)

    def import_playlist_url(self, url):
        """ Extract a playlist and create it in DB """
        self.update_display_signal.emit("IMPORTING PLAYLIST...")
        
        def do_import():
            tracks, title = self.yt.get_playlist_info(url)
            if not tracks:
                self.update_display_signal.emit("IMPORT FAILED")
                return
                
            pl_id = self.db.create_playlist(title)
            if not pl_id:
                # Append random number if exists
                import random
                pl_id = self.db.create_playlist(f"{title} ({random.randint(100, 999)})")
                
            for idx, track in enumerate(tracks):
                self.db.add_track_to_playlist(pl_id, track, idx)
                
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self.playlist_contents_window.refresh_playlists)
            self.update_display_signal.emit("IMPORT COMPLETE")
            
        import threading
        threading.Thread(target=do_import, daemon=True).start()

from PySide6.QtCore import QTimer

class AutoplayModal(QDialog):
    def __init__(self, master, artist, parent=None):
        super().__init__(parent)
        self.master = master
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(280, 110)
        self.setWindowModality(Qt.ApplicationModal)
        
        self.result_action = "autoplay"
        self.time_left = 30
        
        self.lbl_title = RetroDisplayLabel(" QUEUE ENDED", self)
        self.lbl_title.setGeometry(0, 0, 260, 20)
        
        self.lbl_msg = RetroDisplayLabel(f"Autoplaying similar to:\n{artist}", self)
        self.lbl_msg.setGeometry(10, 25, 260, 30)
        self.lbl_msg.setStyleSheet("background: transparent; color: #0f0; font-size: 10px;")
        
        self.lbl_timer = RetroDisplayLabel("30", self)
        self.lbl_timer.setGeometry(125, 60, 30, 20)
        
        self.btn_loop = RetroButton("Loop Playlist", self)
        self.btn_loop.setGeometry(10, 85, 100, 20)
        self.btn_loop.clicked.connect(self._loop)
        
        self.btn_auto = RetroButton("Autoplay Now", self)
        self.btn_auto.setGeometry(170, 85, 100, 20)
        self.btn_auto.clicked.connect(self._auto)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        painter.fillRect(rect, QColor(30, 35, 30))
        painter.setPen(QColor(100, 110, 100))
        painter.drawLine(rect.topLeft(), rect.topRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        painter.setPen(QColor(10, 15, 10))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        
    def _tick(self):
        self.time_left -= 1
        self.lbl_timer.setText(str(self.time_left))
        if self.time_left <= 0:
            self.accept()
            
    def _loop(self):
        self.result_action = "loop"
        self.accept()
        
    def _auto(self):
        self.result_action = "autoplay"
        self.accept()
        
    def accept(self):
        self.timer.stop()
        super().accept()
