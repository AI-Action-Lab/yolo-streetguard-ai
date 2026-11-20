from fastapi.testclient import TestClient

from streetguard.security.oidc import extract_roles
from streetguard.security.rbac import Role


def test_report_mutations_require_bearer_authentication(client: TestClient) -> None:
    create = client.post(
        "/api/v1/reports",
        json={
            "upload_id": "00000000-0000-0000-0000-000000000001",
            "location_id": "00000000-0000-0000-0000-000000000002",
        },
    )
    submit = client.post("/api/v1/reports/SG-GLOBAL-EXAMPLE/submit")
    verify = client.post(
        "/api/v1/reports/SG-GLOBAL-EXAMPLE/verification",
        json={"decision": "verified", "reason": "reviewed"},
    )

    assert create.status_code == 401
    assert submit.status_code == 401
    assert verify.status_code == 401
    assert create.headers["www-authenticate"] == "Bearer"


def test_known_oidc_roles_are_extracted_and_unknown_roles_ignored() -> None:
    roles = extract_roles(
        {
            "roles": [Role.REGISTERED_CITIZEN.value, "future-role"],
            "realm_access": {"roles": [Role.VERIFIED_REVIEWER.value]},
        }
    )

    assert roles == {Role.REGISTERED_CITIZEN, Role.VERIFIED_REVIEWER}


def test_public_schema_does_not_expose_reporter_or_original_image(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    report_schema = schema["components"]["schemas"]["ReportResponse"]
    fields = report_schema["properties"]

    assert "reporter_id" not in fields
    assert "original_image_url" not in fields
    assert "annotated_image_url" in fields
    assert "history" in fields


def test_report_openapi_exposes_complete_phase_four_lifecycle(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/reports" in paths
    assert "/api/v1/reports/mine" in paths
    assert "/api/v1/reports/{public_id}/submit" in paths
    assert "/api/v1/reports/{public_id}/verification" in paths
    assert "/api/v1/reports/{public_id}/duplicates" in paths
    assert "/api/v1/reports/{public_id}" in paths
