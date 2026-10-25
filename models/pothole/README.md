# Pothole Detection Model

## Overview

This directory contains model artifacts for the pothole detection component of YOLO StreetGuard AI.

The current model is based on Ultralytics YOLO11n and was trained using the project's processed pothole dataset.

## Files

| File | Purpose |
|---|---|
| `best.pt` | Trained YOLO model checkpoint |
| `README.md` | Documentation for the pothole model |

The checkpoint is expected to be available locally at `models/pothole/best.pt`.

## Model Details

| Parameter | Value |
|---|---|
| Model family | YOLO11 |
| Model variant | YOLO11n |
| Task | Object detection |
| Number of classes | 1 |
| Class ID | 0 |
| Class name | `pothole` |
| Training epochs | 30 |
| Image size | 640 pixels |

## Evaluation Results

Initial test-set metrics:

- Precision: 78.70%
- Recall: 65.22%
- mAP@50: 76.93%
- mAP@50–95: 49.59%

These are baseline measurements for the current experiment, not guarantees of performance on unfamiliar images.

## Local Inference

The checkpoint is loaded by:

`src/detector/predict.py`

Run the inference script from the repository root:

```bash
python src/detector/predict.py
```

When prompted, enter the path to a road image.

The script reports predicted pothole detections and saves an annotated image under `outputs/detections/`.

## Model Limitations

The model predicts pothole bounding boxes. It does not currently estimate pothole depth, establish actual damage severity, or determine geographic coordinates.

Predictions should be reviewed visually, especially on images with shadows, standing water, unusual lighting, or road surfaces not represented in the training dataset.

## Checkpoint Management

The checkpoint may be excluded from GitHub because of its size.

If it is not present in the repository, obtain it from the project's authorized model storage or training artifacts and place it at:

`models/pothole/best.pt`

Do not upload large model files until the repository's storage approach has been decided.

## Status

**Current status:** The checkpoint has been loaded successfully on the local computer, and initial image inference has completed successfully.