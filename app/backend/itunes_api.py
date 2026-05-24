import requests

class iTunesAPI:
    def __init__(self):
        self.base_url = "https://itunes.apple.com/search"

    def search(self, query, entity='song', limit=10):
        """
        Search iTunes with variable entity (song, album, musicArtist).
        """
        try:
            params = {
                'term': query,
                'entity': entity,
                'limit': limit
            }
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('results', []):
                artwork_url = item.get('artworkUrl100', '')
                if artwork_url:
                    artwork_url = artwork_url.replace('100x100bb', '300x300bb')
                    
                if entity == 'musicArtist':
                    results.append({
                        'id': item.get('artistId'),
                        'artist': item.get('artistName', 'Unknown Artist'),
                        'type': 'artist',
                        'source_platform': 'apple'
                    })
                elif entity == 'album':
                    results.append({
                        'id': item.get('collectionId'),
                        'title': item.get('collectionName', 'Unknown Album'),
                        'artist': item.get('artistName', 'Unknown Artist'),
                        'artwork_url': artwork_url,
                        'type': 'album',
                        'source_platform': 'apple'
                    })
                else:
                    results.append({
                        'id': item.get('trackId'),
                        'title': item.get('trackName', 'Unknown Title'),
                        'artist': item.get('artistName', 'Unknown Artist'),
                        'album': item.get('collectionName', 'Unknown Album'),
                        'duration_ms': item.get('trackTimeMillis', 0),
                        'artwork_url': artwork_url,
                        'source_platform': 'apple',
                        'type': 'song'
                    })
            return results
        except Exception as e:
            print(f"iTunes API Error: {e}")
            return []
            
    def lookup_artist_albums(self, artist_id):
        """ Fetch all albums/singles for an artist """
        try:
            params = {'id': artist_id, 'entity': 'album'}
            response = requests.get('https://itunes.apple.com/lookup', params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get('results', []):
                if item.get('wrapperType') == 'collection':
                    artwork_url = item.get('artworkUrl100', '')
                    if artwork_url: artwork_url = artwork_url.replace('100x100bb', '300x300bb')
                    results.append({
                        'id': item.get('collectionId'),
                        'title': item.get('collectionName', 'Unknown Album'),
                        'artist': item.get('artistName', 'Unknown Artist'),
                        'artwork_url': artwork_url,
                        'type': 'album',
                        'source_platform': 'apple'
                    })
            return results
        except Exception as e:
            print(f"iTunes API Artist Lookup Error: {e}")
            return []

    def get_album_tracks(self, collection_id):
        """ Fetch all tracks for a specific album """
        try:
            params = {'id': collection_id, 'entity': 'song'}
            response = requests.get('https://itunes.apple.com/lookup', params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get('results', []):
                if item.get('wrapperType') == 'track':
                    artwork_url = item.get('artworkUrl100', '')
                    if artwork_url: artwork_url = artwork_url.replace('100x100bb', '300x300bb')
                    results.append({
                        'id': item.get('trackId'),
                        'title': item.get('trackName', 'Unknown Title'),
                        'artist': item.get('artistName', 'Unknown Artist'),
                        'album': item.get('collectionName', 'Unknown Album'),
                        'duration_ms': item.get('trackTimeMillis', 0),
                        'artwork_url': artwork_url,
                        'source_platform': 'apple',
                        'type': 'song'
                    })
            return results
        except Exception as e:
            print(f"iTunes API Album Tracks Lookup Error: {e}")
            return []

    def get_related_tracks(self, artist_name, limit=5):
        """
        Fetch top tracks for a specific artist to use as endless autoplay queue.
        """
        try:
            params = {
                'term': artist_name,
                'entity': 'song',
                'limit': limit * 2, # Fetch more to allow shuffling or skipping exact matches
                'sort': 'recent'
            }
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('results', []):
                artwork_url = item.get('artworkUrl100', '')
                if artwork_url:
                    artwork_url = artwork_url.replace('100x100bb', '300x300bb')
                    
                results.append({
                    'id': item.get('trackId'),
                    'title': item.get('trackName', 'Unknown Title'),
                    'artist': item.get('artistName', 'Unknown Artist'),
                    'album': item.get('collectionName', 'Unknown Album'),
                    'duration_ms': item.get('trackTimeMillis', 0),
                    'artwork_url': artwork_url,
                })
            return results
        except Exception as e:
            print(f"iTunes API Related Error: {e}")
            return []
