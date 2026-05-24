import threading
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QSplitter, QListWidget, QListWidgetItem, QMenu,
                               QStackedWidget, QTreeWidget, QTreeWidgetItem, QInputDialog, QSizeGrip)
from PySide6.QtGui import QPainter, QMouseEvent, QColor
from PySide6.QtCore import Qt, QPoint

from app.ui.widgets import RetroDisplayLabel, RetroButton, RetroMessageBox
from app.ui.windows.history_window import draw_retro_bevel
from app.ui.snapping import apply_magnetic_snap

class PlaylistAndContentsWindow(QWidget):
    def __init__(self, master):
        super().__init__()
        self.master = master
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(250, 400)
        self.resize(300, 500)
        self.drag_pos = QPoint()
        
        self.current_playlist_id = None
        self.current_item = None
        
        self._init_ui()
        self.refresh_playlists()
        
    def _init_ui(self):
        w = self.width()
        h = self.height()
        
        # Absolute positioned Title Bar
        self.lbl_title = RetroDisplayLabel(" PLAYLISTS / CONTENTS", self)
        self.lbl_title.setGeometry(0, 0, w - 25, 20)
        self.lbl_title.setStyleSheet("background: transparent; color: #888;")
        
        self.btn_close = RetroButton("X", self)
        self.btn_close.setGeometry(w - 25, 2, 20, 16)
        self.btn_close.clicked.connect(self.hide)
        
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background-color: transparent;")
        self.size_grip.setGeometry(w - 15, h - 15, 15, 15)
        
        # The main container holding the layout
        self.container = QWidget(self)
        self.container.setGeometry(10, 25, w - 20, h - 35)
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Vertical)
        
        # Splitter style
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #444;
                border: 1px solid #222;
                height: 4px;
            }
        """)
        
        # TOP: PLAYLISTS
        self.playlist_container = QWidget()
        playlist_layout = QVBoxLayout(self.playlist_container)
        playlist_layout.setContentsMargins(0, 0, 0, 0)
        playlist_layout.setSpacing(2)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)
        self.btn_add = RetroButton("+")
        self.btn_add.setFixedSize(20, 20)
        self.btn_add.clicked.connect(self._add_playlist)
        
        self.btn_sub = RetroButton("-")
        self.btn_sub.setFixedSize(20, 20)
        self.btn_sub.clicked.connect(self._del_playlist)
        
        self.btn_ref = RetroButton("↻")
        self.btn_ref.setFixedSize(20, 20)
        self.btn_ref.clicked.connect(self.refresh_playlists)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_sub)
        btn_layout.addWidget(self.btn_ref)
        btn_layout.addStretch()

        self.list_playlists = QListWidget()
        self.list_playlists.setStyleSheet(self._list_style())
        self.list_playlists.itemClicked.connect(self._on_playlist_select)
        self.list_playlists.itemDoubleClicked.connect(self._play_full_playlist)
        self.list_playlists.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_playlists.customContextMenuRequested.connect(self._playlist_context_menu)
        
        playlist_layout.addLayout(btn_layout)
        playlist_layout.addWidget(self.list_playlists)

        # BOTTOM: CONTENTS
        self.contents_container = QWidget()
        contents_layout = QVBoxLayout(self.contents_container)
        contents_layout.setContentsMargins(0, 5, 0, 0)
        contents_layout.setSpacing(2)

        self.lbl_breadcrumb = RetroDisplayLabel("CONTENTS")
        self.lbl_breadcrumb.setStyleSheet("background: transparent; color: #aaa; font-size: 10px;")
        self.lbl_breadcrumb.setFixedHeight(15)
        
        self.stack = QStackedWidget()
        
        self.list_contents = QListWidget()
        self.list_contents.setStyleSheet(self._list_style())
        self.tree_contents = QTreeWidget()
        self.tree_contents.setHeaderHidden(True)
        self.tree_contents.setStyleSheet(self._list_style())
        
        from app.ui.delegates import RetroItemDelegate
        self.delegate_contents = RetroItemDelegate(self.list_contents)
        self.list_contents.setItemDelegate(self.delegate_contents)
        
        self.list_contents.itemDoubleClicked.connect(self._play_item)
        self.tree_contents.itemDoubleClicked.connect(self._play_tree_item)
        self.list_contents.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_contents.customContextMenuRequested.connect(self._contents_context_menu)
        
        self.stack.addWidget(self.list_contents)
        self.stack.addWidget(self.tree_contents)
        
        contents_layout.addWidget(self.lbl_breadcrumb)
        contents_layout.addWidget(self.stack)

        self.splitter.addWidget(self.playlist_container)
        self.splitter.addWidget(self.contents_container)
        self.splitter.setSizes([200, 300])

        main_layout.addWidget(self.splitter)
        
        # Drag and drop logic for contents (reorder)
        self.list_contents.setDragDropMode(QListWidget.DragDrop)
        self.list_contents.setAcceptDrops(True)
        self.list_contents.setDragEnabled(True)
        
        original_drop = self.list_contents.dropEvent
        def dropEvent_override(event):
            # Check if external drop
            if hasattr(self.master, 'dragged_track') and self.master.dragged_track:
                track = self.master.dragged_track
                if self.current_item and 'name' in self.current_item and not self.current_item.get('is_playlist'):
                    playlist_id = self.current_item['id']
                    tracks = self.master.db.get_playlist_tracks(playlist_id)
                    order = len(tracks)
                    self.master.db.add_track_to_playlist(playlist_id, track, order)
                    self.master.update_display_signal.emit(f"ADDED TO {self.current_item['name'].upper()}")
                    self.load_playlist(self.current_item) # refresh contents
                self.master.dragged_track = None
                event.acceptProposedAction()
                return

            original_drop(event)
            if self.current_item and 'name' in self.current_item and not self.current_item.get('is_playlist'):
                order = []
                # Skip the "Queue Full Playlist" item
                for i in range(1, self.list_contents.count()):
                    item = self.list_contents.item(i)
                    track = item.data(Qt.UserRole)
                    if track and isinstance(track, dict) and 'id' in track:
                        order.append(track['id'])
                self.master.db.update_playlist_order(order)
        self.list_contents.dropEvent = dropEvent_override
        
        def dragEnterEvent_override(event):
            if hasattr(self.master, 'dragged_track') and self.master.dragged_track:
                event.acceptProposedAction()
            else:
                event.ignore()
        self.list_contents.dragEnterEvent = dragEnterEvent_override
        
        def dragMoveEvent_override(event):
            if hasattr(self.master, 'dragged_track') and self.master.dragged_track:
                event.acceptProposedAction()
            else:
                event.ignore()
        self.list_contents.dragMoveEvent = dragMoveEvent_override

        # Drag and drop logic for playlist (receiving items)
        self.setAcceptDrops(True)

    def _list_style(self):
        from app.ui.widgets import get_retro_scrollbar_style
        return """
            QListWidget, QTreeWidget {
                background-color: #050505; color: #0f0; border: 2px solid #333;
                font-family: Consolas; font-size: 11px;
            }
            QListWidget::item:selected, QTreeWidget::item:selected {
                background-color: #004400; color: #fff;
            }
        """ + get_retro_scrollbar_style()

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        self.lbl_title.setGeometry(0, 0, w - 25, 20)
        self.btn_close.setGeometry(w - 25, 2, 20, 16)
        self.container.setGeometry(10, 25, w - 20, h - 45)
        self.size_grip.setGeometry(w - 15, h - 15, 15, 15)
        super().resizeEvent(event)
        if hasattr(self.master, 'trigger_save_layout'): self.master.trigger_save_layout()

    def paintEvent(self, event):
        draw_retro_bevel(QPainter(self), self.rect(), True)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            apply_magnetic_snap(self, self.master)
            event.accept()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self.master, 'trigger_save_layout'): self.master.trigger_save_layout()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self.master, 'trigger_save_layout'): self.master.trigger_save_layout()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self.master, 'trigger_save_layout'): self.master.trigger_save_layout()

    # PLAYLIST LOGIC
    def refresh_playlists(self):
        self.list_playlists.clear()
        playlists = self.master.db.get_all_playlists()
        for p in playlists:
            item = QListWidgetItem(f"► {p['name']}")
            item.setData(Qt.UserRole, p)
            self.list_playlists.addItem(item)
            
    def _add_playlist(self):
        text, ok = QInputDialog.getText(self, "New Playlist", "Enter playlist name:")
        if ok and text:
            self.master.db.create_playlist(text)
            self.refresh_playlists()
            
    def _del_playlist(self):
        if not self.current_playlist_id: return
        dlg = RetroMessageBox("Delete Playlist?")
        if dlg.exec():
            self.master.db.delete_playlist(self.current_playlist_id)
            self.current_playlist_id = None
            self.refresh_playlists()
            self.list_contents.clear()
            self.lbl_breadcrumb.setText("CONTENTS")

    def _on_playlist_select(self, item):
        p = item.data(Qt.UserRole)
        self.current_playlist_id = p['id']
        self.load_playlist(p)
        
    def _play_full_playlist(self, item):
        p = item.data(Qt.UserRole)
        tracks = self.master.db.get_playlist_tracks(p['id'])
        if not tracks: return
        self.master.is_autoplay_mode = False
        self.master.queue.clear()
        for t in tracks: self.master.queue.append(t)
        self.master.current_queue_idx = 0
        self.master.search_queue_window.update_queue_signal.emit()
        self.master.load_and_play(self.master.queue[0])
        
    def _menu_style(self):
        return """
            QMenu { background-color: #222; color: #0f0; border: 1px solid #444; }
            QMenu::item:selected { background-color: #004400; }
        """

    def _playlist_context_menu(self, pos):
        item = self.list_playlists.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        
        rn_act = menu.addAction("Rename Playlist")
        del_act = menu.addAction("Delete Playlist")
        play_act = menu.addAction("Play Playlist")
        queue_act = menu.addAction("Queue Playlist")
        
        action = menu.exec(self.list_playlists.mapToGlobal(pos))
        p = item.data(Qt.UserRole)
        
        if action == rn_act:
            text, ok = QInputDialog.getText(self, "Rename", "New name:")
            if ok and text:
                self.master.db.rename_playlist(p['id'], text)
                self.refresh_playlists()
                if self.current_playlist_id == p['id']:
                    self.load_playlist(p)
        elif action == del_act:
            self._del_playlist()
        elif action == play_act:
            self._play_full_playlist(item)
        elif action == queue_act:
            tracks = self.master.db.get_playlist_tracks(p['id'])
            for t in tracks: self.master.queue.append(t)
            self.master.search_queue_window.update_queue_signal.emit()

    def dragEnterEvent(self, event):
        if hasattr(self.master, 'dragged_track') and self.master.dragged_track:
            event.acceptProposedAction()
        elif event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if hasattr(self.master, 'dragged_track') and self.master.dragged_track:
            event.acceptProposedAction()
        elif event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if hasattr(self.master, 'dragged_track') and self.master.dragged_track:
            # We want to drop onto the list_playlists widget
            pos_in_list = self.list_playlists.mapFrom(self, event.position().toPoint())
            item = self.list_playlists.itemAt(pos_in_list)
            if item:
                playlist = item.data(Qt.UserRole)
                if playlist:
                    # Get max order_index to append
                    tracks = self.master.db.get_playlist_tracks(playlist['id'])
                    order = len(tracks)
                    self.master.db.add_track_to_playlist(playlist['id'], self.master.dragged_track, order)
                    self.master.update_display_signal.emit(f"ADDED TO {playlist['name'].upper()}")
                    if self.current_playlist_id == playlist['id']:
                        self.load_playlist(playlist) # refresh contents
            self.master.dragged_track = None
            event.acceptProposedAction()
            return
            
        urls = []
        if event.mimeData().hasUrls():
            urls = [url.toString() for url in event.mimeData().urls()]
        elif event.mimeData().hasText():
            urls = [event.mimeData().text()]
            
        for url in urls:
            self.master.import_playlist_url(url)
        event.acceptProposedAction()

    # CONTENTS LOGIC
    def load_artist(self, artist_data):
        self.current_item = artist_data
        artist_name = artist_data.get('artist', 'Unknown')
        if len(artist_name) > 30: artist_name = artist_name[:27] + "..."
        self.lbl_breadcrumb.setText(f"{artist_name}")
        self.tree_contents.clear()
        self.stack.setCurrentWidget(self.tree_contents)
        
        root = QTreeWidgetItem([artist_data.get('artist', 'Unknown')])
        self.tree_contents.addTopLevelItem(root)
        
        cat_albums = QTreeWidgetItem(root, ["Albums"])
        cat_singles = QTreeWidgetItem(root, ["Singles"])
        cat_unknown = QTreeWidgetItem(root, ["Unknown"])
        
        # We need to fetch the discography to populate
        def fetch():
            albums = self.master.itunes.lookup_artist_albums(artist_data['id'])
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: apply_albums(albums))
            
        def apply_albums(albums):
            for a in albums:
                child = QTreeWidgetItem([a.get('title', 'Unknown')])
                child.setData(0, Qt.UserRole, a)
                cat_albums.addChild(child)
            
            root.setExpanded(True)
            cat_albums.setExpanded(True)
            
        threading.Thread(target=fetch, daemon=True).start()
        self.show()

    def load_album(self, album_data):
        self.current_item = album_data
        artist = album_data.get('artist', 'Unknown')
        if len(artist) > 20: artist = artist[:17] + "..."
        self.lbl_breadcrumb.setText(f"{artist} > Albums > {album_data.get('title', 'Unknown')}")
        self.list_contents.clear()
        self.stack.setCurrentWidget(self.list_contents)
        
        item = QListWidgetItem("Queue Full Album")
        item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)
        item.setData(Qt.UserRole, "header")
        self.list_contents.addItem(item)
        
        def fetch():
            tracks = self.master.itunes.get_album_tracks(album_data['id'])
            for t in tracks:
                item = QListWidgetItem("") # Blank text, delegate handles it
                item.setData(Qt.UserRole, t)
                self.list_contents.addItem(item)
        # Fetching synchronously to avoid threading issues with QListWidget updates.
        tracks = self.master.itunes.get_album_tracks(album_data['id'])
        for track in tracks:
            item = QListWidgetItem("")
            item.setData(Qt.UserRole, track)
            self.list_contents.addItem(item)
            
        self.show()
        
    def load_playlist(self, playlist_data, autoplay=False):
        self.current_item = playlist_data
        p_name = playlist_data.get('title') if playlist_data.get('is_playlist') else playlist_data.get('name', 'Unknown')
        if len(p_name) > 30: p_name = p_name[:27] + "..."
        self.lbl_breadcrumb.setText(f"Playlists > {p_name}")
        self.list_contents.clear()
        self.stack.setCurrentWidget(self.list_contents)
        
        item = QListWidgetItem("Queue Full Playlist")
        item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)
        item.setData(Qt.UserRole, "header")
        self.list_contents.addItem(item)
        
        if playlist_data.get('is_playlist'):
            # YouTube/Community Playlist
            tracks, _ = self.master.yt.get_playlist_info(playlist_data['url'])
            for track in tracks:
                item = QListWidgetItem("") # Blank text, delegate handles it
                item.setData(Qt.UserRole, track)
                self.list_contents.addItem(item)
        else:
            tracks = self.master.db.get_playlist_tracks(playlist_data['id'])
            if not tracks:
                item = QListWidgetItem("Drag songs here...")
                item.setFlags(Qt.NoItemFlags)
                item.setData(Qt.UserRole, "empty")
                self.list_contents.addItem(item)
            else:
                for track in tracks:
                    item = QListWidgetItem("") # Blank text, delegate handles it
                    item.setData(Qt.UserRole, track)
                    self.list_contents.addItem(item)
            
        self.show()
        if autoplay:
            self._play_item(self.list_contents.item(0))
            
    def _play_tree_item(self, item):
        track = item.data(0, Qt.UserRole)
        if not track: return
        t_type = track.get('type')
        if t_type == 'album':
            self.load_album(track)
            
    def _play_item(self, item):
        if not item: return
        track = item.data(Qt.UserRole)
        if track == "header": track = self.current_item
        if track == "empty": return
        
        if track.get('type') == 'album' or 'name' in track or track.get('is_playlist'): 
            self.master.is_autoplay_mode = False
            self.master.queue.clear()
            
            if track.get('is_playlist'):
                tracks, _ = self.master.yt.get_playlist_info(track['url'])
                for t in tracks: self.master.queue.append(t)
            elif 'name' in track: # Local Playlist
                tracks = self.master.db.get_playlist_tracks(track['id'])
                for t in tracks: self.master.queue.append(t)
            else: # Album auto-queueing
                tracks = self.master.itunes.get_album_tracks(track['id'])
                for t in tracks: self.master.queue.append(t)
                
            self.master.repeat_mode = 2 # REPEAT ALL
            self.master.btn_repeat.setText("↻A")
            self.master.btn_repeat.setStyleSheet("color: #fff; background-color: #004400;")
            
            self.master.search_queue_window.update_queue_signal.emit()
            if self.master.queue:
                self.master.current_queue_idx = 0
                self.master.load_and_play(self.master.queue[0])
            return
            
        # Single track click
        self.master.is_autoplay_mode = True
        self.master.queue.append(track)
        self.master.current_queue_idx = len(self.master.queue) - 1
        self.master.search_queue_window.update_queue_signal.emit()
        self.master.load_and_play(track)

    def _contents_context_menu(self, pos):
        if self.stack.currentWidget() != self.list_contents: return
        
        item = self.list_contents.itemAt(pos)
        if not item: return
        track = item.data(Qt.UserRole)
        
        if track.get('type') == 'album' or 'name' in track or track.get('is_playlist'): return
        
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        
        play_act = menu.addAction("Play Song")
        rm_act = None
        if self.current_item and 'name' in self.current_item and not self.current_item.get('is_playlist'): 
            rm_act = menu.addAction("Remove from Playlist")
            
        action = menu.exec(self.list_contents.mapToGlobal(pos))
        
        if action == play_act:
            self._play_item(item)
        elif rm_act and action == rm_act:
            dlg = RetroMessageBox("Remove track?")
            if dlg.exec():
                self.master.db.remove_track_from_playlist(track['id'])
                self.load_playlist(self.current_item) # Refresh
