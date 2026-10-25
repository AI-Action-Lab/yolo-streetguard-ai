# Database Module

## Overview

The `database/` module is planned to manage structured records associated with the YOLO StreetGuard AI project.

It will provide a foundation for storing pothole detection results and connecting them with image references, geographical locations, severity assessments, and maintenance reports as these features are implemented.

**Database integration has not yet been implemented.**

## Planned Objectives

- Store pothole detection records.
- Maintain references to source and annotated images.
- Store model confidence scores and timestamps.
- Associate detections with geographical coordinates when available.
- Store severity assessments when the severity module is implemented.
- Support retrieval of records for reporting and analytics.

## Proposed Detection Record

A future database record may contain the following fields:

| Field | Description |
|---|---|
| `detection_id` | Unique identifier for a detection |
| `image_path` | Reference to the source image |
| `confidence` | Model confidence score |
| `latitude` | Geographic latitude, when available |
| `longitude` | Geographic longitude, when available |
| `severity` | Severity assessment, when implemented |
| `timestamp` | Date and time of observation, when available |
| `model_version` | Version or identifier of the model used |

These fields are proposed for future development and do not represent an existing database schema.

## Potential Technologies

Depending on project requirements, future implementation may use:

- SQLite for a lightweight local database.
- PostgreSQL for a more scalable relational database.
- PostGIS if advanced geographic queries become necessary.

The final database technology has not yet been selected.

## Proposed Workflow

1. Receive detection results from the detector module.
2. Validate the information before storage.
3. Store the detection record and relevant metadata.
4. Retrieve records for reporting and analytics.
5. Integrate stored records with future dashboard functionality.

## Data Management Considerations

- Avoid storing duplicate detection records unnecessarily.
- Validate input values before database insertion.
- Keep large image files separate from database records where appropriate.
- Protect sensitive information and credentials.
- Document database schema changes as the project develops.

## Current Status

**Status: Planned**

The project currently generates pothole detections and annotated images. Persistent database storage, record retrieval, and database-backed reporting have not yet been implemented.