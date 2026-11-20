FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations

RUN pip install --no-cache-dir . \
    && groupadd --system --gid 10001 streetguard \
    && useradd --system --uid 10001 --gid streetguard --create-home streetguard \
    && mkdir -p /tmp/ultralytics \
    && chown -R streetguard:streetguard /home/streetguard /tmp/ultralytics

ENV HOME=/home/streetguard \
    YOLO_CONFIG_DIR=/tmp/ultralytics

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "streetguard.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS inference

USER root

RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install --no-cache-dir ".[model]"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libxcb1 \
        libxext6 \
        libx11-6 \
        libsm6 \
        libice6 \
    && rm -rf /var/lib/apt/lists/*

USER 10001:10001

CMD ["celery", "-A", "streetguard.celery_app:celery_app", "worker", "--loglevel=INFO", "--queues=detection", "--concurrency=1"]

FROM runtime AS final

CMD ["uvicorn", "streetguard.main:app", "--host", "0.0.0.0", "--port", "8000"]
