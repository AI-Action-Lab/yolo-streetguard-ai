# Pothole Detection Module

## Overview

The `detector/` module contains the code responsible for detecting potholes in road images using the trained YOLO model.

The current implementation loads the trained model, processes an input image, identifies predicted pothole locations, and saves an annotated image for visual inspection.

## Files

### `predict.py`

The prediction script runs inference using the trained YOLO model.

**Main responsibilities:**
- Load the trained model from `models/pothole/best.pt`.
- Read the input road image.
- Run pothole detection using YOLO.
- Generate bounding boxes around predicted potholes.
- Display confidence scores for individual detections.
- Save an annotated image under `outputs/detections/`.
- Print detection coordinates and confidence scores.

## Model Information

| Property | Value |
|---|---|
| Model family | YOLO |
| Model variant | YOLO11n |
| Detection class | `pothole` |
| Class ID | `0` |
| Input image size | 640 pixels |
| Confidence threshold | 0.25 |
| Inference device | CPU |

The trained model was developed using Google Colab with a Tesla T4 GPU and tested locally on a CPU.

## How to Run

Open the project root in VS Code and activate the `streetguard` Conda environment.

Run:

```powershell
python src/detector/predict.py
```

Ensure the trained model is available at:

```text
models/pothole/best.pt
```

The input image path and output directory are configured in the prediction script.

## Detection Workflow

1. Load the trained YOLO model.
2. Read the selected road image.
3. Perform inference.
4. Extract predicted bounding boxes and confidence scores.
5. Save the annotated image.
6. Review the results to identify missed potholes or false detections.

## Current Limitations

- The model detects potholes but does not yet classify their severity.
- GPS-based location tracking has not been implemented.
- Detection accuracy can vary with lighting, camera angle, road conditions, and image quality.
- Predictions require further testing across diverse road images.

## Future Improvements

- Support batch processing of road images and videos.
- Integrate GPS coordinates with detection results.
- Add severity assessment after developing and validating a suitable method.
- Improve detection performance through validation-based model tuning.
- Integrate predictions with the future reporting and analytics modules.