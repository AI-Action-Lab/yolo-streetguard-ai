# Testing Directory

## Overview

The `tests/` directory is intended to contain automated tests for the YOLO StreetGuard AI project.

Testing helps identify errors, validate data-processing behavior, and improve the reliability of the pothole detection pipeline as the project grows.

**A comprehensive automated testing suite has not yet been implemented.**

## Planned Test Coverage

### 1. Data Processing Tests
Validate annotation conversion, YOLO label formatting, and handling of invalid bounding boxes.

### 2. Dataset Validation Tests
Check image-label consistency, dataset configuration, and bounding-box coordinate validity.

### 3. Model Loading Tests
Verify that the trained model can be loaded from the expected checkpoint path.

### 4. Prediction Tests
Check input-image handling, prediction output structure, confidence scores, and error handling.

### 5. Output Tests
Verify that annotated images are saved to the expected output directory.

## Proposed Directory Structure

```text
tests/
├── README.md
├── test_data_processing.py
├── test_dataset_validation.py
└── test_detector.py
```

The Python test files above are proposed examples. Create them as testing functionality is implemented.

## Recommended Testing Approach

- Use small, controlled test cases for data-processing logic.
- Test valid and invalid annotation inputs.
- Verify expected outputs instead of relying only on printed messages.
- Use temporary files or directories when practical.
- Avoid requiring a GPU for basic automated tests.
- Keep tests reproducible and independent of the full training dataset where possible.

## Running Tests

Once automated tests have been implemented, they can be run from the project root using the project's configured Python environment.

For example, if the project adopts `pytest`:

```powershell
python -m pytest tests/
```

This command is a future testing recommendation; it will only run meaningful tests after test files and the required dependencies are available.

## Current Status

**Status: Planned**

The project has validated the processed dataset and successfully run local pothole inference. A comprehensive automated testing suite remains future work.