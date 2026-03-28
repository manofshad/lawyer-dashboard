from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import AuthenticatedUser, get_current_user
from ..database import DatabaseConfigError, DatabaseConnectionError, get_database_url
from ..models.incidents import (
    AddressIncidentLookupResponse,
    AddressLookupDebugResponse,
    DatabaseDebugResponse,
    IncidentLookupRequest,
)
from ..services.incident_lookup import (
    IncidentLookupDataError,
    IncidentLookupNotFoundError,
    IncidentLookupRepository,
    IncidentLookupRepositoryError,
)
from ..settings import Settings, get_settings


router = APIRouter()


def get_incident_lookup_repository(
    settings: Settings = Depends(get_settings),
) -> IncidentLookupRepository:
    try:
        database_url = get_database_url(settings)
    except DatabaseConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database URL is not configured on the backend.",
        ) from exc

    return IncidentLookupRepository(database_url)


@router.post("/api/incidents/by-address", response_model=AddressIncidentLookupResponse)
async def incidents_by_address(
    payload: IncidentLookupRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: IncidentLookupRepository = Depends(get_incident_lookup_repository),
) -> AddressIncidentLookupResponse:
    del current_user

    try:
        result = repository.lookup_by_address(payload.address)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address field is required.",
        ) from exc
    except IncidentLookupNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No incidents found for the provided address.",
        ) from exc
    except IncidentLookupDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Multiple locations matched the provided address.",
        ) from exc
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query the incident database.",
        ) from exc
    except IncidentLookupRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load incidents for the provided address.",
        ) from exc

    return AddressIncidentLookupResponse.model_validate(result)


@router.get("/api/incidents/debug/db-check", response_model=DatabaseDebugResponse)
async def incident_db_check(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: IncidentLookupRepository = Depends(get_incident_lookup_repository),
) -> DatabaseDebugResponse:
    del current_user

    try:
        payload = repository.debug_summary()
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query the incident database.",
        ) from exc
    except IncidentLookupRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query the incident database.",
        ) from exc

    return DatabaseDebugResponse.model_validate(payload)


@router.get("/api/incidents/debug/address-check", response_model=AddressLookupDebugResponse)
async def incident_address_check(
    address: Annotated[str | None, Query()] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: IncidentLookupRepository = Depends(get_incident_lookup_repository),
) -> AddressLookupDebugResponse:
    del current_user

    try:
        payload = repository.debug_lookup_address(address)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address query parameter is required.",
        ) from exc
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query the incident database.",
        ) from exc
    except IncidentLookupRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query the incident database.",
        ) from exc

    return AddressLookupDebugResponse.model_validate(payload)
