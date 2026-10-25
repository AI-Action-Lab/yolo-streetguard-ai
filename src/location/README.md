# Location Tracking Module

## Overview

The `location/` module is planned to manage geographical information associated with potholes detected by YOLO StreetGuard AI.

The goal is to associate detected road damage with its location so that maintenance teams can identify affected areas and plan inspections.

**GPS-based location tracking has not yet been implemented.**

## Planned Objectives

- Capture or receive GPS coordinates associated with road images.
- Associate pothole detections with geographical locations.
- Store latitude and longitude with detection records.
- Support mapping of reported potholes.
- Help identify areas with repeated road damage.
- Provide location information to the reporting and analytics modules.

## Proposed Location Data

Each location record may contain the following fields:

| Field | Description |
|---|---|
| `latitude` | Geographic latitude |
| `longitude` | Geographic longitude |
| `timestamp` | Date and time of the observation |
| `image_path` | Reference to the road image |
| `detection_id` | Identifier for the associated detection |

These fields are proposed for future development and are not yet implemented.

## Proposed Workflow

1. Capture a road image using a camera or mobile device.
2. Obtain GPS coordinates from the image capture device or another location source.
3. Run pothole detection on the image.
4. Associate the detection with the corresponding coordinates.
5. Store the record for future reporting and visualization.
6. Display available records on a map once mapping functionality is implemented.

## Potential Integrations

Future development may include:

- GPS-enabled mobile devices.
- Mapping libraries.
- Geographic databases.
- Interactive maps showing detected potholes.
- Location-based maintenance reports.

## Important Considerations

- Image-based pothole detection does not automatically provide GPS coordinates.
- Location data should be captured or obtained separately and associated with the correct image.
- Coordinates should be validated before being stored or displayed.
- Avoid publishing precise location data that could create privacy or safety concerns.

## Current Status

**Status: Planned**

The current project detects potholes in road images. GPS integration, geographic storage, and map visualization have not yet been implemented.