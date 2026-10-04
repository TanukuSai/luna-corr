#!/usr/bin/env python3

"""
PRADAN Data Download Script

Prerequisites:
* Log in to PRADAN using your web browser.
* Select the required data products (Data order and indexes are meaningful only when same filters and sort order is applied [default are also good]. Indexes may get updated with more data released on PRADAN).
* Download the generated script for the current session.
* Run the script (do not logout the browser session).

Notes:
- Preserves the PRADAN directory structure.
- Resumes interrupted downloads.
- Skips files already downloaded. (Delete the file manually if you want to force re-download or run script in a new directory.)

Caution:
* Session download limits, request rate limits, and session timeouts
  are in effect.
* Excessive automated requests may result in temporary blocking.
* Use this script to simplify manual downloads, but do not overload
  the server.
"""

import requests
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

# =====================================================

# CONFIGURATION

# =====================================================

MAX_RETRIES = 5
RETRY_WAIT_SECONDS = 30
CHUNK_SIZE_MB = 8

url_prefix = "https://pradan.issdc.gov.in"

# =====================================================

# COOKIES

# =====================================================

cookie_string = "FGTServer=5DB1E9B68132028CF7976EE4DF4CBB47C2F908C978D8DADB79380837E680FA20672DD56B0798AF391BF6;primefaces.download=null;JSESSIONID=5b99b4eef0a0c58609e7c285bd2e;FGTServer=5DB1E9B68132028CF7976EE4DF4CBB47C2F908C978D8DADB79380837E680FA20672DD56B0798AF391BF6;OAuth_Token_Request_State=5de6747e-3cf9-4edf-ab33-8b03744fe213;" 

headers = {
"Cookie": cookie_string
}

# =====================================================

# FILE LIST

# =====================================================

data_file_paths = ["/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260717/ch2_iir_nci_20260717T1140497770_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260717/ch2_iir_nci_20260717T0744556649_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260715/ch2_iir_nci_20260715T2015031271_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260715/ch2_iir_nci_20260715T2020241878_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260715/ch2_iir_nci_20260715T0819249465_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260715/ch2_iir_nci_20260715T0357586126_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260714/ch2_iir_nci_20260714T1828081875_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260714/ch2_iir_nci_20260714T1032069302_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260714/ch2_iir_nci_20260714T0435041330_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260714/ch2_iir_nci_20260714T0236048632_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260713/ch2_iir_nci_20260713T0226085025_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260712/ch2_iir_nci_20260712T1655234840_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260712/ch2_iir_nci_20260712T0632554384_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260712/ch2_iir_nci_20260712T1653096655_d_img_d18.zip?iirs", "/ch2/protected/downloadData/POST_OD/isda_archive/ch2_bundle/cho_bundle/nop/iir_collection/data/calibrated/20260711/ch2_iir_nci_20260711T0051009140_d_img_d18.zip?iirs", ] 

# =====================================================

# BASE URL

# =====================================================

host_name = urlparse(url_prefix).netloc

# =====================================================

# DOWNLOAD ROOT

# Uses current working directory

# =====================================================

base_dir = Path.cwd()

# =====================================================

# SESSION

# =====================================================

session = requests.Session()

# =====================================================

# STARTUP BANNER

# =====================================================

print("\nPRADAN Bulk Download Utility")
print("-" * 50)
print(f"Download root    : {base_dir / host_name}")
print("Completed files  : skipped (Delete the file manually if you want to force re-download or run script in a new directory.)")
print("Partial files    : resumed")
print("Keep-alive       : enabled")
print("-" * 50)

# =====================================================

# KEEP ALIVE THREAD

# =====================================================


def keep_alive():
    keep_alive_url = (
        url_prefix +
        "/ch2/protected/payload.xhtml"
    )

    for _ in range(144):  # 24 hours

        time.sleep(600)  # 10 minutes

        try:
            session.get(
                keep_alive_url,
                headers=headers,
                timeout=(30, 60)
            )

        except Exception as e:
            print(
                f"\n[KEEP-ALIVE ERROR] {e}"
            )

threading.Thread(
target=keep_alive,
daemon=True
).start()

# =====================================================

# DOWNLOAD LOOP

# =====================================================

download_count = 0

for file_index, file_path in enumerate(data_file_paths, start=1):

    url = url_prefix + file_path

    clean_path = file_path.split("?")[0]
    relative_path = clean_path.lstrip("/")

    final_file = (
        base_dir /
        host_name /
        relative_path
    )

    partial_file = Path(
        str(final_file) + ".part"
    )

    final_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\n==================================================")
    print(f"File {file_index}/{len(data_file_paths)}")
    print(url)

    # -------------------------------------------------
    # Skip already completed downloads
    # -------------------------------------------------

    if final_file.exists():

        print(
        "Already downloaded. Skipping."
        )

        download_count += 1
        continue

    # -------------------------------------------------
    # Download with retries
    # -------------------------------------------------

    success = False

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            resume_from = 0

            request_headers = headers.copy()

            if partial_file.exists():

                resume_from = (
                    partial_file.stat().st_size
                )

                request_headers[
                    "Range"
                ] = (
                    f"bytes={resume_from}-"
                )

                print(
                    f"Resuming from "
                    f"{resume_from:,} bytes"
                )

            else:

                print(
                    "Starting fresh download"
                )

            with session.get(
                url,
                headers=request_headers,
                stream=True,
                timeout=(30, 600),
                allow_redirects=False
            ) as response:

                if response.status_code not in (
                    200,
                    206
                ):
                    raise RuntimeError(
                        f"HTTP "
                        f"{response.status_code}"
                    )

                mode = (
                    "ab"
                    if resume_from > 0
                    else "wb"
                )

                downloaded = resume_from

                with open(
                    partial_file,
                    mode
                ) as f:

                    for chunk in response.iter_content(
                        chunk_size=
                        CHUNK_SIZE_MB
                        * 1024
                        * 1024
                    ):

                        if not chunk:
                            continue

                        f.write(chunk)

                        downloaded += len(chunk)

                        print(
                            f"\rDownloaded: "
                            f"{downloaded/(1024**2):.3f} MB",
                            end="",
                            flush=True
                        )

            print()

            partial_file.rename(
                final_file
            )

            size_mb = (
                final_file.stat().st_size
                / (1024 ** 2)
            )

            print(
                f"Completed "
                f"({size_mb:.4f} MB)"
            )

            download_count += 1
            success = True

            break

        except Exception as e:

            print()
            print(
                f"Attempt "
                f"{attempt}/{MAX_RETRIES} "
                f"failed: {e}"
            )

            if attempt < MAX_RETRIES:

                print(
                    f"Retrying in "
                    f"{RETRY_WAIT_SECONDS} "
                    f"seconds..."
                )

                time.sleep(
                    RETRY_WAIT_SECONDS
                )

    if not success:

        print()
        print(
        "Error: Network failure, "
        "limits reached, or "
        "session expired."
        )

        print()
        print(
        f"Last file being "
        f"processed "
        f"({file_index}):"
        )

        print(clean_path)

        print()
        print("You may login again later to download script for the new session and resume downloads.")

        raise SystemExit(1)

# =====================================================

# COMPLETION SUMMARY

# =====================================================

print()
print(
f"Your downloads "
f"({download_count}) "
f"are complete."
)

print()
print(
"Downloaded files are "
"available under:"
)

print(base_dir / host_name)
