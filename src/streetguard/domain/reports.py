from uuid import UUID, uuid4

from streetguard.domain.geography import LocationSource


def create_public_report_id(country_code: str | None) -> str:
    prefix = country_code.upper() if country_code and len(country_code) == 2 else "GLOBAL"
    return f"SG-{prefix}-{uuid4().hex[:20].upper()}"


def country_code_from_metadata(metadata: object) -> str | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("country_code")
    if isinstance(value, str) and len(value) == 2 and value.isalpha():
        return value.upper()
    return None


def capture_source_label(source: str) -> LocationSource:
    allowed = {
        "exif",
        "device_gps",
        "map_pin",
        "manual_coordinates",
        "geocoder",
    }
    if source not in allowed:
        raise ValueError("Unknown location provenance source")
    return source  # type: ignore[return-value]


def owns_report(reporter_id: UUID | None, user_id: UUID | None) -> bool:
    return reporter_id is not None and user_id is not None and reporter_id == user_id
