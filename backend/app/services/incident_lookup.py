from __future__ import annotations

from collections import defaultdict
import json
from typing import Any

from psycopg import Error

from ..database import get_db_connection
from ..sample_incidents import normalize_text


class IncidentLookupNotFoundError(RuntimeError):
    pass


class IncidentLookupDataError(RuntimeError):
    pass


class IncidentLookupRepositoryError(RuntimeError):
    pass


def normalize_lookup_address(address: str | None) -> str | None:
    return normalize_text(address)


def assemble_incident_lookup_response(
    *,
    address: str,
    normalized_address: str,
    location: dict[str, Any],
    incidents: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    events_by_incident: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for event in events:
        events_by_incident[int(event["incident_id"])].append(
            {
                "id": int(event["id"]),
                "event_type": event["event_type"],
                "event_at": event["event_at"],
                "event_label": event["event_label"],
                "metadata": event["metadata"],
            }
        )

    location_payload = {
        "id": int(location["id"]),
        "canonical_address": location["canonical_address"],
        "boro": location["boro"],
        "house_num": location["house_num"],
        "street_name": location["street_name"],
        "from_street": location["from_street"],
        "to_street": location["to_street"],
        "spec_loc": location["spec_loc"],
        "location_key": location["location_key"],
    }

    map_payload = _build_map_payload(
        normalized_address=normalized_address,
        location=location_payload,
        location_row=location,
    )

    incident_items: list[dict[str, Any]] = []
    for incident in incidents:
        incident_id = int(incident["id"])
        incident_items.append(
            {
                "id": incident_id,
                "external_id": incident["external_id"],
                "dataset_name": incident["dataset_name"],
                "source": incident["source"],
                "initiated_by": incident["initiated_by"],
                "reported_at": incident["reported_at"],
                "closed_at": incident["closed_at"],
                "status": incident["status"],
                "raw_payload": incident["raw_payload"],
                "events": events_by_incident.get(incident_id, []),
            }
        )

    return {
        "address": address,
        "normalized_address": normalized_address,
        "location": location_payload,
        "map": map_payload,
        "incidents": incident_items,
        "incident_count": len(incident_items),
        "event_count": len(events),
    }


def _build_map_payload(
    *,
    normalized_address: str,
    location: dict[str, Any],
    location_row: dict[str, Any],
) -> dict[str, Any] | None:
    geometry_geojson = location_row.get("geometry_geojson")
    if not isinstance(geometry_geojson, str) or not geometry_geojson.strip():
        return None

    try:
        geometry = json.loads(geometry_geojson)
    except json.JSONDecodeError:
        return None

    geometry_type = geometry.get("type")
    if geometry_type not in {"LineString", "MultiLineString"}:
        return None

    center = None
    if location_row.get("center_lng") is not None and location_row.get("center_lat") is not None:
        center = [float(location_row["center_lng"]), float(location_row["center_lat"])]

    bbox = None
    bbox_fields = ("min_lng", "min_lat", "max_lng", "max_lat")
    if all(location_row.get(field) is not None for field in bbox_fields):
        bbox = [float(location_row[field]) for field in bbox_fields]

    return {
        "normalized_address": normalized_address,
        "location": location,
        "geometry": geometry,
        "bbox": bbox,
        "center": center,
    }


class IncidentLookupRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def lookup_by_address(self, address: str | None) -> dict[str, Any]:
        normalized_address = normalize_lookup_address(address)
        if normalized_address is None:
            raise ValueError("Address query parameter is required.")

        try:
            with get_db_connection(self.database_url) as connection:
                with connection.cursor() as cursor:
                    location = self._fetch_location(cursor, normalized_address)
                    incidents = self._fetch_incidents(cursor, int(location["id"]))
                    events = self._fetch_events(cursor, [int(incident["id"]) for incident in incidents])
        except IncidentLookupNotFoundError:
            raise
        except IncidentLookupDataError:
            raise
        except Error as exc:
            raise IncidentLookupRepositoryError("Unable to query incident records.") from exc

        return assemble_incident_lookup_response(
            address=address or "",
            normalized_address=normalized_address,
            location=location,
            incidents=incidents,
            events=events,
        )

    def debug_summary(self) -> dict[str, Any]:
        try:
            with get_db_connection(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select current_database() as current_database;")
                    database_row = cursor.fetchone()

                    cursor.execute("select count(*) as count from public.locations;")
                    location_row = cursor.fetchone()

                    cursor.execute("select count(*) as count from public.incidents;")
                    incident_row = cursor.fetchone()

                    cursor.execute("select count(*) as count from public.incident_events;")
                    event_row = cursor.fetchone()

                    cursor.execute(
                        """
                        select
                          id,
                          canonical_address,
                          boro,
                          house_num,
                          street_name,
                          from_street,
                          to_street,
                          spec_loc,
                          location_key
                        from public.locations
                        order by id asc
                        limit 1;
                        """
                    )
                    sample_location = cursor.fetchone()
        except Error as exc:
            raise IncidentLookupRepositoryError("Unable to query incident records.") from exc

        return {
            "current_database": database_row["current_database"],
            "location_count": int(location_row["count"]),
            "incident_count": int(incident_row["count"]),
            "event_count": int(event_row["count"]),
            "sample_location": dict(sample_location) if sample_location is not None else None,
        }

    def debug_lookup_address(self, address: str | None) -> dict[str, Any]:
        normalized_address = normalize_lookup_address(address)
        if normalized_address is None:
            raise ValueError("Address query parameter is required.")

        try:
            with get_db_connection(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        select
                          id,
                          canonical_address,
                          boro,
                          house_num,
                          street_name,
                          from_street,
                          to_street,
                          spec_loc,
                          location_key
                        from public.locations
                        where canonical_address = %s
                        order by id asc;
                        """,
                        (normalized_address,),
                    )
                    matches = [dict(row) for row in cursor.fetchall()]
        except Error as exc:
            raise IncidentLookupRepositoryError("Unable to query incident records.") from exc

        return {
            "input_address": address or "",
            "normalized_address": normalized_address,
            "match_count": len(matches),
            "matches": matches,
        }

    def _fetch_location(self, cursor: Any, normalized_address: str) -> dict[str, Any]:
        cursor.execute(
            """
            select
              id,
              canonical_address,
              boro,
              house_num,
              street_name,
              from_street,
              to_street,
              spec_loc,
              location_key,
              ST_AsGeoJSON(geom) as geometry_geojson,
              ST_XMin(ST_Envelope(geom)) as min_lng,
              ST_YMin(ST_Envelope(geom)) as min_lat,
              ST_XMax(ST_Envelope(geom)) as max_lng,
              ST_YMax(ST_Envelope(geom)) as max_lat,
              ST_X(ST_Centroid(geom)) as center_lng,
              ST_Y(ST_Centroid(geom)) as center_lat
            from public.locations
            where canonical_address = %s
            order by id asc;
            """,
            (normalized_address,),
        )
        rows = cursor.fetchall()

        if not rows:
            raise IncidentLookupNotFoundError("No incident location found for the provided address.")
        if len(rows) > 1:
            raise IncidentLookupDataError("Multiple locations matched the provided address.")

        return dict(rows[0])

    def _fetch_incidents(self, cursor: Any, location_id: int) -> list[dict[str, Any]]:
        cursor.execute(
            """
            select
              id,
              external_id,
              dataset_name,
              source,
              initiated_by,
              reported_at,
              closed_at,
              status,
              raw_payload
            from public.incidents
            where location_id = %s
            order by reported_at desc, id desc;
            """,
            (location_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def _fetch_events(self, cursor: Any, incident_ids: list[int]) -> list[dict[str, Any]]:
        if not incident_ids:
            return []

        cursor.execute(
            """
            select
              id,
              incident_id,
              event_type,
              event_at,
              event_label,
              metadata
            from public.incident_events
            where incident_id = any(%s)
            order by event_at asc, id asc;
            """,
            (incident_ids,),
        )
        return [dict(row) for row in cursor.fetchall()]
