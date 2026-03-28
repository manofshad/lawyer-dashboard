from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class IncidentLookupRequest(BaseModel):
    address: str | None = None


class IncidentEventResponse(BaseModel):
    id: int
    event_type: str
    event_at: datetime
    event_label: str | None
    metadata: dict[str, Any]


class IncidentResponse(BaseModel):
    id: int
    external_id: str
    dataset_name: str
    source: str | None
    initiated_by: str | None
    reported_at: date
    closed_at: date | None
    status: str
    raw_payload: dict[str, Any]
    events: list[IncidentEventResponse]


class LocationResponse(BaseModel):
    id: int
    canonical_address: str
    boro: str
    house_num: str | None
    street_name: str
    from_street: str | None
    to_street: str | None
    spec_loc: str | None
    location_key: str


class AddressIncidentLookupResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    address: str
    normalized_address: str
    location: LocationResponse
    incidents: list[IncidentResponse]
    incident_count: int
    event_count: int


class DatabaseDebugResponse(BaseModel):
    current_database: str
    location_count: int
    incident_count: int
    event_count: int
    sample_location: LocationResponse | None


class AddressLookupDebugResponse(BaseModel):
    input_address: str
    normalized_address: str
    match_count: int
    matches: list[LocationResponse]
