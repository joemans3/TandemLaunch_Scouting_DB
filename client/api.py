import requests

from .settings import get_server_url


def download_people_csv() -> bytes:
    response = requests.get(get_server_url() + "/people/export_csv")
    response.raise_for_status()
    return response.content


def ping_server():
    try:
        response = requests.get(get_server_url() + "/ping", timeout=2)
        response.raise_for_status()
        return True
    except Exception:
        return False


def create_person(data: dict):
    """Submit a new person to the backend."""
    response = requests.post(get_server_url() + "/people/", json=data)
    response.raise_for_status()
    return response.json()


def update_person(person_id: int, data: dict):
    """Send partial update to existing person entry."""
    response = requests.patch(f"{get_server_url()}/people/{person_id}", json=data)
    response.raise_for_status()
    return response.json()


def list_people(
    query: str = "",
    role: str = "",
    country: str = "",
    subfield: str = "",
    offset: int = 0,
    limit: int = 100,
):
    """Search/filter people."""
    params = {"offset": offset, "limit": limit}
    if query:
        params["q"] = query
    if role:
        params["role"] = role
    if country:
        params["country"] = country
    if subfield:
        params["subfield"] = subfield
    response = requests.get(get_server_url() + "/people/", params=params)
    response.raise_for_status()
    return response.json()


def delete_person(person_id: int):
    response = requests.delete(get_server_url() + f"/people/{person_id}")
    response.raise_for_status()
    return response.json()


def list_universities():
    """Return all canonical universities."""
    response = requests.get(get_server_url() + "/universities/")
    response.raise_for_status()
    return response.json()


def list_countries():
    """Return all countries."""
    response = requests.get(get_server_url() + "/countries/")
    response.raise_for_status()
    return response.json()


def create_university_alias(alias: str, canonical_name: str):
    """Submit a new university alias."""
    payload = {"alias": alias, "canonical_name": canonical_name}
    response = requests.post(
        get_server_url() + "/universities/aliases/", params=payload
    )
    response.raise_for_status()
    return response.json()
