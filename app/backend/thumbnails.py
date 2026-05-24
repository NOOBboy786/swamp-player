import os
import requests
import hashlib
import threading
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QObject, Signal, Qt

class _ThumbSignals(QObject):
    loaded = Signal(str, QPixmap) # url, pixmap

class ThumbnailManager:
    _instance = None
    
    @classmethod
    def get_instance(cls, base_dir=None):
        if cls._instance is None and base_dir is not None:
            cls._instance = ThumbnailManager(base_dir)
        return cls._instance

    def __init__(self, base_dir):
        self.cache_dir = os.path.join(base_dir, "app", "cache", "thumbnails")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.signals = _ThumbSignals()
        self._memory_cache = {}
        self._in_flight = set()

    def get_thumbnail(self, url, size=(30, 30)):
        if not url: return None
        
        # 1. Check Memory
        if url in self._memory_cache:
            return self._memory_cache[url]
            
        # 2. Check Disk
        filename = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        filepath = os.path.join(self.cache_dir, filename)
        
        if os.path.exists(filepath):
            img = QImage(filepath)
            width = img.width()
            height = img.height()
            size_min = min(width, height)
            x = (width - size_min) // 2
            y = (height - size_min) // 2
            square_img = img.copy(x, y, size_min, size_min)
            pix = QPixmap.fromImage(square_img).scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._memory_cache[url] = pix
            return pix
            
        # 3. Fetch Async
        if url not in self._in_flight:
            self._in_flight.add(url)
            threading.Thread(target=self._download_thumbnail, args=(url, filepath, size), daemon=True).start()
            
        return None # Returns None immediately while loading
        
    def _download_thumbnail(self, url, filepath, size):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                
                img = QImage()
                img.loadFromData(res.content)
                width = img.width()
                height = img.height()
                size_min = min(width, height)
                x = (width - size_min) // 2
                y = (height - size_min) // 2
                square_img = img.copy(x, y, size_min, size_min)
                pix = QPixmap.fromImage(square_img).scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._memory_cache[url] = pix
                self.signals.loaded.emit(url, pix)
        except Exception as e:
            print(f"Thumbnail download failed: {url} -> {e}")
        finally:
            if url in self._in_flight:
                self._in_flight.remove(url)
