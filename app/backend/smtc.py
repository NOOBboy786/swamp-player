import os
import asyncio
import threading
from PySide6.QtCore import QObject, Signal
from winrt.windows.media.playback import MediaPlayer
from winrt.windows.media import MediaPlaybackType, SystemMediaTransportControlsButton, MediaPlaybackStatus
import winrt.windows.storage as storage
from winrt.windows.storage.streams import RandomAccessStreamReference

class SMTCSignals(QObject):
    play_pause = Signal()
    next_track = Signal()
    prev_track = Signal()

class SMTCController:
    def __init__(self):
        self.signals = SMTCSignals()
        self.player = MediaPlayer()
        self.smtc = self.player.system_media_transport_controls
        
        self.smtc.is_play_enabled = True
        self.smtc.is_pause_enabled = True
        self.smtc.is_next_enabled = True
        self.smtc.is_previous_enabled = True
        
        self.smtc.add_button_pressed(self._on_button_pressed)
        
    def _on_button_pressed(self, sender, args):
        button = args.button
        if button == SystemMediaTransportControlsButton.PLAY:
            self.signals.play_pause.emit()
        elif button == SystemMediaTransportControlsButton.PAUSE:
            self.signals.play_pause.emit()
        elif button == SystemMediaTransportControlsButton.NEXT:
            self.signals.next_track.emit()
        elif button == SystemMediaTransportControlsButton.PREVIOUS:
            self.signals.prev_track.emit()
            
    def set_playback_status(self, is_playing):
        if is_playing:
            self.smtc.playback_status = MediaPlaybackStatus.PLAYING
        else:
            self.smtc.playback_status = MediaPlaybackStatus.PAUSED
            
    def update_metadata(self, track, thumbnail_path=None):
        def _update():
            updater = self.smtc.display_updater
            updater.type = MediaPlaybackType.MUSIC
            
            title = track.get('title', track.get('album', 'Unknown'))
            if track.get('type') == 'album':
                title = f"[ALBUM] {title}"
            elif track.get('is_playlist'):
                title = f"[PLAYLIST] {title}"
            
            updater.music_properties.title = title
            updater.music_properties.artist = track.get('artist', 'Unknown')
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                async def _load_thumbnail():
                    try:
                        file = await storage.StorageFile.get_file_from_path_async(os.path.abspath(thumbnail_path))
                        stream_ref = RandomAccessStreamReference.create_from_file(file)
                        updater.thumbnail = stream_ref
                        updater.update()
                    except Exception as e:
                        print(f"Failed to load SMTC thumbnail: {e}")
                        updater.update()
                
                # Run async loading in a temporary event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_load_thumbnail())
                loop.close()
            else:
                updater.update()
                
        # Run in a background thread to prevent blocking the UI
        threading.Thread(target=_update, daemon=True).start()
