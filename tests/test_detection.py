from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from streetguard.detection import Detector
from streetguard.domain.detections import utc_now


class Tensor:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values

    def __getitem__(self, index: int) -> float:
        return self.values[index]

    def __float__(self) -> float:
        return self.values[0]


class FakeBox:
    def __init__(self, confidence: float, coordinates: list[float]) -> None:
        self.conf = Tensor([confidence])
        self.xyxy = [Tensor(coordinates)]


class FakeResult:
    def __init__(self, boxes: list[FakeBox]) -> None:
        self.boxes = boxes

    def save(self, filename: str) -> None:
        Image.new("RGB", (8, 8), "red").save(filename, format="JPEG")


class FakeModel:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.calls: list[dict[str, Any]] = []

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        self.calls.append(kwargs)
        return [FakeResult([FakeBox(0.81, [2.0, 3.0, 10.0, 15.0])])]


@pytest.fixture
def image_content() -> bytes:
    output = BytesIO()
    Image.new("RGB", (20, 20)).save(output, format="JPEG")
    return output.getvalue()


def detector_for(tmp_path: Path, factory: Any, confidence: float = 0.35) -> Detector:
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"trusted-test-model")
    return Detector(
        model_path,
        checksum=sha256(model_path.read_bytes()).hexdigest(),
        confidence_threshold=confidence,
        image_size=640,
        model_factory=factory,
    )


def test_detector_returns_structured_boxes_and_reuses_model(
    tmp_path: Path, image_content: bytes
) -> None:
    created: list[FakeModel] = []

    def factory(path: str) -> FakeModel:
        model = FakeModel(path)
        created.append(model)
        return model

    detector = detector_for(tmp_path, factory)
    result = detector.detect(image_content, "image/jpeg")
    second = detector.detect(image_content, "image/jpeg")

    assert len(created) == 1
    assert len(result.boxes) == 1
    assert result.boxes[0].confidence == pytest.approx(0.81)
    assert result.boxes[0].x_center == pytest.approx(0.3)
    assert result.boxes[0].y_center == pytest.approx(0.45)
    assert result.boxes[0].box_width == pytest.approx(0.4)
    assert result.boxes[0].box_height == pytest.approx(0.6)
    assert result.annotated_bytes.startswith(b"\xff\xd8")
    assert second.processing_ms >= 0
    assert created[0].calls[0]["conf"] == 0.35
    assert created[0].calls[0]["imgsz"] == 640
    assert isinstance(created[0].calls[0]["source"], Image.Image)


def test_detector_rejects_tampered_model(tmp_path: Path, image_content: bytes) -> None:
    detector = detector_for(tmp_path, FakeModel)
    detector.checksum = "0" * 64

    with pytest.raises(ValueError, match="checksum mismatch"):
        detector.detect(image_content, "image/jpeg")


def test_result_time_is_timezone_aware() -> None:
    assert utc_now().tzinfo is not None
