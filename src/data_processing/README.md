# Data Processing Module

## Overview

The `data_processing/` module prepares the pothole dataset for training and evaluating the YOLO StreetGuard AI model.

It converts Pascal VOC XML annotations into YOLO-format text files and validates the processed dataset before model training.

## Scripts

### 1. `convert_voc_to_yolo.py`

Converts the original dataset annotations from Pascal VOC XML format into YOLO format.

**Main responsibilities:**
- Read image annotations from XML files.
- Extract pothole bounding-box coordinates.
- Normalize bounding-box coordinates for YOLO.
- Assign class ID `0` to the `pothole` class.
- Organize images and labels into training, validation, and test sets.
- Generate the YOLO dataset configuration file, `data.yaml`.
- Report annotations that cannot be converted.

### 2. `validate_yolo_dataset.py`

Checks the processed dataset for structural and annotation-format issues.

**Main responsibilities:**
- Check that image and label files exist.
- Validate YOLO label formatting.
- Check normalized bounding-box coordinates.
- Identify invalid labels and missing files.
- Summarize dataset integrity.

## Dataset Organization

The processed dataset follows this structure:

```text
data/processed/potholes/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
└── data.yaml
```

## Dataset Validation Results

The latest successful validation reported:

| Split | Images | Label Files | Bounding Boxes |
|---|---:|---:|---:|
| Train | 479 | 479 | 1,310 |
| Validation | 52 | 52 | 128 |
| Test | 133 | 133 | 299 |
| **Total** | **664** | **664** | **1,737** |

**Validation status:** No structural or label-format issues were found in the processed dataset.

One original annotation was skipped because its bounding box had zero width.

## Workflow

1. Place the original dataset in the appropriate location under `data/raw/`.
2. Run `convert_voc_to_yolo.py`.
3. Review the conversion summary and any skipped annotations.
4. Run `validate_yolo_dataset.py`.
5. Use the validated dataset for model training and evaluation.

## Important Notes

- Keep original dataset files separate from processed data.
- Review invalid annotations rather than inventing replacement coordinates.
- Preserve the dataset's original train/test separation.
- Record changes to preprocessing logic so the workflow remains reproducible.