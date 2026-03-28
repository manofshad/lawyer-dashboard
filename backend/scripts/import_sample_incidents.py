from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.sample_incidents import load_sample_incidents
from app.settings import get_settings


UPSERT_LOCATION_SQL = """
insert into public.locations (
  canonical_address,
  boro,
  house_num,
  street_name,
  from_street,
  to_street,
  spec_loc,
  location_key,
  raw_geom_wkt,
  geom
)
values (
  %(canonical_address)s,
  %(boro)s,
  %(house_num)s,
  %(street_name)s,
  %(from_street)s,
  %(to_street)s,
  %(spec_loc)s,
  %(location_key)s,
  %(raw_geom_wkt)s,
  ST_GeomFromText(%(raw_geom_wkt)s, 4326)
)
on conflict (location_key) do update
set
  canonical_address = excluded.canonical_address,
  boro = excluded.boro,
  house_num = excluded.house_num,
  street_name = excluded.street_name,
  from_street = excluded.from_street,
  to_street = excluded.to_street,
  spec_loc = excluded.spec_loc,
  raw_geom_wkt = excluded.raw_geom_wkt,
  geom = excluded.geom
returning id;
"""

UPSERT_INCIDENT_SQL = """
insert into public.incidents (
  location_id,
  external_id,
  dataset_name,
  source,
  initiated_by,
  reported_at,
  closed_at,
  status,
  raw_house_num,
  raw_street_name,
  raw_from_street,
  raw_to_street,
  raw_spec_loc,
  raw_payload
)
values (
  %(location_id)s,
  %(external_id)s,
  %(dataset_name)s,
  %(source)s,
  %(initiated_by)s,
  %(reported_at)s,
  %(closed_at)s,
  %(status)s,
  %(raw_house_num)s,
  %(raw_street_name)s,
  %(raw_from_street)s,
  %(raw_to_street)s,
  %(raw_spec_loc)s,
  %(raw_payload)s
)
on conflict (external_id) do update
set
  location_id = excluded.location_id,
  dataset_name = excluded.dataset_name,
  source = excluded.source,
  initiated_by = excluded.initiated_by,
  reported_at = excluded.reported_at,
  closed_at = excluded.closed_at,
  status = excluded.status,
  raw_house_num = excluded.raw_house_num,
  raw_street_name = excluded.raw_street_name,
  raw_from_street = excluded.raw_from_street,
  raw_to_street = excluded.raw_to_street,
  raw_spec_loc = excluded.raw_spec_loc,
  raw_payload = excluded.raw_payload
returning id;
"""

INSERT_EVENT_SQL = """
insert into public.incident_events (
  incident_id,
  event_type,
  event_at,
  event_label,
  metadata
)
select
  %(incident_id)s,
  %(event_type)s,
  %(event_at)s,
  %(event_label)s,
  %(metadata)s
where not exists (
  select 1
  from public.incident_events
  where incident_id = %(incident_id)s
    and event_type = %(event_type)s
    and event_at = %(event_at)s
);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import normalized sample incident JSON into the Postgres database."
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path("sample_incidents.json"),
        help="Path to the normalized JSON artifact.",
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Postgres connection string. Defaults to BACKEND_DATABASE_URL from backend/.env.",
    )
    return parser.parse_args()


def get_database_url(cli_value: str) -> str:
    database_url = cli_value.strip() or get_settings().database_url.strip()
    if not database_url:
        raise SystemExit(
            "Missing database URL. Pass --database-url or set BACKEND_DATABASE_URL in backend/.env."
        )
    return database_url


def upsert_location(cursor: Any, location: dict[str, Any]) -> int:
    cursor.execute(UPSERT_LOCATION_SQL, location)
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Location upsert did not return an id.")
    return int(row["id"])


def upsert_incident(cursor: Any, incident: dict[str, Any], location_id: int) -> int:
    params = dict(incident)
    params["location_id"] = location_id
    params["raw_payload"] = Jsonb(params["raw_payload"])
    cursor.execute(UPSERT_INCIDENT_SQL, params)
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Incident upsert did not return an id.")
    return int(row["id"])


def insert_events(cursor: Any, events: list[dict[str, Any]], incident_id: int) -> int:
    inserted_count = 0
    for event in events:
        params = dict(event)
        params["incident_id"] = incident_id
        params["metadata"] = Jsonb(params["metadata"])
        cursor.execute(INSERT_EVENT_SQL, params)
        inserted_count += cursor.rowcount
    return inserted_count


def import_records(records: list[dict[str, Any]], database_url: str) -> dict[str, int]:
    location_count = 0
    incident_count = 0
    event_count = 0

    with connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            for record in records:
                location_id = upsert_location(cursor, record["location"])
                location_count += 1
                incident_id = upsert_incident(cursor, record["incident"], location_id)
                incident_count += 1
                event_count += insert_events(cursor, record["events"], incident_id)

        connection.commit()

    return {
        "processed_locations": location_count,
        "processed_incidents": incident_count,
        "inserted_events": event_count,
    }


def main() -> None:
    args = parse_args()
    database_url = get_database_url(args.database_url)
    records = load_sample_incidents(args.json_path)
    summary = import_records(records, database_url)
    print(summary)


if __name__ == "__main__":
    main()
