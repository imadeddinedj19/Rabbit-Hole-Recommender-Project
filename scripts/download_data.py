"""Download the KuaiRec dataset into data/raw/.

Usage (from the repo root):
    python scripts/download_data.py

The zip is several hundred MB, so this can take a few minutes.
Source: https://zenodo.org/records/18164998 (official host, see the KuaiRec GitHub page).
"""

import urllib.request
import zipfile
from pathlib import Path

URL = "https://zenodo.org/records/18164998/files/KuaiRec.zip?download=1"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ZIP_PATH = RAW_DIR / "KuaiRec.zip"


def show_progress(blocks, block_size, total_size):
    if total_size > 0:
        done = min(blocks * block_size, total_size)
        print(f"\r  {done / 1e6:,.0f} / {total_size / 1e6:,.0f} MB", end="")


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not ZIP_PATH.exists():
        print(f"Downloading {URL}")
        urllib.request.urlretrieve(URL, ZIP_PATH, reporthook=show_progress)
        print()
    else:
        print(f"{ZIP_PATH.name} already downloaded, skipping.")

    print("Unzipping...")
    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extractall(RAW_DIR)

    print("Done. CSV files found:")
    for csv in sorted(RAW_DIR.rglob("*.csv")):
        print(f"  {csv.relative_to(RAW_DIR)}  ({csv.stat().st_size / 1e6:,.0f} MB)")


if __name__ == "__main__":
    main()
