import threading
from PySide6.QtWidgets import (QWidget, QLineEdit, QListWidget, QListWidgetItem, QMenu, 
                               QHBoxLayout, QVBoxLayout, QFrame, QSplitter, QStackedWidget, 
                               QTreeWidget, QTreeWidgetItem)
from PySide6.QtGui import QPainter, QColor, QMouseEvent, QFont, QDrag
from PySide6.QtCore import Qt, QPoint, Signal, QSize, QMimeData
import json

from app.ui.widgets import RetroButton, RetroDisplayLabel
from app.ui.windows.history_window import draw_retro_bevel

class SearchQueueWindow(QWidget):
    update_search_signal = Signal()
    update_queue_signal = Signal()
    update_tree_signal = Signal(object, list) # parent_item, children
    
    def __init__(self, master):
        super().__init__()
        self.master = master
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(300, 300)
        self.resize(350, 420)
        self.drag_pos = QPoint()
        
        self.current_filter = "ALL"
        
        self.update_search_signal.connect(self._render_search_results)
        self.update_queue_signal.connect(self._render_queue)
        self.update_tree_signal.connect(self._render_tree_children)
        
        self._init_ui()
        
        from PySide6.QtWidgets import QSizeGrip
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background-color: transparent;")
        
    def _init_ui(self):
        self.lbl_title = RetroDisplayLabel(" SEARCH / QUEUE", self)
        self.lbl_title.setGeometry(0, 0, 325, 20)
        self.lbl_title.setStyleSheet("background: transparent; color: #888;")
        
        self.btn_close = RetroButton("X", self)
        self.btn_close.setGeometry(325, 2, 20, 16)
        self.btn_close.clicked.connect(self.hide)
        
        self.txt_search = QLineEdit(self)
        self.txt_search.setGeometry(10, 25, 260, 25)
        self.txt_search.setStyleSheet("background-color: #111; color: #0f0; border: 1px solid #444; font-family: Consolas;")
        self.txt_search.setPlaceholderText("Search")
        self.txt_search.returnPressed.connect(self._search_btn_clicked)
        
        self.btn_search = RetroButton("FIND", self)
        self.btn_search.setGeometry(280, 25, 60, 25)
        self.btn_search.clicked.connect(self._search_btn_clicked)
        
        # Filters Frame
        self.frame_filters = QFrame(self)
        self.frame_filters.setGeometry(10, 55, 330, 25)
        layout = QHBoxLayout(self.frame_filters)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(2)
        
        filters = ["ALL", "SONGS", "VIDEOS", "ALBUMS", "ARTISTS", "COMM", "PLAY"]
        self.filter_btns = {}
        for f in filters:
            btn = RetroButton(f, self.frame_filters)
            btn.setStyleSheet("font-size: 8px;")
            btn.clicked.connect(lambda checked=False, name=f: self._set_filter(name))
            self.filter_btns[f] = btn
            layout.addWidget(btn)
        self._update_filter_ui()
            
        # Main Layout container for Splitter
        self.container = QWidget(self)
        self.container.setGeometry(10, 85, 330, 325)
        vbox = QVBoxLayout(self.container)
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Vertical)
        vbox.addWidget(self.splitter)
        
        # Top half: Search Results (Stacked Widget to swap List/Tree)
        self.search_stack = QStackedWidget()
        
        self.list_search = QListWidget()
        self.list_search.setStyleSheet(self._list_style())
        
        from app.ui.delegates import RetroItemDelegate
        self.delegate_search = RetroItemDelegate(self.list_search)
        self.list_search.setItemDelegate(self.delegate_search)
        
        self.list_search.itemDoubleClicked.connect(self._on_search_double_click)
        self.list_search.itemClicked.connect(self._on_search_double_click)
        self.list_search.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_search.customContextMenuRequested.connect(self._search_context_menu)
        
        self.tree_search = QTreeWidget()
        self.tree_search.setHeaderHidden(True)
        self.tree_search.setStyleSheet(self._list_style())
        self.tree_search.itemExpanded.connect(self._on_tree_expanded)
        self.tree_search.itemDoubleClicked.connect(self._on_search_double_click)
        self.tree_search.itemClicked.connect(self._on_search_double_click)
        
        self.search_stack.addWidget(self.list_search)
        self.search_stack.addWidget(self.tree_search)
        
        # Bottom half: Queue
        self.queue_container = QWidget()
        q_vbox = QVBoxLayout(self.queue_container)
        q_vbox.setContentsMargins(0,5,0,0)
        q_vbox.setSpacing(2)
        
        self.lbl_queue = RetroDisplayLabel("QUEUE")
        self.lbl_queue.setStyleSheet("background: transparent; color: #888; font-size: 10px;")
        self.lbl_queue.setFixedHeight(15)
        q_vbox.addWidget(self.lbl_queue)
        
        self.list_queue = QListWidget()
        self.list_queue.setStyleSheet(self._list_style())
        
        self.delegate_queue = RetroItemDelegate(self.list_queue)
        self.list_queue.setItemDelegate(self.delegate_queue)
        
        self.list_queue.itemDoubleClicked.connect(self._play_queue_item)
        self.list_queue.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_queue.customContextMenuRequested.connect(self._queue_context_menu)
        self.list_queue.setDragDropMode(QListWidget.InternalMove)
        q_vbox.addWidget(self.list_queue)
        
        self.splitter.addWidget(self.search_stack)
        self.splitter.addWidget(self.queue_container)
        self.splitter.setSizes([160, 160])
        
        # Splitter style
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #444;
                border: 1px solid #222;
                height: 4px;
            }
        """)

        # Cross-window Drag Configuration
        self.list_search.setDragEnabled(True)
        self.list_queue.setDragEnabled(True)
        self.tree_search.setDragEnabled(True)
        
        def ls_drag(supported):
            it = self.list_search.currentItem()
            if not it: return
            track = it.data(Qt.UserRole)
            self.master.dragged_track = track
            mime = QMimeData()
            mime.setText(json.dumps(track))
            drag = QDrag(self.list_search)
            drag.setMimeData(mime)
            drag.exec(Qt.CopyAction)
        self.list_search.startDrag = ls_drag
        
        def ts_drag(supported):
            it = self.tree_search.currentItem()
            if not it: return
            track = it.data(0, Qt.UserRole)
            self.master.dragged_track = track
            mime = QMimeData()
            mime.setText(json.dumps(track))
            drag = QDrag(self.tree_search)
            drag.setMimeData(mime)
            drag.exec(Qt.CopyAction)
        self.tree_search.startDrag = ts_drag
        
        def lq_drag(supported):
            it = self.list_queue.currentItem()
            if not it: return
            idx = it.data(Qt.UserRole)
            track = self.master.queue[idx]
            self.master.dragged_track = track
            mime = QMimeData()
            mime.setText(json.dumps(track))
            drag = QDrag(self.list_queue)
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction | Qt.CopyAction)
        self.list_queue.startDrag = lq_drag

    def _search_btn_clicked(self):
        if self.txt_search.text().strip():
            self._set_filter("ALL")

    def _set_filter(self, name):
        self.current_filter = name
        self._update_filter_ui()
        if self.txt_search.text().strip():
            self._search() # Auto trigger search
        
    def _update_filter_ui(self):
        for name, btn in self.filter_btns.items():
            if name == self.current_filter:
                btn.setStyleSheet("font-size: 8px; color: #fff; background-color: #004400;")
            else:
                btn.setStyleSheet("font-size: 8px; color: #0f0;")

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
        
        self.txt_search.setGeometry(10, 25, w - 80, 25)
        self.btn_search.setGeometry(w - 65, 25, 55, 25)
        
        self.frame_filters.setGeometry(10, 55, w - 20, 25)
        
        # The container holding the splitter
        self.container.setGeometry(10, 85, w - 20, h - 95)
        
        self.size_grip.setGeometry(w - 15, h - 15, 15, 15)
        super().resizeEvent(event)

    def paintEvent(self, event):
        draw_retro_bevel(QPainter(self), self.rect(), True)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            from app.ui.snapping import apply_magnetic_snap
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
            
    def _search(self):
        query = self.txt_search.text().strip()
        if not query: return
        self.master.update_display_signal.emit(f"SEARCHING: {query}")
        self.list_search.clear()
        self.tree_search.clear()
        
        if self.current_filter in ["ARTISTS", "COMM", "PLAY"]:
            self.search_stack.setCurrentWidget(self.tree_search)
        else:
            self.search_stack.setCurrentWidget(self.list_search)
        
        def fetch():
            # Parallel fetching logic based on filters
            results = []
            if self.current_filter == "ALL":
                songs = self.master.itunes.search(query, entity='song', limit=4)
                albums = self.master.itunes.search(query, entity='album', limit=2)
                videos = self.master.yt.search(query, filter_type='VIDEOS', limit=2)
                results = {'songs': songs, 'albums': albums, 'videos': videos}
            elif self.current_filter == "SONGS":
                results = self.master.itunes.search(query, entity='song')
            elif self.current_filter == "ALBUMS":
                results = self.master.itunes.search(query, entity='album')
                if not results:
                    results = self.master.itunes.search(query, entity='song')
            elif self.current_filter == "ARTISTS":
                results = self.master.itunes.search(query, entity='musicArtist')
            elif self.current_filter in ["COMM", "PLAY", "VIDEOS"]:
                yt_filter = "COMMUNITY" if self.current_filter == "COMM" else ("PLAYLIST" if self.current_filter == "PLAY" else "VIDEOS")
                results = self.master.yt.search(query, filter_type=yt_filter)
                
            self.master.search_results = results
            self.update_search_signal.emit()
            self.master.update_display_signal.emit("SEARCH COMPLETE")
        threading.Thread(target=fetch, daemon=True).start()
        
    def _render_search_results(self):
        res = self.master.search_results
        
        if self.current_filter in ["ARTISTS", "COMM", "PLAY"]:
            self.tree_search.clear()
            for track in res:
                title = track.get('artist') if self.current_filter == "ARTISTS" else track.get('title')
                item = QTreeWidgetItem([title])
                item.setData(0, Qt.UserRole, track)
                # Add a dummy child to enable expansion arrow
                QTreeWidgetItem(item, ["Loading..."])
                self.tree_search.addTopLevelItem(item)
            return

        self.list_search.clear()
        
        def add_header(text):
            item = QListWidgetItem(f"--- {text} ---")
            item.setFlags(Qt.NoItemFlags) # Unselectable
            item.setForeground(QColor(150, 150, 150))
            self.list_search.addItem(item)
            
        def add_track(track):
            if track.get('type') == 'album' or self.current_filter == "ALBUMS":
                title = f"[ALBUM] {track['artist']} - {track.get('title', track.get('album'))}"
            elif track.get('is_playlist'):
                title = f"[PLAYLIST] {track['title']}"
            else:
                mins, secs = divmod(track.get('duration_ms', 0) // 1000, 60)
                title = f"{track['artist']} - {track['title']} [{mins}:{secs:02d}]"
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, track)
            self.list_search.addItem(item)

        if self.current_filter == "ALL" and isinstance(res, dict):
            if res.get('songs'):
                add_header("SONGS")
                for t in res['songs']: add_track(t)
            if res.get('albums'):
                add_header("ALBUMS")
                for t in res['albums']: add_track(t)
            if res.get('videos'):
                add_header("VIDEOS")
                for t in res['videos']: add_track(t)
        elif isinstance(res, list):
            for t in res: add_track(t)
            
    def _on_tree_expanded(self, item):
        track = item.data(0, Qt.UserRole)
        if not track: return
        t_type = track.get('type')
        is_playlist = track.get('is_playlist')
        
        if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
            if t_type == 'artist':
                def fetch_albums():
                    albums = self.master.itunes.lookup_artist_albums(track['id'])
                    self.update_tree_signal.emit(item, albums)
                threading.Thread(target=fetch_albums, daemon=True).start()
            elif is_playlist:
                def fetch_playlist_tracks():
                    tracks, _ = self.master.yt.get_playlist_info(track['url'])
                    self.update_tree_signal.emit(item, tracks)
                threading.Thread(target=fetch_playlist_tracks, daemon=True).start()

    def _render_tree_children(self, parent_item, children):
        parent_item.takeChildren() # Remove "Loading..."
        if not children:
            QTreeWidgetItem(parent_item, ["No items found"])
            return
            
        track = parent_item.data(0, Qt.UserRole)
        if track.get('type') == 'artist':
            cat_albums = QTreeWidgetItem(parent_item, ["Albums"])
            for c in children:
                child = QTreeWidgetItem(cat_albums, [f"{c.get('title', 'Unknown')}"])
                child.setData(0, Qt.UserRole, c)
        else:
            for idx, c in enumerate(children, 1):
                child = QTreeWidgetItem(parent_item, [f"{idx}. {c.get('title', 'Unknown')}"])
                child.setData(0, Qt.UserRole, c)
                
    def _on_search_click(self, item):
        pass # Merged into _on_search_double_click
            
    def _on_search_double_click(self, item):
        track = item.data(0, Qt.UserRole) if isinstance(item, QTreeWidgetItem) else item.data(Qt.UserRole)
        if not track: return
        
        t_type = track.get('type', '')
        if t_type == 'album' or self.current_filter == "ALBUMS":
            self.master.is_autoplay_mode = False
            album_id = track.get('id', track.get('collectionId'))
            if hasattr(self.master, '_play_full_album'):
                self.master._play_full_album(album_id)
            return
        elif t_type == 'artist':
            self.master.is_autoplay_mode = False
            self.master.playlist_contents_window.load_artist(track)
            return
        elif track.get('is_playlist'):
            self.master.is_autoplay_mode = False
            self.master.playlist_contents_window.load_playlist(track, autoplay=True)
            return
            
        # Standard track queueing
        self.master.is_autoplay_mode = True
        self.master.queue.append(track)
        self.master.current_queue_idx = len(self.master.queue) - 1
        self.update_queue_signal.emit()
        self.master.load_and_play(track)
            
    def _render_queue(self):
        self.list_queue.clear()
        # Bottom-to-Top Ordering: populate in reverse!
        for idx in range(len(self.master.queue) - 1, -1, -1):
            track = self.master.queue[idx]
            prefix = ">> " if idx == self.master.current_queue_idx else "   "
            mins, secs = divmod(track.get('duration_ms', 0) // 1000, 60)
            item = QListWidgetItem(f"{prefix}{track.get('artist','')} - {track.get('title','')} [{mins}:{secs:02d}]")
            item.setData(Qt.UserRole, idx)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if idx == self.master.current_queue_idx:
                item.setBackground(QColor(0, 50, 0))
                item.setForeground(QColor(200, 255, 200))
            self.list_queue.addItem(item)
            
    def _play_queue_item(self, item):
        idx = item.data(Qt.UserRole)
        self.master.is_autoplay_mode = False
        self.master.current_queue_idx = idx
        self._render_queue()
        self.master.load_and_play(self.master.queue[idx])

    def _menu_style(self):
        return """
            QMenu { background-color: #222; color: #0f0; border: 1px solid #444; }
            QMenu::item:selected { background-color: #004400; }
        """

    def _search_context_menu(self, pos):
        item = self.list_search.itemAt(pos)
        if not item or item.flags() & Qt.NoItemFlags: return
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        
        q_next = menu.addAction("Queue Next")
        q_last = menu.addAction("Queue Last")
        action = menu.exec(self.list_search.mapToGlobal(pos))
        
        track = item.data(Qt.UserRole)
        t_type = track.get('type', '')
        
        if action == q_next or action == q_last:
            def queue_items(items):
                if action == q_next:
                    if self.master.current_queue_idx != -1:
                        for i, t in enumerate(items):
                            self.master.queue.insert(self.master.current_queue_idx + 1 + i, t)
                    else:
                        for t in items: self.master.queue.append(t)
                else:
                    for t in items: self.master.queue.append(t)
                self.update_queue_signal.emit()

            if t_type == 'album' or self.current_filter == "ALBUMS":
                album_id = track.get('id', track.get('collectionId'))
                def fetch_and_queue():
                    tracks = self.master.itunes.get_album_tracks(album_id)
                    if tracks:
                        queue_items(tracks)
                threading.Thread(target=fetch_and_queue, daemon=True).start()
            elif track.get('is_playlist'):
                def fetch_and_queue():
                    tracks, _ = self.master.yt.get_playlist_info(track['url'])
                    if tracks:
                        queue_items(tracks)
                threading.Thread(target=fetch_and_queue, daemon=True).start()
            else:
                queue_items([track])

    def _queue_context_menu(self, pos):
        item = self.list_queue.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        
        play_act = menu.addAction("Play")
        remove_act = menu.addAction("Remove from Queue")
        clear_act = menu.addAction("Clear Queue")
        
        action = menu.exec(self.list_queue.mapToGlobal(pos))
        
        idx = item.data(Qt.UserRole)
        if action == play_act:
            self._play_queue_item(item)
        elif action == remove_act:
            self.master.queue.pop(idx)
            if self.master.current_queue_idx == idx:
                self.master.current_queue_idx = -1
                self.master.mpv.stop()
            elif self.master.current_queue_idx > idx:
                self.master.current_queue_idx -= 1
            self.update_queue_signal.emit()
        elif action == clear_act:
            self.master.queue.clear()
            self.master.current_queue_idx = -1
            self.master.mpv.stop()
            self.update_queue_signal.emit()
            
    def clear_all_items(self):
        self.master.queue.clear()
        self.master.current_queue_idx = -1
        self.master.mpv.stop()
        self.update_queue_signal.emit()
