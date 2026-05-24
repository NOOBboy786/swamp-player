import requests

params = {'id': '325692257', 'entity': 'song'} # Example trackId
response = requests.get('https://itunes.apple.com/lookup', params=params, timeout=5)
data = response.json()
print("Total results:", data['resultCount'])
for item in data['results']:
    print(item.get('wrapperType'), item.get('kind'), item.get('trackName'))
