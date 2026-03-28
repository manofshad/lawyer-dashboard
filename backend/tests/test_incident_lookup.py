from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, get_current_user
from app.main import app
from app.routers.incidents import get_incident_lookup_repository
from app.services.incident_lookup import (
    IncidentLookupNotFoundError,
    assemble_incident_lookup_response,
)


class StubIncidentLookupRepository:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def lookup_by_address(self, address: str | None) -> dict[str, object]:
        self.calls.append(address)

        if address is None or not address.strip():
            raise ValueError("Address field is required.")
        if address.strip().upper() == "UNKNOWN ADDRESS":
            raise IncidentLookupNotFoundError("No incidents found.")

        return {
            "address": address,
            "normalized_address": "145 SMITH STREET",
            "location": {
                "id": 1,
                "canonical_address": "145 SMITH STREET",
                "boro": "B",
                "house_num": "145",
                "street_name": "SMITH STREET",
                "from_street": "ATLANTIC AVENUE",
                "to_street": "PACIFIC STREET",
                "spec_loc": None,
                "location_key": "B|145|SMITH STREET|ATLANTIC AVENUE|PACIFIC STREET",
            },
            "incidents": [
                {
                    "id": 10,
                    "external_id": "DBSAMPLE0001",
                    "dataset_name": "street_pothole_work_orders_closed",
                    "source": "CALL CENTER",
                    "initiated_by": "CITIZEN",
                    "reported_at": date(2026, 1, 2),
                    "closed_at": date(2026, 1, 6),
                    "status": "closed",
                    "raw_payload": {"DefNum": "DBSAMPLE0001"},
                    "events": [
                        {
                            "id": 100,
                            "event_type": "reported",
                            "event_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                            "event_label": "Reported",
                            "metadata": {"source_field": "RptDate"},
                        },
                        {
                            "id": 101,
                            "event_type": "closed",
                            "event_at": datetime(2026, 1, 6, tzinfo=timezone.utc),
                            "event_label": "Closed",
                            "metadata": {"source_field": "RptClosed"},
                        },
                    ],
                }
            ],
            "incident_count": 1,
            "event_count": 2,
        }

    def debug_summary(self) -> dict[str, object]:
        return {
            "current_database": "postgres",
            "location_count": 10,
            "incident_count": 10,
            "event_count": 20,
            "sample_location": {
                "id": 1,
                "canonical_address": "145 SMITH STREET",
                "boro": "B",
                "house_num": "145",
                "street_name": "SMITH STREET",
                "from_street": "ATLANTIC AVENUE",
                "to_street": "PACIFIC STREET",
                "spec_loc": None,
                "location_key": "B|145|SMITH STREET|ATLANTIC AVENUE|PACIFIC STREET",
            },
        }

    def debug_lookup_address(self, address: str | None) -> dict[str, object]:
        if address is None or not address.strip():
            raise ValueError("Address query parameter is required.")

        return {
            "input_address": address,
            "normalized_address": "145 SMITH STREET",
            "match_count": 1,
            "matches": [
                {
                    "id": 1,
                    "canonical_address": "145 SMITH STREET",
                    "boro": "B",
                    "house_num": "145",
                    "street_name": "SMITH STREET",
                    "from_street": "ATLANTIC AVENUE",
                    "to_street": "PACIFIC STREET",
                    "spec_loc": None,
                    "location_key": "B|145|SMITH STREET|ATLANTIC AVENUE|PACIFIC STREET",
                }
            ],
        }


def override_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(token="token", claims={"sub": "user-1", "email": "user@example.com"})


def test_incidents_by_address_returns_nested_location_payload() -> None:
    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post("/api/incidents/by-address", json={"address": "145 smith street"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert repository.calls == ["145 smith street"]

    payload = response.json()
    assert payload["normalized_address"] == "145 SMITH STREET"
    assert payload["location"]["canonical_address"] == "145 SMITH STREET"
    assert payload["incident_count"] == 1
    assert payload["event_count"] == 2
    assert payload["incidents"][0]["external_id"] == "DBSAMPLE0001"
    assert [event["event_type"] for event in payload["incidents"][0]["events"]] == [
        "reported",
        "closed",
    ]


def test_incidents_by_address_trims_whitespace_input() -> None:
    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post(
            "/api/incidents/by-address",
            json={"address": "   145 smith street   "},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert repository.calls == ["   145 smith street   "]
    assert response.json()["normalized_address"] == "145 SMITH STREET"


def test_incidents_by_address_requires_address() -> None:
    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post("/api/incidents/by-address", json={})

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {"detail": "Address field is required."}
    assert repository.calls == [None]


def test_incidents_by_address_returns_not_found_for_unknown_address() -> None:
    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post("/api/incidents/by-address", json={"address": "unknown address"})

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "No incidents found for the provided address."}


def test_incidents_by_address_requires_authentication() -> None:
    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post("/api/incidents/by-address", json={"address": "145 smith street"})

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token."}


def test_incident_db_check_returns_database_summary() -> None:
    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.get("/api/incidents/debug/db-check")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "current_database": "postgres",
        "location_count": 10,
        "incident_count": 10,
        "event_count": 20,
        "sample_location": {
            "id": 1,
            "canonical_address": "145 SMITH STREET",
            "boro": "B",
            "house_num": "145",
            "street_name": "SMITH STREET",
            "from_street": "ATLANTIC AVENUE",
            "to_street": "PACIFIC STREET",
            "spec_loc": None,
            "location_key": "B|145|SMITH STREET|ATLANTIC AVENUE|PACIFIC STREET",
        },
    }


def test_incident_address_check_returns_normalized_match_details() -> None:
    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.get(
            "/api/incidents/debug/address-check",
            params={"address": "145 smith street"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "input_address": "145 smith street",
        "normalized_address": "145 SMITH STREET",
        "match_count": 1,
        "matches": [
            {
                "id": 1,
                "canonical_address": "145 SMITH STREET",
                "boro": "B",
                "house_num": "145",
                "street_name": "SMITH STREET",
                "from_street": "ATLANTIC AVENUE",
                "to_street": "PACIFIC STREET",
                "spec_loc": None,
                "location_key": "B|145|SMITH STREET|ATLANTIC AVENUE|PACIFIC STREET",
            }
        ],
    }


def test_assemble_incident_lookup_response_groups_events_per_incident() -> None:
    payload = assemble_incident_lookup_response(
        address="145 smith street",
        normalized_address="145 SMITH STREET",
        location={
            "id": 1,
            "canonical_address": "145 SMITH STREET",
            "boro": "B",
            "house_num": "145",
            "street_name": "SMITH STREET",
            "from_street": "ATLANTIC AVENUE",
            "to_street": "PACIFIC STREET",
            "spec_loc": None,
            "location_key": "B|145|SMITH STREET|ATLANTIC AVENUE|PACIFIC STREET",
        },
        incidents=[
            {
                "id": 11,
                "external_id": "DBSAMPLE0002",
                "dataset_name": "street_pothole_work_orders_closed",
                "source": "APP",
                "initiated_by": "CITIZEN",
                "reported_at": date(2026, 1, 3),
                "closed_at": date(2026, 1, 25),
                "status": "closed",
                "raw_payload": {"DefNum": "DBSAMPLE0002"},
            },
            {
                "id": 10,
                "external_id": "DBSAMPLE0001",
                "dataset_name": "street_pothole_work_orders_closed",
                "source": "CALL CENTER",
                "initiated_by": "CITIZEN",
                "reported_at": date(2026, 1, 2),
                "closed_at": date(2026, 1, 6),
                "status": "closed",
                "raw_payload": {"DefNum": "DBSAMPLE0001"},
            },
        ],
        events=[
            {
                "id": 200,
                "incident_id": 11,
                "event_type": "reported",
                "event_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
                "event_label": "Reported",
                "metadata": {"source_field": "RptDate"},
            },
            {
                "id": 201,
                "incident_id": 11,
                "event_type": "closed",
                "event_at": datetime(2026, 1, 25, tzinfo=timezone.utc),
                "event_label": "Closed",
                "metadata": {"source_field": "RptClosed"},
            },
            {
                "id": 100,
                "incident_id": 10,
                "event_type": "reported",
                "event_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                "event_label": "Reported",
                "metadata": {"source_field": "RptDate"},
            },
            {
                "id": 101,
                "incident_id": 10,
                "event_type": "closed",
                "event_at": datetime(2026, 1, 6, tzinfo=timezone.utc),
                "event_label": "Closed",
                "metadata": {"source_field": "RptClosed"},
            },
        ],
    )

    assert payload["incident_count"] == 2
    assert payload["event_count"] == 4
    assert [incident["id"] for incident in payload["incidents"]] == [11, 10]
    assert [event["id"] for event in payload["incidents"][0]["events"]] == [200, 201]
    assert [event["id"] for event in payload["incidents"][1]["events"]] == [100, 101]
