import sqlite3
import os
import json

class Database:
    def __init__(self, base_dir):
        # Always use %APPDATA%/Caveman for the database so it persists across executable moves
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        db_dir = os.path.join(appdata, "Caveman", "database")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "caveman.db")
        self._init_db()
        
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = 1")
        return conn
        
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT UNIQUE,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    duration_ms INTEGER,
                    artwork_url TEXT,
                    play_count INTEGER DEFAULT 1,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER,
                    track_id TEXT,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    duration_ms INTEGER,
                    artwork_url TEXT,
                    order_index INTEGER,
                    source_platform TEXT,
                    uploader TEXT,
                    FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT UNIQUE,
                    value TEXT
                )
            ''')
            
            # Simple migrations for existing tables (if they were created without the new columns)
            try: cursor.execute("ALTER TABLE history ADD COLUMN play_count INTEGER DEFAULT 1")
            except: pass
            
            try: cursor.execute("ALTER TABLE playlist_tracks ADD COLUMN source_platform TEXT")
            except: pass
            
            try: cursor.execute("ALTER TABLE playlist_tracks ADD COLUMN uploader TEXT")
            except: pass
            
            conn.commit()

    # --- Config Management ---
    def set_config(self, key, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            val_str = json.dumps(value)
            cursor.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, val_str))
            conn.commit()

    def get_config(self, key, default=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default

    # --- History Management ---
    def add_to_history(self, track_info):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Ensure type column exists
            try: cursor.execute("ALTER TABLE history ADD COLUMN type TEXT DEFAULT 'song'")
            except: pass
            
            track_id = str(track_info.get('id', ''))
            
            # Check if it's the MOST recent song. If it is exactly the same, don't update/insert to avoid spam.
            cursor.execute('SELECT track_id FROM history ORDER BY played_at DESC LIMIT 1')
            last_row = cursor.fetchone()
            if last_row and last_row[0] == track_id:
                return # Do nothing if it's already the most recently played song
                
            # Check if exists to update play_count and played_at
            cursor.execute('SELECT id, play_count FROM history WHERE track_id = ?', (track_id,))
            row = cursor.fetchone()
            
            if row:
                cursor.execute('''
                    UPDATE history 
                    SET play_count = play_count + 1, played_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (row[0],))
            else:
                cursor.execute('''
                    INSERT INTO history (track_id, title, artist, album, duration_ms, artwork_url, play_count, type)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                ''', (
                    track_id,
                    track_info.get('title', track_info.get('name', '')),
                    track_info.get('artist', ''),
                    track_info.get('album', ''),
                    track_info.get('duration_ms', 0),
                    track_info.get('artwork_url', ''),
                    track_info.get('type', 'song')
                ))
            conn.commit()
            
    def get_history(self, limit=100, item_type=None):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if item_type:
                cursor.execute('SELECT * FROM history WHERE type = ? ORDER BY played_at DESC LIMIT ?', (item_type, limit))
            else:
                cursor.execute('SELECT * FROM history ORDER BY played_at DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
            
    def clear_history(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM history')
            conn.commit()
            
    def remove_from_history(self, history_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM history WHERE id = ?', (history_id,))
            conn.commit()

    # --- Playlist Management ---
    def create_playlist(self, name):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO playlists (name) VALUES (?)', (name,))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None 
                
    def rename_playlist(self, playlist_id, new_name):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('UPDATE playlists SET name = ? WHERE id = ?', (new_name, playlist_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def delete_playlist(self, playlist_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
            conn.commit()
            
    def get_all_playlists(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM playlists ORDER BY created_at ASC')
            return [dict(row) for row in cursor.fetchall()]
            
    def get_playlist_tracks(self, playlist_id):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM playlist_tracks WHERE playlist_id = ? ORDER BY order_index ASC', (playlist_id,))
            return [dict(row) for row in cursor.fetchall()]
            
    def add_track_to_playlist(self, playlist_id, track_info, order_index):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO playlist_tracks (playlist_id, track_id, title, artist, album, duration_ms, artwork_url, order_index, source_platform, uploader)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                playlist_id,
                str(track_info.get('id', '')),
                track_info.get('title', ''),
                track_info.get('artist', ''),
                track_info.get('album', ''),
                track_info.get('duration_ms', 0),
                track_info.get('artwork_url', ''),
                order_index,
                track_info.get('source_platform', ''),
                track_info.get('uploader', '')
            ))
            conn.commit()
            
    def remove_track_from_playlist(self, track_db_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM playlist_tracks WHERE id = ?', (track_db_id,))
            conn.commit()
            
    def clear_playlist_tracks(self, playlist_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,))
            conn.commit()
            
    def update_playlist_order(self, track_db_ids_in_order):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for idx, track_db_id in enumerate(track_db_ids_in_order):
                cursor.execute('UPDATE playlist_tracks SET order_index = ? WHERE id = ?', (idx, track_db_id))
            conn.commit()
