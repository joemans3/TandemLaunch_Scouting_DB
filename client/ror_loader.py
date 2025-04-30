import json
import zipfile
from pathlib import Path

import requests

APP_NAME = "scouting-database"
DATA_DIR = Path.home() / APP_NAME
ROR_ZIP_PATH = DATA_DIR / "ror_dump.zip"
ROR_NAMES_PATH = DATA_DIR / "university_names.json"

ROR_URL = (
    "https://zenodo.org/records/15298417/files/v1.64-2025-04-28-ror-data.zip?download=1"
)


def ensure_ror_data(status_cb=None):
    def update(msg):
        if status_cb:
            status_cb(msg)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if ROR_NAMES_PATH.exists():
        update("University data already prepared.")
        return

    if not ROR_ZIP_PATH.exists():
        update("Downloading ROR ZIP data...")
        response = requests.get(ROR_URL, timeout=30)
        response.raise_for_status()
        with open(ROR_ZIP_PATH, "wb") as f:
            f.write(response.content)

    update("Extracting university list...")
    with zipfile.ZipFile(ROR_ZIP_PATH, "r") as zipf:
        json_name = next(
            (name for name in zipf.namelist() if "schema_v2.json" in name), None
        )
        if not json_name:
            raise RuntimeError("Expected JSON file not found in ROR zip.")

        with zipf.open(json_name) as json_file:
            records = json.load(json_file)

    update("Parsing university names...")
    names = []
    for record in records:
        for name_entry in record.get("names", []):
            if "ror_display" in name_entry.get("types", []):
                names.append(name_entry["value"])
                break

    with open(ROR_NAMES_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(set(names)), f, indent=2)

    update(f"{len(names)} university names saved.")

    if ROR_ZIP_PATH.exists():
        ROR_ZIP_PATH.unlink()
        update("Cleaned up ROR ZIP file.")


def load_university_names() -> list[str]:
    if not ROR_NAMES_PATH.exists():
        raise RuntimeError("ROR university names not downloaded yet.")
    with open(ROR_NAMES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
