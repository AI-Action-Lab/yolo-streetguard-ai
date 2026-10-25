# Training Notebooks

## Overview

The `notebooks/` directory contains Jupyter notebooks used for experimentation, model training, evaluation, and analysis in YOLO StreetGuard AI.

The primary notebook documents the initial pothole detection model training workflow performed in Google Colab.

## Current Notebook

### `YOLO_StreetGuard_Training.ipynb`

The notebook contains the training workflow for the project's baseline YOLO pothole detector.

The initial experiment used Ultralytics YOLO11n and a prepared pothole dataset.

## Training Environment

The initial model training was performed using Google Colab.

| Component | Configuration |
|---|---|
| Platform | Google Colab |
| Model | Ultralytics YOLO11n |
| GPU | NVIDIA Tesla T4 |
| Training epochs | 30 |
| Image size | 640 pixels |
| Batch size | 8 |
| Detection class | Pothole |

## Dataset

The notebook uses the processed pothole dataset with training, validation, and test splits.

The initial dataset contains:

| Split | Images |
|---|---:|
| Training | 479 |
| Validation | 52 |
| Testing | 133 |
| **Total** | **664** |

The dataset contains one object class: `pothole`.

The notebook's dataset paths may differ from local paths because the training workflow was executed in Google Colab.

## Training Workflow

The initial workflow includes:

1. Preparing the training environment.
2. Making the processed dataset available in Google Colab.
3. Configuring the dataset paths.
4. Loading the YOLO11n model.
5. Training the model.
6. Evaluating the trained model.
7. Reviewing validation predictions and diagnostic plots.
8. Saving and downloading the trained checkpoint.

## Initial Model Evaluation

The initial test-set evaluation reported:

| Metric | Result |
|---|---:|
| Precision | 78.70% |
| Recall | 65.22% |
| mAP@50 | 76.93% |
| mAP@50–95 | 49.59% |

These metrics describe the current baseline experiment. Further evaluation is needed to assess performance on diverse real-world road images.

## Reproducing the Experiment

To reproduce the initial training workflow:

1. Open `YOLO_StreetGuard_Training.ipynb` in Google Colab or a compatible Jupyter environment.
2. Obtain the authorized dataset and make it available to the notebook.
3. Verify the dataset configuration and file paths.
4. Confirm that the required Python packages are installed.
5. Run the notebook cells in the intended order.
6. Review the training and evaluation results.
7. Save the resulting checkpoint and supporting artifacts.

Exact commands, paths, and parameters should be taken from the notebook itself.

Google Colab resource availability and package versions may change over time, so results may not be identical across environments.

## Notebook Guidelines

- Keep notebooks organized into logical sections.
- Document important training parameters.
- Record evaluation results and observations.
- Avoid storing credentials or private information in notebook outputs.
- Remove unnecessary output cells when they significantly increase file size.
- Do not commit raw datasets or large model checkpoints inside notebooks.
- Keep notebook results consistent with the actual experiment.

## Future Improvements

- Add experiments comparing model architectures.
- Document confidence-threshold selection using validation data.
- Analyze false positives and missed detections.
- Compare performance across different road conditions.
- Track experiments and their configurations.
- Document model improvements without repeatedly tuning against the test set.

## Status

**Current status:** The initial training notebook has been saved in the repository. The baseline model has been trained and tested locally.