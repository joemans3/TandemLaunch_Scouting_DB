from pathlib import Path

import requests
import tomli

# Load settings
SETTINGS_FILE = Path(__file__).parent.parent / "settings.toml"

with open(SETTINGS_FILE, "rb") as f:
    settings = tomli.load(f)

SERVER_HOST = settings["server"]["host"]
SERVER_PORT = settings["server"]["port"]

BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


def search_catalog(query: str):
    try:
        response = requests.get(f"{BASE_URL}/search/", params={"q": query})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error contacting server: {e}")
        return []


def add_university(name: str):
    try:
        response = requests.post(f"{BASE_URL}/universities/", json={"name": name})
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def add_department(name: str, university_id: int):
    try:
        response = requests.post(
            f"{BASE_URL}/departments/",
            json={"name": name, "university_id": university_id},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def add_department_head(name: str, email: str, department_id: int, university_id: int):
    try:
        response = requests.post(
            f"{BASE_URL}/department_heads/",
            json={
                "name": name,
                "email": email,
                "department_id": department_id,
                "university_id": university_id,
            },
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def add_admin(name: str, email: str, department_id: int, university_id: int):
    try:
        response = requests.post(
            f"{BASE_URL}/admins/",
            json={
                "name": name,
                "email": email,
                "department_id": department_id,
                "university_id": university_id,
            },
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def delete_department_head(head_id: int):
    try:
        response = requests.delete(f"{BASE_URL}/department_heads/{head_id}")
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def delete_admin(admin_id: int):
    try:
        response = requests.delete(f"{BASE_URL}/admins/{admin_id}")
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def update_university(university_id: int, new_name: str):
    try:
        response = requests.patch(
            f"{BASE_URL}/universities/{university_id}", json={"name": new_name}
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def update_department(department_id: int, new_name: str):
    try:
        response = requests.patch(
            f"{BASE_URL}/departments/{department_id}", json={"name": new_name}
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def update_department_head(head_id: int, new_name: str, new_email: str):
    try:
        response = requests.patch(
            f"{BASE_URL}/department_heads/{head_id}",
            json={"name": new_name, "email": new_email},
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def update_admin(admin_id: int, new_name: str, new_email: str):
    try:
        response = requests.patch(
            f"{BASE_URL}/admins/{admin_id}", json={"name": new_name, "email": new_email}
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def ping_server():
    try:
        response = requests.get(f"{BASE_URL}/ping", timeout=1.0)  # 1 second timeout
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False
