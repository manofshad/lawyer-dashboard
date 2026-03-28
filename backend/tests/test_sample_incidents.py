from __future__ import annotations

from datetime import date
from pathlib import Path

from app.sample_incidents import build_sample_incidents, load_sample_incidents


def test_build_sample_incidents_creates_expected_shape() -> None:
    records = build_sample_incidents(Path("street-pothole-sample-10.csv"))

    assert len(records) == 10

    first = records[0]
    assert first["location"]["canonical_address"] == "145 SMITH STREET"
    assert first["location"]["location_key"] == "B|145|SMITH STREET|ATLANTIC AVENUE|PACIFIC STREET"
    assert first["incident"]["external_id"] == "DBSAMPLE0001"
    assert first["incident"]["reported_at"] == "2026-01-02"
    assert first["incident"]["closed_at"] == "2026-01-06"
    assert [event["event_type"] for event in first["events"]] == ["reported", "closed"]
    assert first["events"][0]["event_at"] == "2026-01-02T00:00:00Z"
    assert first["events"][1]["event_at"] == "2026-01-06T00:00:00Z"


def test_sample_json_matches_transformed_csv() -> None:
    csv_records = build_sample_incidents(Path("street-pothole-sample-10.csv"))
    json_records = load_sample_incidents(Path("sample_incidents.json"))

    assert json_records == csv_records


def test_five_records_took_more_than_fifteen_days() -> None:
    records = build_sample_incidents(Path("street-pothole-sample-10.csv"))

    slow_records = [
        record
        for record in records
        if (
            date.fromisoformat(record["incident"]["closed_at"])
            - date.fromisoformat(record["incident"]["reported_at"])
        ).days
        > 15
    ]

    assert [record["incident"]["external_id"] for record in slow_records] == [
        "DBSAMPLE0002",
        "DBSAMPLE0004",
        "DBSAMPLE0006",
        "DBSAMPLE0008",
        "DBSAMPLE0010",
    ]
