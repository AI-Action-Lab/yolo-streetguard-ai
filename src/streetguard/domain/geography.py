from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LocationSource = Literal[
    "exif",
    "device_gps",
    "map_pin",
    "manual_coordinates",
    "geocoder",
]


class CountryOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    alpha3: str
    name: str
    official_name: str | None = None


class SubdivisionOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    type: str
    parent_code: str | None = None


class AddressComponents(BaseModel):
    model_config = ConfigDict(frozen=True)

    country: str | None = None
    country_code: str | None = None
    state_province: str | None = None
    district: str | None = None
    city: str | None = None
    locality: str | None = None
    postal_code: str | None = None
    road: str | None = None


class GeocodingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    formatted_address: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    place_id: str | None = None
    components: AddressComponents
    provider: Literal["google"] = "google"
