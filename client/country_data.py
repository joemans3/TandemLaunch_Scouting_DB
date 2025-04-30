import pycountry


def get_all_country_names() -> list[str]:
    return sorted(country.name for country in pycountry.countries)
