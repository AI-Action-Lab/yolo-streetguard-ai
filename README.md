# YOLO StreetGuard AI 🚧

### AI-Powered Pothole Detection and Road Safety Platform

YOLO StreetGuard AI is a computer vision project designed to detect potholes in road images using a custom-trained YOLO object detection model.

The project's long-term goal is to develop an intelligent road monitoring platform that combines pothole detection with severity assessment, location tracking, reporting, and interactive analytics to support road maintenance and improve road safety.

> **Current status:** The pothole detection model has been trained, evaluated, and tested locally. Additional platform features are under development.

---

## 📌 Table of Contents

- [Project Overview](#-project-overview)
- [Problem Statement](#-problem-statement)
- [Project Objectives](#-project-objectives)
- [Current Features](#-current-features)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Dataset and Preparation](#-dataset-and-preparation)
- [Model Training and Evaluation](#-model-training-and-evaluation)
- [Installation](#-installation)
- [Running Pothole Detection](#-running-pothole-detection)
- [Output](#-output)
- [Development Roadmap](#-development-roadmap)
- [Limitations](#-limitations)
- [Contributing](#-contributing)
- [License and Dataset Attribution](#-license-and-dataset-attribution)

---

## 📖 Project Overview

Potholes can damage vehicles, create traffic hazards, and increase the risk of road accidents.

Traditional road inspection often depends on manual observation and reporting. Computer vision provides an opportunity to automate part of this process by identifying potential potholes from images.

YOLO StreetGuard AI uses a custom-trained YOLO model to locate potholes in road images and generate annotated images containing bounding boxes and confidence scores.

The planned platform will extend this detection pipeline into a more complete road monitoring solution.

### Intended workflow

1. Provide an image containing a road.
2. Run the trained YOLO model.
3. Identify potential potholes.
4. Display bounding boxes and confidence scores.
5. Save the annotated image.
6. Extend the system with severity estimation, geographic location, reporting, and analytics.

---

## 🎯 Problem Statement

Road damage can be difficult to monitor consistently across large road networks. Manual inspections can require substantial time and resources, while reports from road users may lack precise location information or supporting evidence.

This project explores how AI-based object detection can help identify potholes from images and provide a foundation for a more structured road monitoring and maintenance workflow.

The model's predictions are intended to assist inspection. They do not replace professional road assessments or establish the actual severity of road damage.

---

## 🚀 Project Objectives

- Develop a custom-trained YOLO model for pothole detection.
- Convert annotated road images into YOLO-compatible training labels.
- Validate dataset structure and annotation integrity.
- Train and evaluate the model using Google Colab with GPU acceleration.
- Run trained-model inference locally on Windows.
- Generate annotated images with detection confidence scores.
- Develop a future severity estimation component.
- Integrate geographic location and pothole reporting.
- Build an interactive dashboard for road condition analytics.
- Explore a structured workflow for tracking reported potholes and repairs.

---

## ✨ Current Features

### Implemented

- Pothole dataset preparation.
- Pascal VOC XML to YOLO annotation conversion.
- Training, validation, and test dataset organization.
- Dataset integrity validation.
- YOLO model training in Google Colab.
- Evaluation using precision, recall, and mean average precision.
- Local inference using the trained model.
- Bounding-box visualization.
- Confidence score reporting.
- Saving annotated detection images.

### Planned

- Pothole severity estimation.
- GPS coordinates and geographic mapping.
- Structured pothole reporting.
- Database integration.
- Interactive analytics dashboard.
- Map-based road damage visualization.
- Maintenance status tracking.
- Automated reporting and repair workflow.

---

## 🛠 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Primary programming language |
| Ultralytics YOLO | Object detection and model training |
| PyTorch | Deep learning framework |
| OpenCV | Computer vision and image processing |
| Google Colab | Cloud-based model training |
| CUDA-enabled GPU | Accelerated training in Colab |
| VS Code | Local development |
| Anaconda | Python environment management |
| Git and GitHub | Version control and project collaboration |

Additional technologies may be introduced as the reporting, database, mapping, and dashboard components are developed.

---

## 📁 Project Structure

```text
yolo-streetguard-ai/
│
├── configs/                    # Project and model configurations
│
├── data/
│   ├── raw/                    # Original dataset and annotations
│   └── processed/
│       └── potholes/           # YOLO-formatted dataset
│           ├── images/
│           │   ├── train/
│           │   ├── val/
│           │   └── test/
│           ├── labels/
│           │   ├── train/
│           │   ├── val/
│           │   └── test/
│           └── data.yaml
│
├── models/
│   └── pothole/
│       └── best.pt             # Trained model checkpoint
│
├── notebooks/
│   └── YOLO_StreetGuard_Training.ipynb
│
├── outputs/
│   └── detections/             # Locally generated predictions
│
├── src/
│   ├── data_processing/        # Dataset conversion and validation
│   ├── detector/               # Pothole inference
│   ├── severity/               # Planned severity estimation
│   ├── location/               # Planned location processing
│   ├── reporting/              # Planned reporting functionality
│   ├── database/               # Planned data persistence
│   └── analytics/              # Planned analytics
│
├── pages/                      # Planned dashboard pages
├── tests/                      # Automated tests
├── docs/                       # Additional documentation
├── .gitignore
└── README.md
```

This tree describes the intended organization. Some folders may contain only placeholders or documentation until their functionality is implemented.

---

## 🗂 Dataset and Preparation

The project uses an annotated pothole dataset sourced from Kaggle.

The original annotations use Pascal VOC XML format. A preprocessing script converts valid bounding boxes into normalized YOLO format.

### Dataset source

[Annotated Potholes Dataset — Kaggle](https://www.kaggle.com/datasets/chitholian/annotated-potholes-dataset)

Review the original dataset's license and redistribution conditions before sharing the dataset or its images.

### Processed dataset summary

| Split | Images | Bounding boxes |
|---|---:|---:|
| Training | 479 | 1,310 |
| Validation | 52 | 128 |
| Testing | 133 | 299 |
| **Total** | **664** | **1,737** |

One invalid source annotation was excluded because its bounding box had zero width.

The processed dataset was checked for structural and label-format issues. The validation script reported zero issues.

### Dataset configuration

The YOLO dataset configuration defines:

- Training images.
- Validation images.
- Test images.
- One object class: `pothole`.

The raw dataset is kept separate from generated files. Dataset files should not be committed to GitHub unless their licensing, size, and redistribution permissions have been checked.

---

## 🧠 Model Training and Evaluation

The initial model was trained using Ultralytics YOLO11n in Google Colab with a Tesla T4 GPU.

### Training configuration

| Parameter | Value |
|---|---|
| Model | YOLO11n |
| Training epochs | 30 |
| Image size | 640 pixels |
| Batch size | 8 |
| Training environment | Google Colab |
| GPU | NVIDIA Tesla T4 |
| Detection class | Pothole |

### Initial test-set results

| Metric | Result |
|---|---:|
| Precision | 78.70% |
| Recall | 65.22% |
| mAP@50 | 76.93% |
| mAP@50–95 | 49.59% |

These results are the baseline evaluation from the current experiment.

**Metric interpretation:**

- **Precision:** Measures how many predicted detections were correct under the evaluation criteria.
- **Recall:** Measures how many annotated potholes the model successfully detected.
- **mAP@50:** Measures detection performance at an intersection-over-union threshold of 0.50.
- **mAP@50–95:** Evaluates detection performance across multiple intersection-over-union thresholds.

Performance may vary on unfamiliar images, including roads with different lighting, weather, surface textures, and camera angles.

The test results should not be treated as a guarantee of real-world performance.

---

## 💻 Installation

### Prerequisites

- Windows, macOS, or Linux.
- Python environment with compatible dependencies.
- Git.
- A local copy of this repository.
- The trained model checkpoint, `best.pt`.

The current local development environment uses Windows and an Anaconda environment named `streetguard`.

### 1. Clone the repository

```bash
git clone https://github.com/AI-Action-Lab/yolo-streetguard-ai.git
cd yolo-streetguard-ai
```

### 2. Install dependencies

Activate your Python environment and install the required packages:

```bash
pip install ultralytics opencv-python pyyaml
```

The project has been tested with Ultralytics 8.4.189 in the current development environment. Other versions may behave differently.

For reproducibility, a dependency file with verified package versions should be maintained as the project develops.

### 3. Add the trained model

Place the trained checkpoint at:

```text
models/pothole/best.pt
```

The checkpoint is not necessarily included in the GitHub repository. Obtain it from the project's training artifacts or the authorized model-storage location.

---

## 🔍 Running Pothole Detection

The current inference script is:

```text
src/detector/predict.py
```

It loads the trained model, runs inference on a user-provided image, prints the detected bounding boxes and confidence scores, and saves the annotated image.

### Run the script

From the repository root, run:

```bash
python src/detector/predict.py
```

If you are using a specific Python environment, invoke the Python executable from that environment.

When prompted, enter the full path to an image:

```text
Enter the full path to a road image:
```

For example:

```text
C:\Images\road_test.jpg
```

The current script uses:

- Confidence threshold: `0.25`
- Inference image size: `640`
- Device: CPU

### Output location

The annotated image is saved in:

```text
outputs/detections/
```

The output filename is based on the input image name and ends with `_detected.jpg`.

---

## 📊 Output

The inference script reports:

- Input image name.
- Number of detected potholes.
- Confidence threshold.
- Confidence score for each detection.
- Bounding-box coordinates.
- Output image location.

Detection confidence is a model score, not a calibrated probability that a pothole exists.

Predictions should be reviewed visually, particularly when the model is applied to images outside the training distribution.

---

## 🗺 Development Roadmap

### Phase 1 — Dataset Preparation
**Status: Completed**

- [x] Organize the source dataset.
- [x] Convert Pascal VOC annotations to YOLO format.
- [x] Prepare training, validation, and test splits.
- [x] Validate the processed dataset.

### Phase 2 — Model Training
**Status: Completed — Initial Baseline**

- [x] Train YOLO11n in Google Colab.
- [x] Evaluate the trained model.
- [x] Download the trained checkpoint.
- [x] Verify local model loading.

### Phase 3 — Local Detection
**Status: Completed — Initial Implementation**

- [x] Implement local inference.
- [x] Generate bounding boxes.
- [x] Print confidence scores.
- [x] Save annotated images.
- [ ] Conduct broader real-world error analysis.
- [ ] Evaluate duplicate detections and missed potholes.

### Phase 4 — Severity Estimation
**Status: Planned**

- [ ] Define a defensible severity-assessment methodology.
- [ ] Determine which image features or additional labels are required.
- [ ] Evaluate severity estimates against appropriate ground truth.

### Phase 5 — Location and Reporting
**Status: Planned**

- [ ] Capture or associate geographic coordinates.
- [ ] Define a structured pothole report.
- [ ] Store reports in a database.
- [ ] Add report validation and status tracking.

### Phase 6 — Analytics and Dashboard
**Status: Planned**

- [ ] Develop interactive analytics.
- [ ] Visualize reported potholes on a map.
- [ ] Track reported and repaired road damage.
- [ ] Build a dashboard for reviewing road conditions.

---

## ⚠️ Limitations

The current implementation is an image-based pothole detector, not a complete road safety monitoring system.

- It processes images rather than continuously monitoring roads.
- It does not currently calculate actual pothole depth.
- It does not independently establish pothole severity.
- It does not automatically determine GPS coordinates.
- It does not currently submit reports to a database or authority.
- Predictions may be affected by lighting, shadows, standing water, image quality, and unfamiliar road surfaces.
- A high-confidence detection can still be incorrect.
- Model performance requires further testing on diverse real-world road images.

These limitations will guide future development and evaluation.

---

## 🤝 Contributing

Contributions, suggestions, and constructive feedback are welcome.

For proposed changes:

1. Explain the issue or feature.
2. Describe the proposed implementation.
3. Test changes before submitting them.
4. Avoid committing raw datasets, large model artifacts, credentials, or generated outputs unless explicitly intended.
5. Document new functionality and dependencies.

---

## 📄 License and Dataset Attribution

The repository's software license and the source dataset's license are separate matters.

Before publishing a license for the complete project:

- Verify the dataset's license and redistribution conditions.
- Confirm the terms applicable to pretrained model weights and dependencies.
- Decide which license applies to the project's original source code.
- Document the attribution required by the dataset provider.

Do not assume that permission to download or use a dataset automatically permits redistribution.

---

## 👨‍💻 Project

**YOLO StreetGuard AI**

Repository: [AI-Action-Lab/yolo-streetguard-ai](https://github.com/AI-Action-Lab/yolo-streetguard-ai)

An evolving computer vision project exploring AI-assisted pothole detection and intelligent road monitoring.