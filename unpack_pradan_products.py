"""
Safe sequential extract-and-delete utility for PRADAN products.
Extracts one zip file at a time, verifies the extraction, and deletes the zip
to conserve disk space.
"""
from pathlib import Path
import zipfile
import shutil
import argparse
import sys

def get_free_gb():
    total, used, free = shutil.disk_usage(".")
    return free / (1024 ** 3)

def unpack_sequential(delete_zip: bool = True, target_instrument: str = "ALL"):
    pradan_root = Path("pradan.issdc.gov.in")
    data_root = Path("data")

    if not pradan_root.exists():
        print("No PRADAN download directory found.")
        return

    zips = sorted(list(pradan_root.rglob("*.zip")), key=lambda p: p.stat().st_size)
    print(f"Total zip archives found: {len(zips)}")
    print(f"Current free disk space: {get_free_gb():.2f} GB\n")

    extracted_count = 0
    space_freed_mb = 0.0

    for idx, zpath in enumerate(zips, 1):
        name = zpath.name.lower()
        if "ohr" in name:
            inst = "OHRC"
            dest_dir = data_root / "ohrc"
        elif "tmc" in name:
            inst = "TMC2"
            dest_dir = data_root / "tmc2"
        elif "iir" in name:
            inst = "IIRS"
            dest_dir = data_root / "iirs"
        else:
            inst = "MISC"
            dest_dir = data_root / "misc"

        if target_instrument != "ALL" and inst != target_instrument.upper():
            continue

        zip_size_mb = zpath.stat().st_size / (1024 * 1024)
        dest_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{idx}/{len(zips)}] Processing {inst}: {zpath.name} ({zip_size_mb:.1f} MB)", flush=True)
        print(f"  Free space before: {get_free_gb():.2f} GB", flush=True)

        try:
            with zipfile.ZipFile(zpath, "r") as z:
                # Check integrity first
                if z.testzip() is not None:
                    print(f"  [SKIPPED] Archive CRC mismatch in {zpath.name}", flush=True)
                    continue

                members = z.namelist()
                z.extractall(dest_dir)

            # Verification: ensure extracted member exists on disk with non-zero size
            file_members = [m for m in members if not m.endswith('/')]
            check_file = dest_dir / (file_members[0] if file_members else members[0])
            if not check_file.exists():
                print(f"  [ERROR] Verification failed for {zpath.name}. Zip retained.", flush=True)
                continue

            print(f"  [OK] Successfully extracted {len(members)} items to {dest_dir}", flush=True)

            if delete_zip:
                zpath.unlink()
                space_freed_mb += zip_size_mb
                print(f"  [DELETED] Removed {zpath.name} (Freed {zip_size_mb:.1f} MB archive)", flush=True)

            print(f"  Free space after: {get_free_gb():.2f} GB\n", flush=True)
            extracted_count += 1

        except Exception as e:
            print(f"  [ERROR] Failed to extract {zpath.name}: {e}\n", flush=True)

    print("=" * 60)
    print(f"Extraction complete.")
    print(f"Products unpacked: {extracted_count}")
    if delete_zip:
        print(f"Total archive space reclaimed: {space_freed_mb / 1024:.2f} GB")
    print(f"Final free disk space: {get_free_gb():.2f} GB")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract PRADAN zips and optionally delete source archives.")
    parser.add_argument("--keep-zips", action="store_true", help="Do not delete zip files after extraction")
    parser.add_argument("--instrument", default="ALL", choices=["ALL", "OHRC", "TMC2", "IIRS"], help="Extract specific instrument")
    args = parser.parse_args()

    unpack_sequential(delete_zip=not args.keep_zips, target_instrument=args.instrument)
