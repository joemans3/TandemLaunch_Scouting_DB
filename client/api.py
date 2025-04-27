from pathlib import Path

import requests
import tomli
from platformdirs import user_config_dir

from .settings import get_server_url

APP_NAME = "scouting-database"
SETTINGS_FILE = Path(user_config_dir(APP_NAME)) / "settings.toml"


def load_settings():
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "rb") as f:
            return tomli.load(f)
    else:
        # fallback defaults
        return {"server": {"host": "127.0.0.1", "port": 8000}}


def get_base_url():
    settings = load_settings()
    host = settings["server"]["host"]
    port = settings["server"]["port"]
    return f"http://{host}:{port}"


def ping_server():
    try:
        response = requests.get(get_base_url() + "/ping", timeout=2)
        response.raise_for_status()
        return True
    except Exception:
        return False


def create_catalog_entry(data: dict):
    response = requests.post(get_base_url() + "/catalog/", json=data)
    response.raise_for_status()
    return response.json()


def search_catalog_entries(query: str = "", offset: int = 0, limit: int = 100):
    params = {"offset": offset, "limit": limit}
    if query:
        params["q"] = query
    response = requests.get(get_base_url() + "/catalog/", params=params)
    response.raise_for_status()
    return response.json()


def update_catalog_entry(entry_id: int, data: dict):
    response = requests.post(get_server_url() + "/catalog/", json=data)
    response.raise_for_status()
    return response.json()


def delete_catalog_entry(entry_id: int):
    response = requests.delete(get_base_url() + f"/catalog/{entry_id}")
    response.raise_for_status()
    return response.json()
