# Trained Models

## Overview

The `models/` directory is intended to organize trained machine learning models used by YOLO StreetGuard AI.

The project currently uses a custom-trained YOLO11n model for pothole detection.

Model checkpoints contain learned parameters required to run inference without training the model again.

## Directory Structure

```text
models/
├── README.md
└── pothole/
    └── best.pt
```

## Model Organization

### `pothole/`

Contains model artifacts associated with pothole detection.

See [`pothole/README.md`](pothole/README.md) for details about the current checkpoint and its usage.

### `best.pt`

The trained checkpoint currently used by the local inference script.

Expected location:

`models/pothole/best.pt`

The checkpoint was trained in Google Colab and successfully loaded in the local development environment.

## Model Training

The baseline model was trained using Ultralytics YOLO11n with the prepared pothole dataset.

Training configuration:

| Parameter | Value |
|---|---|
| Architecture | YOLO11n |
| Training epochs | 30 |
| Image size | 640 |
| Batch size | 8 |
| Training platform | Google Colab |
| Detection class | Pothole |

## Model Evaluation

The initial test-set evaluation reported:

| Metric | Result |
|---|---:|
| Precision | 78.70% |
| Recall | 65.22% |
| mAP@50 | 76.93% |
| mAP@50–95 | 49.59% |

These results describe the initial experiment. Further evaluation on diverse road images is required before drawing conclusions about real-world performance.

## Model Usage

The current inference implementation is located at:

`src/detector/predict.py`

It loads the checkpoint, performs object detection on an input image, reports detection confidence scores, and saves an annotated image.

## Storage and Version Control

Model checkpoints can be large, so their storage should be considered separately from source code.

Before committing a checkpoint:

1. Check its file size.
2. Check GitHub's current file-size limits.
3. Decide whether the model belongs in Git, Git LFS, or external artifact storage.
4. Document how other developers can obtain the checkpoint.
5. Avoid committing duplicate model versions unnecessarily.

Do not assume that a model checkpoint is available in the remote repository merely because it exists locally.

## Reproducibility

Keep the training notebook and relevant configuration files alongside the source code so that the training process can be understood and, where practical, reproduced.

Model weights and training code are separate artifacts and may need separate storage arrangements.

## Future Improvements

- Compare alternative YOLO model sizes.
- Evaluate false positives and missed potholes.
- Tune inference thresholds using validation data.
- Record model versions and evaluation results.
- Document model provenance and training configuration.
- Consider model artifact versioning for future releases.

## Status

**Current status:** A trained pothole detection checkpoint is available locally and has been tested with the inference script.