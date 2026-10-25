# Dataset Management

## Overview

The `data/` directory contains the datasets used by YOLO StreetGuard AI.

It separates the original source data from the processed data used for model training, validation, and testing.

This separation helps maintain data integrity, reproducibility, and a clear preprocessing workflow.

## Directory Structure

```text
data/
├── README.md
├── raw/
│   ├── README.md
│   ├── annotated-images/
│   └── splits.json
└── processed/
    ├── README.md
    └── potholes/
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

This structure represents the dataset organization used by the current project. Some generated files may exist only on the local machine or in the training environment.

## Raw Data

The `raw/` directory is intended for original dataset files and annotations.

The current dataset contains road images and Pascal VOC XML annotations.

Original files should be preserved so that the preprocessing workflow can be repeated when necessary.

See [`raw/README.md`](raw/README.md) for details.

## Processed Data

The `processed/` directory contains data prepared for model training and evaluation.

The current preprocessing pipeline converts valid Pascal VOC bounding boxes into normalized YOLO annotation format.

The processed dataset is organized into training, validation, and test splits.

See [`processed/README.md`](processed/README.md) for details.

## Dataset Summary

The current processed pothole dataset contains:

| Split | Images | Bounding Boxes |
|---|---:|---:|
| Training | 479 | 1,310 |
| Validation | 52 | 128 |
| Testing | 133 | 299 |
| **Total** | **664** | **1,737** |

One invalid source annotation was excluded because its bounding box had zero width.

## Data Management Guidelines

- Keep original source files separate from generated files.
- Do not modify raw annotations directly during preprocessing.
- Validate generated labels before training.
- Keep training, validation, and test splits separate.
- Avoid including test-set results in iterative model tuning.
- Do not commit large datasets without checking repository storage limits.
- Verify dataset licensing and attribution requirements before redistribution.
- Keep private data and credentials out of the repository.

## Reproducibility

The project includes preprocessing and dataset-validation scripts under `src/data_processing/`.

The intended workflow is:

1. Obtain the authorized source dataset.
2. Place the original files in the expected raw-data directory.
3. Run the annotation conversion script.
4. Validate the processed dataset.
5. Configure the dataset paths for the training environment.
6. Train and evaluate the model.

Exact commands and requirements should be maintained alongside the relevant scripts as the project develops.

## Status

**Current status:** The initial dataset has been converted, validated, and used to train the baseline pothole detection model.