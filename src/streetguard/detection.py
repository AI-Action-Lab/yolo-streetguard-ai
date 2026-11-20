from __future__ import annotations

import io
import time
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Any, Protocol, cast

from PIL import Image

from streetguard.domain.detections import DetectionBox, DetectionResult, utc_now
from streetguard.images import inspect_image


class ModelProtocol(Protocol):
    def predict(self, **kwargs: Any) -> list[Any]: ...


class Detector:
    def __init__(
        self,
        model_path: Path,
        *,
        checksum: str,
        confidence_threshold: float = 0.25,
        image_size: int = 640,
        device: str = "cpu",
        max_bytes: int = 20_000_000,
        max_pixels: int = 50_000_000,
        model_factory: Any | None = None,
    ) -> None:
        self.model_path = model_path.resolve()
        self.checksum = checksum.lower()
        self.confidence_threshold = confidence_threshold
        self.image_size = image_size
        self.device = device
        self.max_bytes = max_bytes
        self.max_pixels = max_pixels
        self._model_factory = model_factory
        self._model: ModelProtocol | None = None
        self._lock = Lock()

    def verify_model(self) -> str:
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Trained model not found: {self.model_path}")
        digest = sha256(self.model_path.read_bytes()).hexdigest()
        if digest != self.checksum:
            raise ValueError(
                f"Model checksum mismatch for {self.model_path}; "
                f"expected {self.checksum}, got {digest}"
            )
        return digest

    def _load_model(self) -> ModelProtocol:
        with self._lock:
            if self._model is None:
                self.verify_model()
                if self._model_factory is None:
                    from ultralytics import YOLO

                    self._model_factory = YOLO
                self._model = cast(ModelProtocol, self._model_factory(str(self.model_path)))
            model = self._model
            assert model is not None
            return model

    def detect(self, content: bytes, mime_type: str) -> DetectionResult:
        metadata = inspect_image(
            content,
            expected_mime_type=mime_type,
            max_bytes=self.max_bytes,
            max_pixels=self.max_pixels,
        )
        model = self._load_model()
        started = time.perf_counter()
        source_image = Image.open(io.BytesIO(content)).convert("RGB")
        result = model.predict(
            source=source_image,
            conf=self.confidence_threshold,
            imgsz=self.image_size,
            device=self.device,
            save=False,
            verbose=False,
        )[0]
        elapsed_ms = max(0, round((time.perf_counter() - started) * 1000))

        boxes: list[DetectionBox] = []
        for raw_box in result.boxes:
            x1, y1, x2, y2 = raw_box.xyxy[0].tolist()
            width = x2 - x1
            height = y2 - y1
            boxes.append(
                DetectionBox(
                    class_name="pothole",
                    confidence=float(raw_box.conf[0]),
                    x_center=(x1 + x2) / (2 * metadata.width),
                    y_center=(y1 + y2) / (2 * metadata.height),
                    box_width=width / metadata.width,
                    box_height=height / metadata.height,
                )
            )

        with TemporaryDirectory(prefix="streetguard-") as temporary_directory:
            output_path = Path(temporary_directory) / "annotated.jpg"
            result.save(filename=str(output_path))
            annotated_bytes = output_path.read_bytes()

        if not annotated_bytes:
            image = Image.open(io.BytesIO(content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            annotated_bytes = buffer.getvalue()

        return DetectionResult(
            boxes=tuple(boxes),
            annotated_bytes=annotated_bytes,
            processing_ms=elapsed_ms,
            model_version=self.checksum[:16],
            completed_at=utc_now(),
        )
