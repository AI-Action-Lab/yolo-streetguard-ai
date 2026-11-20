from streetguard.models import Base


def test_phase_one_core_tables_are_registered() -> None:
    required_tables = {
        "users",
        "roles",
        "permissions",
        "uploads",
        "model_versions",
        "detection_runs",
        "pothole_detections",
        "geographical_regions",
        "locations",
        "reports",
        "severity_assessments",
        "authorities",
        "authority_assignments",
        "authority_memberships",
        "report_status_history",
        "duplicate_report_links",
        "notifications",
        "email_delivery_logs",
        "whatsapp_share_logs",
        "audit_logs",
        "system_settings",
    }

    assert required_tables <= set(Base.metadata.tables)


def test_phase_five_email_preferences_and_delivery_purpose_are_registered() -> None:
    user_columns = Base.metadata.tables["users"].columns
    delivery_columns = Base.metadata.tables["email_delivery_logs"].columns

    assert "email_verified" in user_columns
    assert "email_status_notifications_enabled" in user_columns
    assert "email_notifications_confirmed_at" in user_columns
    assert "purpose" in delivery_columns


def test_spatial_indexes_are_configured() -> None:
    geographical_region = Base.metadata.tables["geographical_regions"]
    location = Base.metadata.tables["locations"]

    region_spatial_indexes = [
        index
        for index in geographical_region.indexes
        if index.dialect_options["postgresql"].get("using") == "gist"
    ]
    location_spatial_indexes = [
        index
        for index in location.indexes
        if index.dialect_options["postgresql"].get("using") == "gist"
    ]

    assert len(region_spatial_indexes) == 1
    assert len(location_spatial_indexes) == 1
