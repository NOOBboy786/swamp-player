import yt_dlp

class YouTubeStreamer:
    def __init__(self):
        # We only want to extract the URL, not download the file
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            'extract_flat': False,
        }
        
    def get_stream_url(self, query):
        """
        Takes a search query (e.g. "Artist - Title") and returns the direct audio stream URL.
        """
        print(f"Searching YouTube for: {query}")
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Use ytsearch1: to get only the first result
                search_query = f"ytsearch1:{query}"
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info and len(info['entries']) > 0:
                    entry = info['entries'][0]
                    # The direct stream URL is inside the 'url' property, or 'requested_formats'
                    # Usually, 'url' gives the best match depending on options.
                    # Sometimes yt-dlp puts it in a format list.
                    if 'url' in entry:
                        return entry['url']
                    elif 'formats' in entry:
                        # get the best audio format
                        for f in reversed(entry['formats']):
                            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                                return f['url']
                elif 'url' in info:
                    return info['url']
                return None
        except Exception as e:
            print(f"Error fetching stream URL: {e}")
            return None

    def get_playlist_info(self, url):
        """
        Extracts playlist metadata without downloading streams.
        Returns a list of tracks.
        """
        opts = {
            'extract_flat': 'in_playlist',
            'quiet': True,
        }
        tracks = []
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        tracks.append({
                            'id': entry.get('id', ''),
                            'title': entry.get('title', 'Unknown Title'),
                            'artist': entry.get('uploader', 'Unknown Artist'),
                            'album': info.get('title', 'Unknown Playlist'),
                            'duration_ms': int(entry.get('duration', 0) or 0) * 1000,
                            'artwork_url': entry.get('thumbnail', '') or (entry.get('thumbnails', [{'url': ''}])[-1]['url'] if entry.get('thumbnails') else '')
                        })
                else:
                    # Single video
                    tracks.append({
                        'id': info.get('id', ''),
                        'title': info.get('title', 'Unknown Title'),
                        'artist': info.get('uploader', 'Unknown Artist'),
                        'album': 'Single Track',
                        'duration_ms': int(info.get('duration', 0) or 0) * 1000,
                        'artwork_url': info.get('thumbnail', '')
                    })
            return tracks, info.get('title', 'Imported Playlist')
        except Exception as e:
            print(f"Error extracting playlist: {e}")
            return [], "Error"

    def search(self, query, filter_type="ALL", limit=10):
        """
        Perform a yt-dlp search based on the filter type.
        filter_type: VIDEOS, COMMUNITY, PLAYLIST, ALL
        """
        search_query = query
        if filter_type in ["PLAYLIST", "COMMUNITY"]:
            # Bias yt-dlp toward playlists
            search_query = f"ytsearch{limit}:playlist {query}"
        else:
            search_query = f"ytsearch{limit}:{query}"
            
        opts = {
            'extract_flat': True,
            'quiet': True,
        }
        results = []
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        results.append({
                            'id': entry.get('id', ''),
                            'title': entry.get('title', 'Unknown Title'),
                            'artist': entry.get('uploader', 'Unknown Artist'),
                            'album': 'YouTube' if entry.get('_type') != 'playlist' else 'Playlist',
                            'duration_ms': int(entry.get('duration', 0) or 0) * 1000,
                            'artwork_url': entry.get('thumbnail') or (entry.get('thumbnails')[-1]['url'] if entry.get('thumbnails') else ''),
                            'source_platform': 'youtube',
                            'is_playlist': entry.get('_type') == 'playlist',
                            'url': entry.get('url', '')
                        })
            return results
        except Exception as e:
            print(f"Error in yt_dlp search: {e}")
            return []
