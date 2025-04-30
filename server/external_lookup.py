import requests


def lookup_country_by_name(name: str) -> tuple[str, str] | None:
    """Lookup ISO country info using REST Countries API."""
    try:
        response = requests.get(f"https://restcountries.com/v3.1/name/{name}")
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        match = data[0]
        return match["name"]["common"], match["cca2"]
    except Exception:
        return None


def lookup_ror_for_university(query: str) -> tuple[str, str, list[str]] | None:
    """Lookup ROR info for a university by name or alias."""
    try:
        url = f"https://api.ror.org/organizations?query={query}"
        response = requests.get(url)
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            return None
        item = items[0]
        name = item["name"]
        ror_id = item["id"]
        aliases = item.get("aliases", [])
        return name, ror_id, aliases
    except Exception:
        return None
