import os
from python_mpv_jsonipc import MPV
from PySide6.QtCore import QObject, Signal

class MPVSignals(QObject):
    time_pos_changed = Signal(float)
    duration_changed = Signal(float)
    eof_reached = Signal()

class MPVController:
    def __init__(self, base_dir):
        self.bin_dir = os.path.join(base_dir, "app", "bin", "mpv")
        self.mpv_exe = os.path.join(self.bin_dir, "mpv.exe")
        self.mpv = None
        self.signals = MPVSignals()
        
    def start(self):
        if not os.path.exists(self.mpv_exe):
            print("mpv.exe not found! Please ensure it is downloaded.")
            return False
            
        print(f"Starting mpv from {self.mpv_exe}")
        
        # Monkey patch subprocess.Popen inside python_mpv_jsonipc to hide the console window on Windows
        import python_mpv_jsonipc
        import subprocess
        _orig_popen = python_mpv_jsonipc.subprocess.Popen
        def _hidden_popen(*args, **kwargs):
            if os.name == 'nt':
                kwargs['creationflags'] = 0x08000000 # CREATE_NO_WINDOW
            return _orig_popen(*args, **kwargs)
        python_mpv_jsonipc.subprocess.Popen = _hidden_popen
        
        # Monkey patch os.path.exists to return True for Windows named pipes.
        # Python's os.path.exists always returns False for them, causing python_mpv_jsonipc to timeout.
        _orig_exists = os.path.exists
        def _pipe_exists(path):
            if os.name == 'nt' and path.startswith('\\\\.\\pipe\\'):
                # Try to open the pipe briefly to see if it exists, or just return True.
                # Since python_mpv_jsonipc has connection retries, returning True is safe.
                return True
            return _orig_exists(path)
        os.path.exists = _pipe_exists
        
        try:
            # Initialize MPV. force_window="no" ensures no GUI window pops up.
            self.mpv = MPV(start_mpv=True, mpv_location=self.mpv_exe, vid="no", force_window="no", input_media_keys="no")
        finally:
            # Restore the original Popen and os.path.exists
            python_mpv_jsonipc.subprocess.Popen = _orig_popen
            os.path.exists = _orig_exists
        
        # Setup property observers
        @self.mpv.property_observer('time-pos')
        def time_observer(_name, value):
            if value is not None:
                self.signals.time_pos_changed.emit(value)
                
        @self.mpv.property_observer('duration')
        def duration_observer(_name, value):
            if value is not None:
                self.signals.duration_changed.emit(value)
                
        @self.mpv.property_observer('eof-reached')
        def eof_observer(_name, value):
            if value:
                self.signals.eof_reached.emit()

        return True
        
    def play(self, url):
        if self.mpv:
            self.mpv.play(url)
            
    def pause(self):
        if self.mpv:
            self.mpv.pause = not self.mpv.pause
            
    def stop(self):
        if self.mpv:
            self.mpv.command("stop")
            
    def set_volume(self, value):
        # value from 0 to 100
        if self.mpv:
            self.mpv.volume = value
            
    def seek(self, position):
        if self.mpv:
            self.mpv.command("seek", position, "absolute")
            
    def get_duration(self):
        if self.mpv:
            return self.mpv.duration
        return 0

    def get_time_pos(self):
        if self.mpv:
            return self.mpv.time_pos
        return 0
        
    def shutdown(self):
        if self.mpv:
            try:
                self.mpv.terminate()
            except:
                pass
            if hasattr(self.mpv, 'mpv_process') and self.mpv.mpv_process:
                try:
                    self.mpv.mpv_process.kill()
                except:
                    pass
