import json
from pathlib import Path

import requests

ROR_URL = "https://zenodo.org/record/15298417/files/ror-data-v2.0.json?download=1"
ROR_LOCAL_PATH = Path("data/ror_dump.json")


def load_university_names() -> list[str]:
    if not ROR_LOCAL_PATH.exists():
        raise FileNotFoundError(
            "ROR dump not found. Make sure `ensure_ror_data()` is called."
        )

    with open(ROR_LOCAL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    names = []
    for record in data:
        for name_entry in record.get("names", []):
            if "ror_display" in name_entry.get("types", []):
                names.append(name_entry["value"])
                break  # use first preferred name
    return sorted(set(names))


def ensure_ror_data():
    ROR_LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ROR_LOCAL_PATH.exists():
        print("[✅] ROR data found.")
        return

    print("[⬇️] Downloading ROR data from Zenodo...")
    try:
        response = requests.get(ROR_URL, timeout=20)
        response.raise_for_status()
        with open(ROR_LOCAL_PATH, "wb") as f:
            f.write(response.content)
        print("[✅] ROR data downloaded and saved.")
    except Exception as e:
        print(f"[❌] Failed to download ROR data: {e}")
