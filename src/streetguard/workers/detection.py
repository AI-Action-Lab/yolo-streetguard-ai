from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock
from uuid import UUID

from celery import Task
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from streetguard.celery_app import celery_app
from streetguard.config import get_settings
from streetguard.detection import Detector
from streetguard.images import ImageValidationError, inspect_image
from streetguard.models.core import DetectionRun, ModelVersion, PotholeDetection, Upload
from streetguard.storage import S3ObjectStorage

_detector_lock = Lock()
_detector: Detector | None = None


def get_detector() -> Detector:
    global _detector
    settings = get_settings()
    with _detector_lock:
        if _detector is None:
            _detector = Detector(
                settings.model_path,
                checksum=settings.model_checksum,
                confidence_threshold=settings.detection_confidence_threshold,
                image_size=settings.detection_image_size,
                device=settings.detection_device,
                max_bytes=settings.max_image_upload_bytes,
                max_pixels=settings.max_image_pixels,
            )
        return _detector


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True, name="streetguard.process_upload", max_retries=3
)
def process_upload(self: Task, upload_id: str, detection_run_id: str) -> dict[str, object]:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            upload = session.get(Upload, UUID(upload_id))
            run = session.get(DetectionRun, UUID(detection_run_id))
            if upload is None or run is None:
                raise ValueError("Upload or detection run no longer exists")
            if run.upload_id != upload.id:
                raise ValueError("Detection run does not belong to the upload")
            if run.status == "completed":
                return {
                    "upload_id": upload_id,
                    "detection_run_id": detection_run_id,
                    "status": "completed",
                }

            run.status = "processing"
            run.started_at = datetime.now(UTC)
            upload.processing_status = "ai_processing"
            upload.scan_status = "validating"
            session.commit()
            try:
                storage = S3ObjectStorage(settings)
                content = storage.download_bytes(upload.original_object_key)
                if len(content) != upload.byte_size:
                    raise ValueError("Uploaded byte size does not match the declared size")
                digest = sha256(content).hexdigest()
                if digest != upload.sha256:
                    raise ValueError("Uploaded file checksum does not match the declared SHA-256")

                metadata = inspect_image(
                    content,
                    expected_mime_type=upload.mime_type,
                    max_bytes=settings.max_image_upload_bytes,
                    max_pixels=settings.max_image_pixels,
                )
                upload.scan_status = "validated"
                upload.pixel_width = metadata.width
                upload.pixel_height = metadata.height
                upload.capture_time = metadata.captured_at
                upload.exif_summary = {
                    **upload.exif_summary,
                    **metadata.exif_summary,
                    "gps": (metadata.gps.model_dump() if metadata.gps is not None else None),
                    "location_message": (
                        None
                        if metadata.gps is not None
                        else (
                            "Location information is not available in this photograph. "
                            "Please select the location manually."
                        )
                    ),
                }
                session.commit()

                model_version = session.get(ModelVersion, run.model_version_id)
                if model_version is None:
                    raise ValueError("Configured model version no longer exists")
                if not model_version.is_active:
                    raise ValueError("Configured model version is no longer active")
                if model_version.artifact_sha256.lower() != settings.model_checksum.lower():
                    raise ValueError(
                        "Active database model checksum does not match worker configuration"
                    )
                if (
                    run.confidence_threshold != settings.detection_confidence_threshold
                    or run.image_size != settings.detection_image_size
                ):
                    raise ValueError("Detection run settings do not match worker configuration")

                detector = get_detector()
                result = detector.detect(content, upload.mime_type)
                annotated_key = f"derived/{upload.id}/annotated.jpg"
                storage.put_bytes(annotated_key, result.annotated_bytes, "image/jpeg")

                session.execute(
                    delete(PotholeDetection).where(PotholeDetection.detection_run_id == run.id)
                )
                session.add_all(
                    [
                        PotholeDetection(
                            detection_run_id=run.id,
                            class_name=box.class_name,
                            confidence=box.confidence,
                            x_center=box.x_center,
                            y_center=box.y_center,
                            box_width=box.box_width,
                            box_height=box.box_height,
                        )
                        for box in result.boxes
                    ]
                )
                upload.annotated_object_key = annotated_key
                upload.processing_status = "completed"
                run.status = "completed"
                run.completed_at = result.completed_at
                run.processing_ms = result.processing_ms
                run.worker_version = "phase-2"
                session.commit()
                return {
                    "upload_id": upload_id,
                    "detection_run_id": detection_run_id,
                    "status": "completed",
                    "detections": len(result.boxes),
                }
            except Exception as exc:
                session.rollback()
                session.refresh(run)
                session.refresh(upload)
                run.status = "failed"
                run.error_message = str(exc)
                run.completed_at = datetime.now(UTC)
                upload.processing_status = "failed"
                failure_text = str(exc).lower()
                upload.scan_status = (
                    "rejected"
                    if "uploaded" in failure_text or "image" in failure_text
                    else "pending"
                )
                session.commit()
                if isinstance(exc, (ImageValidationError, ValueError, FileNotFoundError)):
                    return {
                        "upload_id": upload_id,
                        "detection_run_id": detection_run_id,
                        "status": "failed",
                        "error": str(exc),
                    }
                raise
    except Exception as exc:
        raise self.retry(exc=exc, countdown=min(60, 5 * (2**self.request.retries))) from exc
    finally:
        engine.dispose()
