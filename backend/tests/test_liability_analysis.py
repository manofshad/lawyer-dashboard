from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from app.services.liability_analysis import (
    OpenAILiabilitySummaryGenerator,
    build_liability_analysis_response,
    build_liability_prompt_payload,
)


def _incident(
    *,
    external_id: str,
    reported_at: date,
    closed_at: date | None,
    status: str = "open",
) -> dict[str, object]:
    return {
        "id": 1,
        "external_id": external_id,
        "dataset_name": "street_pothole_work_orders_closed",
        "source": "CTZ",
        "initiated_by": "CSC",
        "reported_at": reported_at,
        "closed_at": closed_at,
        "status": status,
        "raw_payload": {},
        "events": [],
    }


class _StubSummaryGenerator:
    def __init__(self, summary: str = "Stub summary.") -> None:
        self.summary = summary
        self.payloads = []

    def generate_summary(self, payload):
        self.payloads.append(payload)
        return self.summary


class _FakeCompletions:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self._content = content
        self._error = error

    def create(self, **_: object):
        if self._error is not None:
            raise self._error

        message = type("Message", (), {"content": self._content})
        choice = type("Choice", (), {"message": message})
        return type("Response", (), {"choices": [choice]})


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = _FakeChat(completions)


def test_prompt_payload_is_weak_when_no_incident_reaches_15_days() -> None:
    payload = build_liability_prompt_payload(
        address="145 SMITH STREET",
        client_incident_date=date(2026, 1, 10),
        incidents=[
            _incident(
                external_id="DBSAMPLE0001",
                reported_at=date(2026, 1, 2),
                closed_at=None,
            )
        ],
    )

    assert payload.liability_signal == "likely_not_liable"
    assert payload.case_strength == "weak"
    assert payload.best_matching_incident is None


def test_prompt_payload_is_maybe_when_incident_is_open_15_to_29_days() -> None:
    payload = build_liability_prompt_payload(
        address="145 SMITH STREET",
        client_incident_date=date(2026, 1, 20),
        incidents=[
            _incident(
                external_id="DBSAMPLE0002",
                reported_at=date(2026, 1, 2),
                closed_at=None,
            )
        ],
    )

    assert payload.liability_signal == "likely_liable"
    assert payload.case_strength == "maybe"
    assert payload.best_matching_incident is not None
    assert payload.best_matching_incident.external_id == "DBSAMPLE0002"
    assert payload.best_matching_incident.days_open_as_of_client_incident == 18


def test_prompt_payload_is_strong_when_incident_is_open_30_plus_days() -> None:
    payload = build_liability_prompt_payload(
        address="145 SMITH STREET",
        client_incident_date=date(2026, 2, 10),
        incidents=[
            _incident(
                external_id="DBSAMPLE0003",
                reported_at=date(2026, 1, 2),
                closed_at=None,
            )
        ],
    )

    assert payload.liability_signal == "likely_liable"
    assert payload.case_strength == "strong"
    assert payload.best_matching_incident is not None
    assert payload.best_matching_incident.days_open_as_of_client_incident == 39


def test_prompt_payload_ignores_incident_closed_before_client_incident_date() -> None:
    payload = build_liability_prompt_payload(
        address="145 SMITH STREET",
        client_incident_date=date(2026, 2, 10),
        incidents=[
            _incident(
                external_id="DBSAMPLE0004",
                reported_at=date(2026, 1, 2),
                closed_at=date(2026, 1, 25),
                status="closed",
            )
        ],
    )

    assert payload.liability_signal == "likely_not_liable"
    assert payload.case_strength == "weak"
    assert payload.best_matching_incident is None


def test_prompt_payload_chooses_strongest_matching_incident() -> None:
    payload = build_liability_prompt_payload(
        address="145 SMITH STREET",
        client_incident_date=date(2026, 2, 10),
        incidents=[
            _incident(
                external_id="DBSAMPLE0005",
                reported_at=date(2026, 1, 20),
                closed_at=None,
            ),
            _incident(
                external_id="DBSAMPLE0006",
                reported_at=date(2026, 1, 5),
                closed_at=None,
            ),
        ],
    )

    assert payload.case_strength == "strong"
    assert payload.best_matching_incident is not None
    assert payload.best_matching_incident.external_id == "DBSAMPLE0006"
    assert payload.additional_supporting_incident_count == 1


def test_build_liability_analysis_response_returns_public_payload() -> None:
    summary_generator = _StubSummaryGenerator("The timeline likely supports liability.")

    response = build_liability_analysis_response(
        address="145 SMITH STREET",
        client_incident_date=date(2026, 2, 10),
        incidents=[
            _incident(
                external_id="DBSAMPLE0007",
                reported_at=date(2026, 1, 5),
                closed_at=None,
            )
        ],
        summary_generator=summary_generator,
    )

    assert response.address == "145 SMITH STREET"
    assert response.client_incident_date == date(2026, 2, 10)
    assert response.liability_signal == "likely_liable"
    assert response.case_strength == "strong"
    assert response.best_matching_incident_id == "DBSAMPLE0007"
    assert response.best_matching_days_open == 36
    assert "not legal advice" in response.disclaimer.lower()
    assert summary_generator.payloads[0].case_strength == "strong"


def test_openai_liability_summary_generator_parses_summary() -> None:
    generator = OpenAILiabilitySummaryGenerator(api_key="test-key", model="gpt-test")
    generator._client = _FakeClient(
        _FakeCompletions('{"analysis_summary":"The timeline likely supports liability."}')
    )

    summary = generator.generate_summary(
        build_liability_prompt_payload(
            address="145 SMITH STREET",
            client_incident_date=date(2026, 2, 10),
            incidents=[
                _incident(
                    external_id="DBSAMPLE0008",
                    reported_at=date(2026, 1, 5),
                    closed_at=None,
                )
            ],
        )
    )

    assert summary == "The timeline likely supports liability."


def test_openai_liability_summary_generator_raises_for_invalid_model_output() -> None:
    generator = OpenAILiabilitySummaryGenerator(api_key="test-key", model="gpt-test")
    generator._client = _FakeClient(_FakeCompletions('{"wrong_key":"value"}'))

    with pytest.raises(HTTPException) as exc_info:
        generator.generate_summary(
            build_liability_prompt_payload(
                address="145 SMITH STREET",
                client_incident_date=date(2026, 2, 10),
                incidents=[
                    _incident(
                        external_id="DBSAMPLE0009",
                        reported_at=date(2026, 1, 5),
                        closed_at=None,
                    )
                ],
            )
        )

    assert exc_info.value.status_code == 502
