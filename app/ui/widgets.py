from PySide6.QtWidgets import QWidget, QPushButton, QLabel
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent
from PySide6.QtCore import Qt, QRect, Signal

class RetroButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Arial", 8, QFont.Bold))

    def get_accent_color(self):
        try:
            return QColor(self.window().master.accent_color)
        except:
            return QColor(0, 255, 0)
            
    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        
        # Bevel colors
        if self.isDown():
            bg_color = QColor(40, 40, 40)
            top_border = QColor(20, 20, 20)
            bottom_border = QColor(100, 100, 100)
            text_color = self.get_accent_color().darker(150)
        else:
            bg_color = QColor(60, 60, 60)
            top_border = QColor(120, 120, 120)
            bottom_border = QColor(30, 30, 30)
            text_color = self.get_accent_color()
            
        # Fill
        painter.fillRect(rect, bg_color)
        
        # Draw Bevel
        painter.setPen(top_border)
        painter.drawLine(rect.topLeft(), rect.topRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        
        painter.setPen(bottom_border)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        
        # Text
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignCenter, self.text())

class RetroDisplayLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Consolas", 9))
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def get_accent_color(self):
        try:
            return QColor(self.window().master.accent_color)
        except:
            return QColor(0, 255, 0)
            
    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        
        # Dark recessed background
        painter.fillRect(rect, QColor(10, 15, 10))
        
        # Inner shadow / Bevel
        painter.setPen(QColor(40, 40, 40))
        painter.drawLine(rect.topLeft(), rect.topRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        painter.setPen(QColor(80, 80, 80))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        
        # Text
        text_rect = rect.adjusted(5, 0, -5, 0)
        painter.setPen(self.get_accent_color())
        painter.drawText(text_rect, self.alignment(), self.text())

class RetroSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max = 100
        self.is_dragging = False

    def setValue(self, val):
        if not self.is_dragging:
            self._value = max(0, min(self._max, val))
            self.update()

    def setMaximum(self, val):
        self._max = val
        self.update()

    def value(self):
        return self._value
        
    def _update_from_mouse(self, pos):
        width = self.width() - 4
        x = max(0, min(width, pos.x() - 2))
        self._value = int((x / width) * self._max)
        self.valueChanged.emit(self._value)
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self._update_from_mouse(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging:
            self._update_from_mouse(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        
        # Track background (recessed)
        painter.fillRect(rect, QColor(20, 20, 20))
        painter.setPen(QColor(10, 10, 10))
        painter.drawLine(rect.topLeft(), rect.topRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        painter.setPen(QColor(60, 60, 60))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        
        if self._max <= 0:
            return
            
        # Fill portion
        fill_width = int((self._value / self._max) * (rect.width() - 4))
        if fill_width > 0:
            fill_rect = QRect(2, 2, fill_width, rect.height() - 4)
            painter.fillRect(fill_rect, QColor(0, 150, 0))

def get_retro_scrollbar_style():
    return """
        QScrollBar:vertical {
            border: 1px solid #444;
            background: #111;
            width: 12px;
            margin: 12px 0 12px 0;
        }
        QScrollBar::handle:vertical {
            background: #444;
            min-height: 15px;
            border: 1px solid #777;
        }
        QScrollBar::add-line:vertical {
            border: 1px solid #444;
            background: #222;
            height: 12px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }
        QScrollBar::sub-line:vertical {
            border: 1px solid #444;
            background: #222;
            height: 12px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
            width: 3px;
            height: 3px;
            background: #0f0;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
    """

from PySide6.QtWidgets import QDialog

class RetroMessageBox(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(250, 100)
        self.setWindowModality(Qt.ApplicationModal)
        
        self.lbl_msg = RetroDisplayLabel(text, self)
        self.lbl_msg.setGeometry(10, 20, 230, 40)
        self.lbl_msg.setAlignment(Qt.AlignCenter)
        self.lbl_msg.setStyleSheet("background: transparent; color: #0f0; font-size: 11px;")
        
        self.btn_ok = RetroButton("OK", self)
        self.btn_ok.setGeometry(60, 70, 50, 20)
        self.btn_ok.clicked.connect(self.accept)
        
        self.btn_cancel = RetroButton("CANCEL", self)
        self.btn_cancel.setGeometry(140, 70, 50, 20)
        self.btn_cancel.clicked.connect(self.reject)
        
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
