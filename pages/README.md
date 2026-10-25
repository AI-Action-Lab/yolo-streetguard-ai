# Dashboard Pages

## Overview

The `pages/` directory is intended to contain the user-interface pages for the YOLO StreetGuard AI application.

The planned dashboard will help users explore pothole detection results and, as additional features are implemented, review road-damage information, locations, and analytical summaries.

**The complete interactive dashboard has not yet been implemented.**

## Planned Pages

### 1. Home Dashboard
A central overview of the application's available features and key detection statistics.

### 2. Pothole Detection
A page for submitting road images, displaying detection results, and reviewing predicted pothole bounding boxes and confidence scores.

### 3. Detection History
A planned page for reviewing previously recorded detections once persistent storage is implemented.

### 4. Location Map
A planned map view for displaying pothole locations when GPS integration becomes available.

### 5. Analytics
A planned page for presenting detection statistics, charts, and road-damage trends.

### 6. Reports
A planned page for reviewing or exporting structured pothole reports.

These pages describe the intended application design. They should not be considered existing functionality until implemented.

## Potential Technologies

Depending on the final application architecture, the interface may use:

- Plotly Dash
- Plotly for interactive charts
- Python for application logic
- Mapping libraries for future geographic visualization

The final dashboard architecture remains subject to implementation decisions.

## Design Principles

- Keep the interface simple and easy to navigate.
- Present detection results clearly.
- Distinguish model predictions from verified road damage.
- Display meaningful error messages.
- Design pages so future features can be added independently.

## Current Status

**Status: Planned**

The project currently includes a local YOLO prediction script. The complete multi-page dashboard, detection history, map, analytics, and reporting interfaces remain future development tasks.