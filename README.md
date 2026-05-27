# Swamp Player (W.I.P)

A retro-styled desktop music player with a Winamp aesthetic.(vibecoded) Swamp Player supports local history, playlists, and online streaming.

## Features
- **Online Audio Streaming:** Instantly stream audio directly.
- **Rich Metadata:** Automatically fetches high-quality album art and track information.
- **Winamp Aesthetic:** Classic, nostalgic green-on-black interface with a 1:1 aspect ratio album art display.
- **Portable:** Automatically downloads the required `mpv.exe` binary on first run, requiring no external setup.
- **playlists:** You can drag and drop links and it will show the playlist content in a nutshell import online playlist

## Features that dont work yet
- ~~**album** still doesnt work~~ works on the latest version :D
- **playback** can automatically stop sometimes
- ~~**autoplay** can bug out or crash the app fully~~ buggy but doesnt crash :DDD
- **pin function** is bugged and im too lazy to fix

## Features that i wanna add
- **more optimization** sudden spikes in cpu and mem usage

## How to Compile / Run from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/NOOBboy786/swamp-player.git
   cd swamp-player
   ```

2. **Create a Virtual Environment & Install Dependencies:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the App Directly (for development):**
   ```bash
   python main.py
   ```

4. **Compile into a standalone executable (Windows):**
   ```bash
   pyinstaller --noconfirm --onefile --windowed --icon "app/assets/icon.ico" --add-data "app/assets;app/assets" --version-file version_info.txt main.py
   ```
   *Once finished, the standalone file will be available in the `dist` folder as `main.exe`.*


   <img width="1246" height="625" alt="{DF56E715-D4A2-497D-A6E4-65EA6FDFE3D5}" src="https://github.com/user-attachments/assets/9769c029-cb28-4616-b709-3a69eca1087a" />

