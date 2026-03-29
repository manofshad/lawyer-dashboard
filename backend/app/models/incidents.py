from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class GeoJsonLineGeometry(BaseModel):
    type: str
    coordinates: list[Any]


class IncidentMapData(BaseModel):
    normalized_address: str
    location: LocationResponse
    geometry: GeoJsonLineGeometry
    bbox: list[float] | None = None
    center: list[float] | None = None


class AddressIncidentLookupResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    address: str
    normalized_address: str
    location: LocationResponse
    map: IncidentMapData | None = None
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


class LiabilityAnalysisRequest(BaseModel):
    address: str | None = None
    client_incident_date: date | None = None


class LiabilityIncidentSummary(BaseModel):
    external_id: str
    reported_at: date
    closed_at: date | None
    status: str
    days_open_as_of_client_incident: int | None
    was_open_on_client_incident_date: bool
    qualifies_for_notice_window: bool


class LiabilityAnalysisResponse(BaseModel):
    address: str
    client_incident_date: date
    liability_signal: str
    case_strength: str
    best_matching_incident_id: str | None
    best_matching_days_open: int | None
    analysis_summary: str
    disclaimer: str


class LiabilityPromptPayload(BaseModel):
    address: str
    client_incident_date: date
    liability_signal: str
    case_strength: str
    best_matching_incident: LiabilityIncidentSummary | None
    incident_summaries: list[LiabilityIncidentSummary]
    additional_supporting_incident_count: int = Field(default=0, ge=0)
