from __future__ import annotations

import io
from datetime import datetime
from typing import Any, cast

from PIL import ExifTags, Image, UnidentifiedImageError

from streetguard.domain.detections import GpsCoordinates, ImageMetadata

SUPPORTED_IMAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}
)


class ImageValidationError(ValueError):
    pass


def _ratio_to_float(value: object) -> float:
    try:
        return float(cast(float, value))
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ImageValidationError("Invalid EXIF rational value") from exc


def _degrees(values: tuple[object, object, object]) -> float:
    return (
        _ratio_to_float(values[0])
        + _ratio_to_float(values[1]) / 60
        + _ratio_to_float(values[2]) / 3600
    )


def extract_gps(gps_raw: Any) -> GpsCoordinates | None:
    if not isinstance(gps_raw, dict):
        return None

    latitude_ref = gps_raw.get(ExifTags.GPS.GPSLatitudeRef)
    longitude_ref = gps_raw.get(ExifTags.GPS.GPSLongitudeRef)
    latitude_values = gps_raw.get(ExifTags.GPS.GPSLatitude)
    longitude_values = gps_raw.get(ExifTags.GPS.GPSLongitude)
    if not (
        latitude_ref in {"N", "S"}
        and longitude_ref in {"E", "W"}
        and isinstance(latitude_values, (tuple, list))
        and isinstance(longitude_values, (tuple, list))
        and len(latitude_values) == 3
        and len(longitude_values) == 3
    ):
        return None

    latitude = _degrees(cast(tuple[object, object, object], latitude_values))
    longitude = _degrees(cast(tuple[object, object, object], longitude_values))
    if latitude_ref == "S":
        latitude *= -1
    if longitude_ref == "W":
        longitude *= -1
    return GpsCoordinates(latitude=latitude, longitude=longitude)


def _capture_time(exif: dict[int, Any]) -> datetime | None:
    value = exif.get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _safe_exif_summary(exif: dict[int, Any], gps: GpsCoordinates | None) -> dict[str, Any]:
    fields: dict[int, str] = {
        ExifTags.Base.Orientation: "orientation",
        ExifTags.Base.Make: "camera_make",
        ExifTags.Base.Model: "camera_model",
        ExifTags.Base.Software: "software",
    }
    summary: dict[str, Any] = {}
    for tag, key in fields.items():
        value = exif.get(tag)
        if isinstance(value, (str, int)):
            summary[key] = value
    summary["has_gps"] = gps is not None
    return summary


def inspect_image(
    content: bytes,
    *,
    expected_mime_type: str,
    max_bytes: int,
    max_pixels: int,
) -> ImageMetadata:
    if not content:
        raise ImageValidationError("Uploaded file is empty")
    if len(content) > max_bytes:
        raise ImageValidationError("Uploaded file exceeds the configured size limit")
    if expected_mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
        raise ImageValidationError(f"Unsupported image MIME type: {expected_mime_type}")

    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width * image.height > max_pixels:
                raise ImageValidationError("Image dimensions exceed the configured pixel limit")
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            detected_mime = Image.MIME.get(image.format, "") if image.format else ""
            if expected_mime_type != detected_mime:
                raise ImageValidationError(
                    f"Declared MIME type {expected_mime_type} does not match "
                    f"{detected_mime or 'file data'}"
                )
            exif = dict(image.getexif())
            gps = extract_gps(image.getexif().get_ifd(ExifTags.IFD.GPSInfo))
            return ImageMetadata(
                mime_type=detected_mime,
                byte_size=len(content),
                width=image.width,
                height=image.height,
                captured_at=_capture_time(exif),
                camera_make=cast(str | None, exif.get(ExifTags.Base.Make)),
                camera_model=cast(str | None, exif.get(ExifTags.Base.Model)),
                gps=gps,
                exif_summary=_safe_exif_summary(exif, gps),
            )
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ImageValidationError("The uploaded file is not a valid readable image") from exc
