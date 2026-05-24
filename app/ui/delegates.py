from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap
from PySide6.QtCore import Qt, QRect

from app.backend.thumbnails import ThumbnailManager

class RetroItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumb_mgr = ThumbnailManager.get_instance()
        # Connect to thumbnail loaded signal to trigger repaint
        if self.thumb_mgr:
            self.thumb_mgr.signals.loaded.connect(self._on_thumb_loaded)
            self.parent_widget = parent
            
    def _on_thumb_loaded(self, url, pixmap):
        if self.parent_widget:
            self.parent_widget.viewport().update()
            
    def sizeHint(self, option, index):
        track = index.data(Qt.UserRole)
        if track and isinstance(track, dict):
            return QRect(0, 0, option.rect.width(), 36).size()
        return super().sizeHint(option, index)
        
    def paint(self, painter: QPainter, option, index):
        painter.save()
        
        # Draw Background
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(0, 68, 0)) # #004400
        else:
            painter.fillRect(option.rect, QColor(5, 5, 5)) # #050505
            
        track = index.data(Qt.UserRole)
        
        if track and isinstance(track, dict):
            # Draw Thumbnail
            art_url = track.get('artwork_url')
            if art_url and self.thumb_mgr:
                pix = self.thumb_mgr.get_thumbnail(art_url, size=(30, 30))
                if pix:
                    painter.drawPixmap(option.rect.x() + 3, option.rect.y() + 3, pix)
                else:
                    # Draw placeholder
                    painter.fillRect(option.rect.x() + 3, option.rect.y() + 3, 30, 30, QColor(20, 20, 20))
                    painter.setPen(QColor(100, 100, 100))
                    painter.drawRect(option.rect.x() + 3, option.rect.y() + 3, 30, 30)
            
            # Draw Text
            if option.state & QStyle.State_Selected:
                painter.setPen(QColor(255, 255, 255))
            else:
                source = track.get('source_platform', '')
                if source == 'spotify':
                    painter.setPen(QColor(0, 255, 0)) # Green
                elif source == 'apple':
                    painter.setPen(QColor(255, 105, 180)) # Pink
                elif source == 'youtube':
                    painter.setPen(QColor(255, 50, 50)) # Red
                else:
                    painter.setPen(QColor(0, 255, 0)) # Default Green
                
            font = QFont("Consolas", 9)
            painter.setFont(font)
            
            title = track.get('title', track.get('album', 'Unknown'))
            if track.get('type') == 'album':
                title = f"[ALBUM] {title}"
            elif track.get('is_playlist'):
                title = f"[PLAYLIST] {title}"
                
            artist = track.get('artist', 'Unknown')
            
            # Top line: Title
            painter.drawText(option.rect.x() + 40, option.rect.y() + 14, title[:40])
            
            # Bottom line: Artist & Duration
            painter.setPen(QColor(150, 150, 150))
            font.setPointSize(8)
            painter.setFont(font)
            
            duration = track.get('duration_ms', 0)
            mins, secs = divmod(duration // 1000, 60)
            dur_str = f"[{mins}:{secs:02d}]" if duration > 0 else ""
            
            painter.drawText(option.rect.x() + 40, option.rect.y() + 28, f"{artist} {dur_str}")
        else:
            # It's a header or simple string (e.g. Queue item or "--- SONGS ---")
            text = index.data(Qt.DisplayRole)
            alignment = index.data(Qt.TextAlignmentRole)
            if alignment is None:
                alignment = Qt.AlignCenter
                
            # Background override
            bg_brush = index.data(Qt.BackgroundRole)
            if bg_brush and not (option.state & QStyle.State_Selected):
                painter.fillRect(option.rect, bg_brush)
                
            # Foreground override
            fg_brush = index.data(Qt.ForegroundRole)
            if fg_brush and not (option.state & QStyle.State_Selected):
                painter.setPen(fg_brush.color())
            elif option.state & QStyle.State_Selected:
                painter.setPen(QColor(255, 255, 255))
            else:
                painter.setPen(QColor(150, 150, 150))
                
            font = QFont("Consolas", 10, QFont.Bold)
            painter.setFont(font)
            
            rect = option.rect
            if alignment & Qt.AlignLeft:
                rect = rect.adjusted(5, 0, -5, 0)
                
            painter.drawText(rect, alignment, str(text))
            
        painter.restore()
