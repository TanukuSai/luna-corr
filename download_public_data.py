import os
import re
import urllib.request
from pathlib import Path

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def download_file(url, dest_path):
    print(f"Downloading: {url} -> {dest_path}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_path, 'wb') as f:
        total_size = resp.length
        downloaded = 0
        while True:
            chunk = resp.read(1024 * 1024) # 1MB
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                pct = downloaded / total_size * 100
                print(f"  {downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB ({pct:.1f}%)", end='\r')
        print(f"\nDone: {dest_path} ({downloaded / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    url = 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
            print("polar jp2 files:", [l for l in links if not l.startswith('?')][:20])
    except Exception as e:
        print("Error:", e)














