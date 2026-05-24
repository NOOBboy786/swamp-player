from PySide6.QtCore import QRect

def apply_magnetic_snap(moving_win, master):
    """
    Applies strong Winamp-style magnetic snapping (8-10px) to all visible application windows.
    """
    if not hasattr(master, 'search_queue_window'):
        return # Not fully initialized
        
    windows = [master, master.search_queue_window, master.playlist_contents_window, master.history_window]
    snap_dist = 10
    
    m_rect = moving_win.frameGeometry()
    snapped = False
    
    for w in windows:
        if w == moving_win or not w.isVisible(): 
            continue
            
        w_rect = w.frameGeometry()
        
        # Horizontal snapping
        if abs(m_rect.right() - w_rect.left()) < snap_dist:
            m_rect.moveRight(w_rect.left())
            snapped = True
        elif abs(m_rect.left() - w_rect.right()) < snap_dist:
            m_rect.moveLeft(w_rect.right())
            snapped = True
        elif abs(m_rect.left() - w_rect.left()) < snap_dist:
            m_rect.moveLeft(w_rect.left())
            snapped = True
            
        # Vertical snapping
        if abs(m_rect.bottom() - w_rect.top()) < snap_dist:
            m_rect.moveBottom(w_rect.top())
            snapped = True
        elif abs(m_rect.top() - w_rect.bottom()) < snap_dist:
            m_rect.moveTop(w_rect.bottom())
            snapped = True
        elif abs(m_rect.top() - w_rect.top()) < snap_dist:
            m_rect.moveTop(w_rect.top())
            snapped = True
            
    if snapped:
        moving_win.move(m_rect.topLeft())
