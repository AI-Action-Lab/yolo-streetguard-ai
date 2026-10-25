# Pothole Reporting Module

## Overview

The `reporting/` module is planned to organize pothole detection results into structured reports for review, maintenance planning, and future integration with the YOLO StreetGuard AI dashboard.

The module will help transform individual detections into useful information for road maintenance teams.

**Automated reporting has not yet been implemented.**

## Planned Objectives

- Generate structured reports from pothole detection results.
- Include detection confidence scores and image references.
- Incorporate severity information when that feature becomes available.
- Include geographical coordinates when location tracking is implemented.
- Summarize detected road damage for review.
- Support future export of reports into common file formats.

## Proposed Report Information

| Field | Description |
|---|---|
| `report_id` | Unique report identifier |
| `detection_id` | Identifier for the associated pothole detection |
| `image_path` | Reference to the source or annotated image |
| `confidence` | Model confidence score |
| `latitude` | Geographic latitude, when available |
| `longitude` | Geographic longitude, when available |
| `severity` | Severity assessment, when implemented |
| `timestamp` | Date and time of observation, when available |

These fields are proposed for future development and are not yet implemented as a reporting system.

## Proposed Workflow

1. Receive detection results from `src/detector/`.
2. Collect available image, confidence, and timestamp information.
3. Attach location or severity information when those modules become available.
4. Organize the information into structured records.
5. Generate reports for review and maintenance planning.
6. Integrate reports with the future dashboard and analytics components.

## Potential Report Formats

Future versions may support:

- CSV summaries.
- JSON detection records.
- PDF reports.
- Dashboard-based reports.

## Important Considerations

- Model predictions should be reviewed before being treated as confirmed road damage.
- Reports should distinguish detected potholes from verified maintenance issues.
- Missing location or severity information should not be presented as confirmed data.
- Reports should retain references to the source images where appropriate.

## Current Status

**Status: Planned**

The project currently supports image-based pothole detection and annotated image generation. Automated report generation and maintenance-workflow integration have not yet been implemented.