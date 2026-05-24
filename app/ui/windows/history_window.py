from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QListWidget, QListWidgetItem, QMenu, QLineEdit)
from PySide6.QtGui import QPainter, QColor, QMouseEvent, QDrag
from PySide6.QtCore import Qt, QPoint, QMimeData
import json

from app.ui.widgets import RetroDisplayLabel, RetroButton

def draw_retro_bevel(painter, rect, is_title=False):
    painter.fillRect(rect, QColor(40, 45, 40))
    painter.setPen(QColor(100, 110, 100))
    painter.drawLine(rect.topLeft(), rect.topRight())
    painter.drawLine(rect.topLeft(), rect.bottomLeft())
    painter.setPen(QColor(10, 15, 10))
    painter.drawLine(rect.bottomLeft(), rect.bottomRight())
    painter.drawLine(rect.topRight(), rect.bottomRight())
    if is_title:
        title_rect = rect.adjusted(2, 2, -2, -(rect.height()-20))
        painter.fillRect(title_rect, QColor(20, 25, 20))

from PySide6.QtWidgets import QHBoxLayout

class HistoryItemWidget(QWidget):
    def __init__(self, master, record, refresh_cb, parent=None):
        super().__init__(parent)
        self.master = master
        self.record = record
        self.refresh_cb = refresh_cb
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.addStretch()
        
        self.btn_del = RetroButton("X")
        self.btn_del.setFixedSize(20, 20)
        self.btn_del.setStyleSheet("color: #f00;")
        self.btn_del.clicked.connect(self._del_clicked)
        layout.addWidget(self.btn_del)
        
    def _del_clicked(self):
        from app.ui.widgets import RetroMessageBox
        dlg = RetroMessageBox("Remove from history?")
        if dlg.exec():
            self.master.db.remove_from_history(self.record['id'])
            self.refresh_cb()
            
    def mousePressEvent(self, event):
        event.ignore()
        
    def mouseDoubleClickEvent(self, event):
        event.ignore()

class HistoryWindow(QWidget):
    def __init__(self, master):
        super().__init__()
        self.master = master
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(250, 250)
        self.resize(300, 300)
        self.drag_pos = QPoint()
        
        self._init_ui()
        self.refresh_history()
        
        from PySide6.QtWidgets import QSizeGrip
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background-color: transparent;")
        
    def _init_ui(self):
        self.lbl_title = RetroDisplayLabel(" HISTORY", self)
        self.lbl_title.setGeometry(0, 0, 275, 20)
        self.lbl_title.setStyleSheet("background: transparent; color: #888;")
        
        self.btn_close = RetroButton("X", self)
        self.btn_close.setGeometry(275, 2, 20, 16)
        self.btn_close.clicked.connect(self.hide)
        
        # Filter Buttons
        self.filter_mode = None
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(0)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_all = RetroButton("ALL", self)
        btn_all.clicked.connect(lambda: self._set_filter(None))
        btn_songs = RetroButton("SONGS", self)
        btn_songs.clicked.connect(lambda: self._set_filter('song'))
        btn_playlists = RetroButton("PLAYLISTS", self)
        btn_playlists.clicked.connect(lambda: self._set_filter('playlist'))
        btn_albums = RetroButton("ALBUMS", self)
        btn_albums.clicked.connect(lambda: self._set_filter('album'))
        
        filter_layout.addWidget(btn_all)
        filter_layout.addWidget(btn_songs)
        filter_layout.addWidget(btn_playlists)
        filter_layout.addWidget(btn_albums)
        
        self.txt_search = QLineEdit(self)
        self.txt_search.setGeometry(10, 25, 280, 20)
        self.txt_search.setStyleSheet("background-color: #111; color: #0f0; border: 1px solid #444; font-family: Consolas;")
        self.txt_search.setPlaceholderText("Search history...")
        self.txt_search.textChanged.connect(self.refresh_history)

        self.filter_container = QWidget(self)
        self.filter_container.setGeometry(10, 48, 280, 20)
        self.filter_container.setLayout(filter_layout)
        
        self.list_history = QListWidget(self)
        self.list_history.setGeometry(10, 71, 280, 219)
        
        from app.ui.widgets import get_retro_scrollbar_style
        self.list_history.setStyleSheet("""
            QListWidget {
                background-color: #050505; color: #0f0; border: 2px solid #333;
                font-family: Consolas; font-size: 11px;
            }
            QListWidget::item:selected {
                background-color: #004400; color: #fff;
            }
        """ + get_retro_scrollbar_style())
        
        from app.ui.delegates import RetroItemDelegate
        self.delegate_history = RetroItemDelegate(self.list_history)
        self.list_history.setItemDelegate(self.delegate_history)
        self.list_history.setFocusPolicy(Qt.NoFocus)
        self.list_history.setDragEnabled(True)
        self.list_history.setSelectionMode(QListWidget.SingleSelection)
        self.list_history.itemDoubleClicked.connect(self._replay_item)
        self.list_history.startDrag = self._start_drag
        self.list_history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_history.customContextMenuRequested.connect(self._show_context_menu)

    def _set_filter(self, mode):
        self.filter_mode = mode
        self.refresh_history()

    def _start_drag(self, supported_actions):
        item = self.list_history.currentItem()
        if not item: return
        track = item.data(Qt.UserRole)
        self.master.dragged_track = track
        
        mime = QMimeData()
        mime.setText(json.dumps(track))
        
        drag = QDrag(self.list_history)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        self.lbl_title.setGeometry(0, 0, w - 25, 20)
        self.btn_close.setGeometry(w - 25, 2, 20, 16)
        self.txt_search.setGeometry(10, 25, w - 20, 20)
        self.filter_container.setGeometry(10, 48, w - 20, 20)
        self.list_history.setGeometry(10, 71, w - 20, h - 81)
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

    def refresh_history(self):
        self.list_history.clear()
        history = self.master.db.get_history(limit=500, item_type=self.filter_mode)
        search_query = self.txt_search.text().lower()
        
        for record in history:
            if search_query:
                title = record.get('title', record.get('name', '')).lower()
                artist = record.get('artist', '').lower()
                album = record.get('album', '').lower()
                if search_query not in title and search_query not in artist and search_query not in album:
                    continue
            item = QListWidgetItem("") # text handled by delegate
            item.setData(Qt.UserRole, record)
            # Size hint must be explicitly set if we overlay a widget that is smaller, but delegate sets it to 36
            self.list_history.addItem(item)
            
            w = HistoryItemWidget(self.master, record, self.refresh_history)
            w.setStyleSheet("background: transparent;")
            self.list_history.setItemWidget(item, w)
            
    def _replay_item(self, item):
        track = item.data(Qt.UserRole)
        t_type = track.get('type', '')
        if t_type == 'album' or track.get('is_playlist'):
            self.master.is_autoplay_mode = False
        else:
            self.master.is_autoplay_mode = True
        self.master.queue.append(track)
        self.master.current_queue_idx = len(self.master.queue) - 1
        self.master.search_queue_window.update_queue_signal.emit()
        self.master.load_and_play(track)
        
    def _show_context_menu(self, pos):
        item = self.list_history.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #222; color: #0f0; border: 1px solid #444; }
            QMenu::item:selected { background-color: #004400; }
        """)
        
        play_action = menu.addAction("Replay Song")
        remove_action = menu.addAction("Remove from History")
        clear_action = menu.addAction("Clear All History")
        
        action = menu.exec(self.list_history.mapToGlobal(pos))
        
        if action == play_action:
            self._replay_item(item)
        elif action == remove_action:
            record = item.data(Qt.UserRole)
            from app.ui.widgets import RetroMessageBox
            dlg = RetroMessageBox("Remove from history?")
            if dlg.exec():
                self.master.db.remove_from_history(record['id'])
                self.refresh_history()
        elif action == clear_action:
            from app.ui.widgets import RetroMessageBox
            dlg = RetroMessageBox("Clear all history?")
            if dlg.exec():
                self.master.db.clear_history()
                self.refresh_history()
