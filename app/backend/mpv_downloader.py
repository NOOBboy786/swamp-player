import os
import urllib.request
import json
import subprocess
import shutil

def get_latest_mpv_url():
    api_url = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            # Find the actual mpv package, NOT ffmpeg
            # We specifically avoid -v3 because it requires AVX2 and crashes on older CPUs
            for asset in data.get('assets', []):
                name = asset['name'].lower()
                if name.startswith('mpv-') and 'x86_64' in name and '-v3' not in name and name.endswith('.7z') and 'dev' not in name and 'debug' not in name:
                    return asset['browser_download_url']
    except Exception as e:
        print(f"Error getting latest mpv url: {e}")
    return None

def ensure_mpv_installed(base_dir):
    bin_dir = os.path.join(base_dir, "app", "bin", "mpv")
    mpv_exe = os.path.join(bin_dir, "mpv.exe")
    
    if os.path.exists(mpv_exe):
        return True
        
    print("mpv.exe not found. Downloading...")
    os.makedirs(bin_dir, exist_ok=True)
    
    url = get_latest_mpv_url()
    if not url:
        print("Failed to find mpv download url. Please download manually.")
        return False
        
    archive_path = os.path.join(bin_dir, "mpv.7z")
    extractor_path = os.path.join(bin_dir, "7zr.exe")
    
    # Download 7zr.exe
    try:
        req_7z = urllib.request.Request("https://www.7-zip.org/a/7zr.exe", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_7z) as response, open(extractor_path, 'wb') as out_file:
            out_file.write(response.read())
    except Exception as e:
        print(f"Failed to download 7zr.exe: {e}")
        return False
        
    print(f"Downloading mpv from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(archive_path, 'wb') as out_file:
            out_file.write(response.read())
            
        print("Extracting mpv using 7zr.exe...")
        subprocess.run([extractor_path, "x", archive_path, f"-o{bin_dir}", "-y"], check=True)
        
        extracted_mpv = None
        for root, dirs, files in os.walk(bin_dir):
            if "mpv.exe" in files:
                extracted_mpv = os.path.join(root, "mpv.exe")
                break
                
        if extracted_mpv and extracted_mpv != mpv_exe:
            shutil.move(extracted_mpv, mpv_exe)
            
    except Exception as e:
        print(f"Extraction error: {e}")
        return False
    finally:
        # Clean up archive and extractor
        if os.path.exists(archive_path):
            os.remove(archive_path)
        if os.path.exists(extractor_path):
            try:
                os.remove(extractor_path)
            except:
                pass
        
    print("mpv installed successfully.")
    return True
