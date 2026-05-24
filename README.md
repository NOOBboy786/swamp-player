# Swamp Player

A retro-styled desktop music player with a Winamp aesthetic. Swamp Player supports local history, playlists, and online streaming.

## Features
- **Online Audio Streaming:** Instantly stream audio directly.
- **Rich Metadata:** Automatically fetches high-quality album art and track information.
- **Winamp Aesthetic:** Classic, nostalgic green-on-black interface with a 1:1 aspect ratio album art display.
- **Portable:** Automatically downloads the required `mpv.exe` binary on first run, requiring no external setup.

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
