import pycountry

from streetguard.domain.geography import CountryOption, SubdivisionOption


def countries() -> list[CountryOption]:
    values = []
    for country in pycountry.countries:
        values.append(
            CountryOption(
                code=country.alpha_2,
                alpha3=country.alpha_3,
                name=country.name,
                official_name=getattr(country, "official_name", None),
            )
        )
    return sorted(values, key=lambda item: item.name)


def subdivisions(country_code: str) -> list[SubdivisionOption]:
    normalized = country_code.upper()
    if len(normalized) != 2 or pycountry.countries.get(alpha_2=normalized) is None:
        return []
    values = []
    for subdivision in pycountry.subdivisions.get(  # type: ignore[no-untyped-call]
        country_code=normalized
    ):
        values.append(
            SubdivisionOption(
                code=subdivision.code,
                name=subdivision.name,
                type=subdivision.type,
                parent_code=getattr(subdivision, "parent_code", None),
            )
        )
    return sorted(values, key=lambda item: item.name)
