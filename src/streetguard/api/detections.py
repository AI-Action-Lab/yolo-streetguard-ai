from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from streetguard.api.schemas import (
    UploadCompleteRequest,
    UploadCreateRequest,
    UploadCreateResponse,
    UploadStatusResponse,
)
from streetguard.config import Settings, get_settings
from streetguard.database import get_session
from streetguard.models.core import DetectionRun, ModelVersion, PotholeDetection, Upload
from streetguard.storage import S3ObjectStorage

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    payload: UploadCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UploadCreateResponse:
    if payload.byte_size > settings.max_image_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds the {settings.max_image_upload_bytes}-byte limit",
        )

    existing = (
        await session.execute(
            select(Upload).where(
                Upload.sha256 == payload.sha256,
                Upload.byte_size == payload.byte_size,
                Upload.mime_type == payload.content_type,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return UploadCreateResponse(
            upload_id=existing.id,
            object_key=existing.original_object_key,
            upload_url="",
            upload_fields={},
            expires_in_seconds=0,
            duplicate=True,
        )

    suffix = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/bmp": "bmp",
        "image/tiff": "tif",
    }[payload.content_type]
    upload_id = uuid4()
    object_key = f"quarantine/{upload_id}.{suffix}"
    storage = S3ObjectStorage(settings)
    grant = storage.presign_upload(object_key, payload.content_type, payload.byte_size)

    upload = Upload(
        id=upload_id,
        original_object_key=object_key,
        sha256=payload.sha256,
        mime_type=payload.content_type,
        byte_size=payload.byte_size,
        scan_status="pending_upload",
        processing_status="awaiting_upload",
        exif_summary={"filename": payload.filename, "idempotency_key": idempotency_key},
    )
    session.add(upload)
    await session.commit()
    return UploadCreateResponse(
        upload_id=upload.id,
        object_key=object_key,
        upload_url=grant.url,
        upload_fields=grant.fields or {},
        expires_in_seconds=settings.storage_signed_url_ttl_seconds,
    )


@router.post("/{upload_id}/complete", response_model=UploadStatusResponse, status_code=202)
async def complete_upload(
    upload_id: UUID,
    payload: UploadCompleteRequest,
    session: AsyncSession = Depends(get_session),
) -> UploadStatusResponse:
    upload = await session.get(Upload, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    if payload.object_key != upload.original_object_key:
        raise HTTPException(status_code=422, detail="Object key does not match the upload")

    existing_run = (
        await session.execute(
            select(DetectionRun)
            .where(DetectionRun.upload_id == upload.id)
            .order_by(DetectionRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing_run is not None:
        return await _upload_status(upload, existing_run, session)

    model = (
        await session.scalars(select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1))
    ).first()
    if model is None:
        raise HTTPException(status_code=503, detail="No active detection model is configured")

    run = DetectionRun(
        upload_id=upload.id,
        model_version_id=model.id,
        status="queued",
        confidence_threshold=model.confidence_threshold,
        image_size=model.image_size,
        settings_snapshot={
            "device": "worker-configured",
            "model_version": model.version,
            "model_sha256": model.artifact_sha256,
        },
    )
    upload.scan_status = "pending"
    upload.processing_status = "queued"
    session.add(run)
    await session.commit()
    await session.refresh(run)

    from streetguard.workers.detection import process_upload

    process_upload.delay(str(upload.id), str(run.id))
    return await _upload_status(upload, run, session)


@router.get("/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> UploadStatusResponse:
    upload = await session.get(Upload, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    run = (
        await session.scalars(
            select(DetectionRun)
            .where(DetectionRun.upload_id == upload.id)
            .order_by(DetectionRun.created_at.desc())
            .limit(1)
        )
    ).first()
    return await _upload_status(upload, run, session)


async def _upload_status(
    upload: Upload, run: DetectionRun | None, session: AsyncSession
) -> UploadStatusResponse:
    if run is not None:
        await session.refresh(run)
    settings = get_settings()
    from streetguard.api.schemas import DetectionRunResponse

    run_payload = None
    if run is not None:
        detections = (
            await session.scalars(
                select(PotholeDetection).where(PotholeDetection.detection_run_id == run.id)
            )
        ).all()
        annotated_url = None
        if upload.annotated_object_key:
            annotated_url = S3ObjectStorage(settings).presign_download(upload.annotated_object_key)
        run_payload = DetectionRunResponse(
            **{
                "id": run.id,
                "upload_id": run.upload_id,
                "status": run.status,
                "confidence_threshold": run.confidence_threshold,
                "image_size": run.image_size,
                "processing_ms": run.processing_ms,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "error_message": run.error_message,
                "annotated_download_url": annotated_url,
                "detections": list(detections),
            }
        )
    return UploadStatusResponse(
        id=upload.id,
        processing_status=upload.processing_status,
        scan_status=upload.scan_status,
        byte_size=upload.byte_size,
        mime_type=upload.mime_type,
        pixel_width=upload.pixel_width,
        pixel_height=upload.pixel_height,
        capture_time=upload.capture_time,
        exif_summary=upload.exif_summary,
        detection_run=run_payload,
    )
