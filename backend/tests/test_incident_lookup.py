from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, get_current_user
from app.main import app
from app.routers.incidents import get_incident_lookup_repository, get_liability_summary_generator
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
                "geometry_geojson": (
                    '{"type":"MultiLineString","coordinates":[[[-73.99,40.68],[-73.98,40.681]]]}'
                ),
                "min_lng": -73.99,
                "min_lat": 40.68,
                "max_lng": -73.98,
                "max_lat": 40.681,
                "center_lng": -73.985,
                "center_lat": 40.6805,
            },
            "map": {
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
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[[-73.99, 40.68], [-73.98, 40.681]]],
                },
                "bbox": [-73.99, 40.68, -73.98, 40.681],
                "center": [-73.985, 40.6805],
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


class StubLiabilitySummaryGenerator:
    def __init__(self, summary: str = "The timeline likely supports liability.") -> None:
        self.summary = summary
        self.payloads = []

    def generate_summary(self, payload):
        self.payloads.append(payload)
        return self.summary


class StubOpenIncidentLookupRepository(StubIncidentLookupRepository):
    def lookup_by_address(self, address: str | None) -> dict[str, object]:
        payload = super().lookup_by_address(address)
        payload["incidents"][0]["closed_at"] = None
        payload["incidents"][0]["status"] = "open"
        payload["incidents"][0]["events"] = [
            payload["incidents"][0]["events"][0],
        ]
        payload["event_count"] = 1
        return payload


class StubNoGeometryIncidentLookupRepository(StubIncidentLookupRepository):
    def lookup_by_address(self, address: str | None) -> dict[str, object]:
        payload = super().lookup_by_address(address)
        payload["map"] = None
        return payload


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
    assert payload["map"] == {
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
        "geometry": {
            "type": "MultiLineString",
            "coordinates": [[[-73.99, 40.68], [-73.98, 40.681]]],
        },
        "bbox": [-73.99, 40.68, -73.98, 40.681],
        "center": [-73.985, 40.6805],
    }
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


def test_incidents_by_address_returns_null_map_when_geometry_is_missing() -> None:
    repository = StubNoGeometryIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository

    with TestClient(app) as client:
        response = client.post("/api/incidents/by-address", json={"address": "145 smith street"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["map"] is None


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


def test_incident_liability_analysis_returns_screened_payload() -> None:
    repository = StubOpenIncidentLookupRepository()
    summary_generator = StubLiabilitySummaryGenerator()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository
    app.dependency_overrides[get_liability_summary_generator] = lambda: summary_generator

    with TestClient(app) as client:
        response = client.post(
            "/api/incidents/liability-analysis",
            json={
                "address": "145 smith street",
                "client_incident_date": "2026-01-25",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["liability_signal"] == "likely_liable"
    assert payload["case_strength"] == "maybe"
    assert payload["best_matching_incident_id"] == "DBSAMPLE0001"
    assert payload["best_matching_days_open"] == 23
    assert payload["analysis_summary"] == "The timeline likely supports liability."
    assert "not legal advice" in payload["disclaimer"].lower()
    assert summary_generator.payloads[0].best_matching_incident.external_id == "DBSAMPLE0001"


def test_incident_liability_analysis_requires_client_incident_date() -> None:
    repository = StubIncidentLookupRepository()
    summary_generator = StubLiabilitySummaryGenerator()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository
    app.dependency_overrides[get_liability_summary_generator] = lambda: summary_generator

    with TestClient(app) as client:
        response = client.post(
            "/api/incidents/liability-analysis",
            json={"address": "145 smith street"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {"detail": "Client incident date is required."}


def test_incident_liability_analysis_propagates_generator_failure() -> None:
    from fastapi import HTTPException

    class _FailingGenerator:
        def generate_summary(self, payload):
            raise HTTPException(status_code=502, detail="OpenAI liability analysis request failed.")

    repository = StubIncidentLookupRepository()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_incident_lookup_repository] = lambda: repository
    app.dependency_overrides[get_liability_summary_generator] = lambda: _FailingGenerator()

    with TestClient(app) as client:
        response = client.post(
            "/api/incidents/liability-analysis",
            json={
                "address": "145 smith street",
                "client_incident_date": "2026-01-25",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "OpenAI liability analysis request failed."


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
            "geometry_geojson": '{"type":"LineString","coordinates":[[-73.99,40.68],[-73.98,40.681]]}',
            "min_lng": -73.99,
            "min_lat": 40.68,
            "max_lng": -73.98,
            "max_lat": 40.681,
            "center_lng": -73.985,
            "center_lat": 40.6805,
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
    assert payload["map"] == {
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
        "geometry": {
            "type": "LineString",
            "coordinates": [[-73.99, 40.68], [-73.98, 40.681]],
        },
        "bbox": [-73.99, 40.68, -73.98, 40.681],
        "center": [-73.985, 40.6805],
    }
    assert [incident["id"] for incident in payload["incidents"]] == [11, 10]
    assert [event["id"] for event in payload["incidents"][0]["events"]] == [200, 201]
    assert [event["id"] for event in payload["incidents"][1]["events"]] == [100, 101]
