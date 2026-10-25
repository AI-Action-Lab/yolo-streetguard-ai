# Raw Dataset

## Overview

The `data/raw/` directory is intended to hold the original dataset used by YOLO StreetGuard AI.

The project uses an annotated pothole dataset containing road images and corresponding Pascal VOC XML annotations.

Original files are kept separate from processed training data to preserve the source material and support reproducible preprocessing.

## Directory Structure

```text
raw/
├── README.md
├── annotated-images/
│   ├── image files
│   └── XML annotation files
└── splits.json
```

The exact contents depend on the source dataset downloaded and prepared for the project.

## Dataset Source

The dataset used for the initial experiment is:

**Annotated Potholes Dataset — Kaggle**

https://www.kaggle.com/datasets/chitholian/annotated-potholes-dataset

Before redistributing any images or annotations, verify the dataset's current license, attribution requirements, and redistribution permissions.

## Dataset Contents

### 1. `annotated-images/`

This directory contains the original road images and their corresponding XML annotation files.

The XML annotations use Pascal VOC format to describe pothole bounding boxes.

The preprocessing pipeline reads the annotations and converts valid bounding boxes into YOLO format.

### 2. `splits.json`

This file records dataset split information used by the preprocessing workflow.

The conversion script uses the supplied training and testing lists and creates a validation subset from the original training list.

The current split configuration uses a fixed random seed of 42 for the training/validation division.

## Data Preparation

The raw dataset is processed using:

`src/data_processing/convert_voc_to_yolo.py`

The conversion workflow:

1. Reads the original image and XML annotation files.
2. Extracts pothole bounding-box coordinates.
3. Validates the bounding boxes.
4. Converts valid coordinates into normalized YOLO format.
5. Organizes the generated images and labels into training, validation, and test directories.
6. Excludes invalid annotations rather than inventing or modifying coordinates.

One source annotation was excluded because its bounding box had zero width.

The initial conversion produced 664 processed images and 1,737 valid pothole bounding boxes.

## Data Integrity

Original annotations should be preserved.

If an annotation is found to be invalid:

- Record the issue.
- Review the original image and annotation.
- Correct the annotation only when there is sufficient evidence.
- Document any correction.
- Regenerate and validate the processed dataset when appropriate.

## Storage and Version Control

**The raw dataset should not be committed to the Git repository by default.**

The project uses `.gitignore` to exclude `data/raw/`.

This helps prevent large dataset files from unnecessarily increasing repository size and avoids redistributing data without confirming the applicable permissions.

The README and preprocessing scripts can be version-controlled separately.

## Reproducibility

To reproduce the initial preprocessing workflow:

1. Obtain the dataset from its authorized source.
2. Place the original files in the expected directory structure.
3. Verify that the split information is available.
4. Run the conversion script.
5. Run the dataset-validation script.
6. Confirm that the generated dataset contains no structural or label-format issues.

Refer to the scripts under `src/data_processing/` for the actual implementation.

## Status

**Current status:** The source dataset has been used to create the initial YOLO-compatible pothole dataset.

The raw files are maintained separately from the processed dataset and should remain excluded from Git unless their redistribution is explicitly permitted.