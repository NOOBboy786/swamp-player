import sys
import os
from PySide6.QtWidgets import QApplication
from app.ui.main_window import CavemanPlayer

def main():
    app = QApplication(sys.argv)
    
    # Use Fusion style as base to avoid modern OS themes
    app.setStyle('Fusion')
    
    from PySide6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'assets', 'icon.ico')
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, 'app', 'assets', 'icon.ico')
    app.setWindowIcon(QIcon(icon_path))
    
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    player = CavemanPlayer(base_dir)
    player.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
