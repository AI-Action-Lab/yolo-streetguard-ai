# Source Code (`src/`)

## Overview

The `src/` directory contains the source code for the YOLO StreetGuard AI project.

It is organized into modules to keep data processing, pothole detection, severity assessment, location tracking, reporting, database operations, and analytics separate and maintainable.

## Directory Structure

```text
src/
├── data_processing/
├── detector/
├── severity/
├── location/
├── reporting/
├── database/
└── analytics/
```

## Modules

### 1. `data_processing/`
Contains scripts for preparing datasets, converting annotations into YOLO format, and validating dataset integrity.

### 2. `detector/`
Contains the YOLO-based pothole detection code, including the prediction script used to identify potholes in road images.

### 3. `severity/`
**Planned module.** Intended to support future road-damage severity assessment. Severity classification has not yet been implemented.

### 4. `location/`
**Planned module.** Intended to support future GPS-based location tracking for detected potholes.

### 5. `reporting/`
**Planned module.** Intended to support the creation of pothole reports and related information.

### 6. `database/`
**Planned module.** Intended to store and manage pothole detection records and related metadata.

### 7. `analytics/`
**Planned module.** Intended to support future analysis of detection results and road-damage trends.

## Development Guidelines

- Keep each module focused on a specific responsibility.
- Use clear, descriptive filenames and function names.
- Add error handling and input validation where appropriate.
- Document new modules and significant changes.
- Keep generated results separate from source code.

## Current Project Status

The dataset preparation and YOLO pothole detection modules have been implemented. Severity assessment, GPS integration, reporting, database functionality, and analytics remain planned enhancements.