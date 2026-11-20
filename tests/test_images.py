from datetime import datetime
from io import BytesIO

import pytest
from PIL import ExifTags, Image

from streetguard.images import ImageValidationError, inspect_image


def image_bytes(*, image_format: str = "JPEG", exif: Image.Exif | None = None) -> bytes:
    output = BytesIO()
    image = Image.new("RGB", (32, 24), color=(40, 80, 120))
    if exif is None:
        image.save(output, format=image_format)
    else:
        image.save(output, format=image_format, exif=exif)
    return output.getvalue()


def test_image_metadata_extracts_capture_time_and_gps() -> None:
    exif = Image.Exif()
    exif[ExifTags.Base.DateTimeOriginal] = "2025:01:02 03:04:05"
    exif[ExifTags.Base.GPSInfo] = {
        1: "N",
        2: (23.0, 1.0, 0.0),
        3: "E",
        4: (72.0, 30.0, 0.0),
    }

    metadata = inspect_image(
        image_bytes(exif=exif),
        expected_mime_type="image/jpeg",
        max_bytes=100_000,
        max_pixels=1_000_000,
    )

    assert metadata.width == 32
    assert metadata.height == 24
    assert metadata.captured_at == datetime(2025, 1, 2, 3, 4, 5)
    assert metadata.gps is not None
    assert metadata.gps.latitude == pytest.approx(23.0166667)
    assert metadata.gps.longitude == 72.5
    assert metadata.exif_summary["has_gps"] is True


def test_image_without_gps_remains_unlocated() -> None:
    metadata = inspect_image(
        image_bytes(),
        expected_mime_type="image/jpeg",
        max_bytes=100_000,
        max_pixels=1_000_000,
    )

    assert metadata.gps is None
    assert metadata.exif_summary == {"has_gps": False}


@pytest.mark.parametrize(
    ("content", "mime_type", "expected_message"),
    [
        (b"", "image/jpeg", "empty"),
        (b"not an image", "image/jpeg", "valid readable image"),
        (image_bytes(), "image/png", "does not match"),
        (image_bytes(), "application/pdf", "Unsupported"),
    ],
)
def test_invalid_images_are_rejected(content: bytes, mime_type: str, expected_message: str) -> None:
    with pytest.raises(ImageValidationError, match=expected_message):
        inspect_image(
            content,
            expected_mime_type=mime_type,
            max_bytes=100_000,
            max_pixels=1_000_000,
        )


def test_image_size_and_pixel_limits_are_enforced() -> None:
    content = image_bytes()

    with pytest.raises(ImageValidationError, match="size limit"):
        inspect_image(
            content,
            expected_mime_type="image/jpeg",
            max_bytes=len(content) - 1,
            max_pixels=1_000_000,
        )
    with pytest.raises(ImageValidationError, match="pixel limit"):
        inspect_image(
            content,
            expected_mime_type="image/jpeg",
            max_bytes=100_000,
            max_pixels=10,
        )
