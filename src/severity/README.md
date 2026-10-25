# Road Damage Severity Assessment

## Overview

The `severity/` module is planned for assessing the severity of potholes detected by the YOLO StreetGuard AI model.

The current YOLO model identifies potholes and predicts their bounding boxes. It does not yet classify potholes by severity.

This module will provide a foundation for developing and integrating severity assessment into the project.

## Planned Objectives

- Assess the potential severity of detected potholes.
- Categorize road damage into meaningful severity levels.
- Associate severity information with individual detections.
- Support prioritization of road maintenance and repair.
- Provide structured severity information for future reports and analytics.

## Proposed Severity Categories

The following categories are proposed for future implementation:

| Category | Description |
|---|---|
| Low | Potentially minor road damage |
| Medium | Road damage that may require maintenance |
| High | Potentially significant road damage requiring priority assessment |

These categories are conceptual. Actual classification criteria must be defined and validated before they are used operationally.

## Proposed Implementation

Future development may investigate:

1. Image-based damage measurements.
2. Additional models or features for severity classification.
3. Road damage dimensions and visual characteristics.
4. Integration of severity results with pothole detections.
5. Validation against appropriately labeled severity data.

A bounding box alone does not reliably establish the real-world size or severity of a pothole. Reliable assessment may require additional information, such as camera calibration, physical measurements, or dedicated severity labels.

## Expected Integration

Once implemented, the module may receive pothole detections from `src/detector/` and provide severity assessments to the reporting and analytics components.

## Current Status

**Status: Planned**

Severity assessment has not yet been implemented or validated. The existing model currently detects potholes only.