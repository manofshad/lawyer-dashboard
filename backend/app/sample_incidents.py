from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DATASET_NAME = "street_pothole_work_orders_closed"


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized.upper()


def parse_source_date(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return datetime.strptime(normalized, "%m/%d/%Y").date().isoformat()


def build_canonical_address(house_num: str | None, street_name: str | None) -> str:
    if house_num and street_name:
        return f"{house_num} {street_name}"
    if street_name:
        return street_name
    raise ValueError("street_name is required to build canonical_address")


def build_location_key(
    boro: str | None,
    house_num: str | None,
    street_name: str | None,
    from_street: str | None,
    to_street: str | None,
) -> str:
    return "|".join(
        [
            boro or "",
            house_num or "",
            street_name or "",
            from_street or "",
            to_street or "",
        ]
    )


def event_at(date_value: str | None) -> str | None:
    if date_value is None:
        return None
    return f"{date_value}T00:00:00Z"


def transform_csv_row(row: dict[str, str]) -> dict[str, Any]:
    house_num = normalize_text(row.get("HouseNum"))
    street_name = normalize_text(row.get("OnPrimName"))
    from_street = normalize_text(row.get("FrmPrimNam"))
    to_street = normalize_text(row.get("ToPrimName"))
    spec_loc = normalize_text(row.get("SpecLoc"))
    boro = normalize_text(row.get("Boro"))
    reported_at = parse_source_date(row.get("RptDate"))
    closed_at = parse_source_date(row.get("RptClosed"))

    if street_name is None:
        raise ValueError(f"OnPrimName is required for DefNum={row.get('DefNum')!r}")
    if boro is None:
        raise ValueError(f"Boro is required for DefNum={row.get('DefNum')!r}")
    if reported_at is None:
        raise ValueError(f"RptDate is required for DefNum={row.get('DefNum')!r}")
    if closed_at is None:
        raise ValueError(f"RptClosed is required for DefNum={row.get('DefNum')!r}")

    location = {
        "canonical_address": build_canonical_address(house_num, street_name),
        "boro": boro,
        "house_num": house_num,
        "street_name": street_name,
        "from_street": from_street,
        "to_street": to_street,
        "spec_loc": spec_loc,
        "location_key": build_location_key(boro, house_num, street_name, from_street, to_street),
        "raw_geom_wkt": row["the_geom"],
    }

    incident = {
        "external_id": row["DefNum"],
        "dataset_name": DATASET_NAME,
        "source": normalize_text(row.get("Source")),
        "initiated_by": normalize_text(row.get("InitBy")),
        "reported_at": reported_at,
        "closed_at": closed_at,
        "status": "closed",
        "raw_house_num": row.get("HouseNum") or None,
        "raw_street_name": row.get("OnPrimName") or None,
        "raw_from_street": row.get("FrmPrimNam") or None,
        "raw_to_street": row.get("ToPrimName") or None,
        "raw_spec_loc": row.get("SpecLoc") or None,
        "raw_payload": {
            "the_geom": row.get("the_geom"),
            "DefNum": row.get("DefNum"),
            "InitBy": row.get("InitBy"),
            "HouseNum": row.get("HouseNum") or None,
            "OFT": row.get("OFT"),
            "OnFaceName": row.get("OnFaceName"),
            "OnPrimName": row.get("OnPrimName"),
            "FrmPrimNam": row.get("FrmPrimNam"),
            "ToPrimName": row.get("ToPrimName"),
            "SpecLoc": row.get("SpecLoc") or None,
            "Boro": row.get("Boro"),
            "Source": row.get("Source"),
            "RptDate": row.get("RptDate"),
            "RptClosed": row.get("RptClosed"),
            "Shape_Leng": row.get("Shape_Leng"),
        },
    }

    events = [
        {
            "event_type": "reported",
            "event_at": event_at(reported_at),
            "event_label": "Reported",
            "metadata": {"source_field": "RptDate"},
        },
        {
            "event_type": "closed",
            "event_at": event_at(closed_at),
            "event_label": "Closed",
            "metadata": {"source_field": "RptClosed"},
        },
    ]

    return {"location": location, "incident": incident, "events": events}


def build_sample_incidents(csv_path: Path) -> list[dict[str, Any]]:
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [transform_csv_row(row) for row in reader]


def dump_sample_incidents(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def load_sample_incidents(json_path: Path) -> list[dict[str, Any]]:
    return json.loads(json_path.read_text(encoding="utf-8"))
