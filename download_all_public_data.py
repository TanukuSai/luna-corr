#!/usr/bin/env python3
"""
Downloads public LRO NAC reference images and LOLA DEM datasets,
and prepares candidate scenes in ./imgs for lunacorr_bench_g0.py.
"""
import os
import sys
import urllib.request
from pathlib import Path
import cv2
import numpy as np

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_FILES = [
    # LRO NAC reference images from NASA Photojournal / Planetary Data
    {
        "url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia19/pia19913/PIA19913.jpg",
        "dest": Path("data/lro_nac/tycho_crater_lroc_nac.jpg"),
        "name": "Tycho Crater (LROC NAC)",
        "tag": "scene_tycho"
    },
    {
        "url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia13/pia13518/PIA13518.jpg",
        "dest": Path("data/lro_nac/shackleton_south_pole_lroc_nac.jpg"),
        "name": "Shackleton Crater / South Pole (LROC NAC)",
        "tag": "scene_shackleton"
    },
    {
        "url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia14/pia14021/PIA14021.jpg",
        "dest": Path("data/lro_nac/apollo17_taurus_littrow_lroc_nac.jpg"),
        "name": "Apollo 17 Taurus-Littrow Valley (LROC NAC)",
        "tag": "scene_apollo17"
    },
    {
        "url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia12/pia12954/PIA12954.jpg",
        "dest": Path("data/lro_nac/marius_hills_pit_lroc_nac.jpg"),
        "name": "Marius Hills Pit (LROC NAC)",
        "tag": "scene_marius_hills"
    },
    {
        "url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia16/pia16624/PIA16624.jpg",
        "dest": Path("data/lro_nac/change3_landing_site_lroc_nac.jpg"),
        "name": "Chang'e 3 Landing Site (LROC NAC)",
        "tag": "scene_change3"
    },
    # LOLA Topography DEM from Washington University PDS Geosciences
    {
        "url": "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldac_50s_1000m.jp2",
        "dest": Path("data/dem/ldac_50s_1000m.jp2"),
        "name": "LOLA South Pole DEM (1000m Polar Stereographic)",
        "tag": None
    },
    {
        "url": "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldac_50s_1000m_aux.xml",
        "dest": Path("data/dem/ldac_50s_1000m_aux.xml"),
        "name": "LOLA South Pole DEM Auxiliary XML",
        "tag": None
    },
    {
        "url": "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldac_50s_1000m_jp2.lbl",
        "dest": Path("data/dem/ldac_50s_1000m_jp2.lbl"),
        "name": "LOLA South Pole DEM PDS Label",
        "tag": None
    }
]

def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[SKIP] {dest.name} already exists ({dest.stat().st_size / 1024 / 1024:.2f} MB)")
        return
    print(f"[DOWNLOADING] {dest.name} from {url}...")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, 'wb') as f:
        total = resp.length
        dl = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            dl += len(chunk)
            if total:
                pct = dl / total * 100
                print(f"  {dl/1024/1024:.1f}/{total/1024/1024:.1f} MB ({pct:.1f}%)", end='\r')
        print(f"\n[DONE] {dest.name} ({dl/1024/1024:.2f} MB)")

def prepare_g0_scenes():
    imgs_dir = Path("imgs")
    imgs_dir.mkdir(parents=True, exist_ok=True)
    print("\nPreparing 1024x1024 scene tiles for lunacorr_bench_g0.py in ./imgs ...")

    for item in TARGET_FILES:
        tag = item.get("tag")
        if not tag:
            continue
        src_path = item["dest"]
        if not src_path.exists():
            continue

        im = cv2.imread(str(src_path), cv2.IMREAD_GRAYSCALE)
        if im is None:
            print(f"Warning: Could not read {src_path} as image")
            continue

        h, w = im.shape
        print(f"Processing {item['name']}: {w}x{h}")
        
        # Extract candidate 1024x1024 crops
        crops = []
        if h >= 1024 and w >= 1024:
            # Center crop
            cy, cx = h // 2, w // 2
            crops.append(("center", im[cy - 512:cy + 512, cx - 512:cx + 512]))
            
            # Alternative quadrant crop if image is large enough
            if h >= 2048 and w >= 2048:
                crops.append(("feature_b", im[h//4:h//4 + 1024, w//4:w//4 + 1024]))
        else:
            # Resize if smaller
            s = 1024 / min(h, w)
            resized = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
            crops.append(("scaled", resized[:1024, :1024]))

        for crop_suffix, crop_img in crops:
            out_file = imgs_dir / f"{tag}_{crop_suffix}.png"
            cv2.imwrite(str(out_file), crop_img)
            print(f"  Saved scene tile: {out_file} (1024x1024, std={crop_img.std():.1f})")

if __name__ == "__main__":
    print("=== Downloading Public Reference Imagery & DEMs ===")
    for item in TARGET_FILES:
        try:
            download(item["url"], item["dest"])
        except Exception as e:
            print(f"[ERROR] Failed to download {item['dest'].name}: {e}")
            
    prepare_g0_scenes()
    print("\n=== Public Dataset Download Complete ===")
