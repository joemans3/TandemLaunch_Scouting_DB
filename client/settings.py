from pathlib import Path

import tomli
import tomli_w
from platformdirs import user_config_dir

APP_NAME = "scouting-database"
SETTINGS_FILE = Path(user_config_dir(APP_NAME)) / "settings.toml"

DEFAULT_SETTINGS = {
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
    }
}


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
    with open(SETTINGS_FILE, "rb") as f:
        return tomli.load(f)


def save_settings(settings: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "wb") as f:
        tomli_w.dump(settings, f)


def get_server_url() -> str:
    settings = load_settings()
    host = settings["server"]["host"]
    port = settings["server"]["port"]
    return f"http://{host}:{port}"
