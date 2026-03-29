from __future__ import annotations

import json
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from openai import OpenAI

from ..models.incidents import LiabilityAnalysisResponse, LiabilityIncidentSummary, LiabilityPromptPayload


LIABILITY_ANALYSIS_SYSTEM_PROMPT = """You are assisting with an internal municipal liability screening tool.

Your job is to write a short, neutral explanation of a precomputed timeline-based screening result. Do not give legal advice. Do not invent facts. Do not change the provided liability result or case strength.

Write 2-4 short bullet points in plain English.

Requirements:
- Explain whether the timeline suggests the city is likely liable or likely not liable.
- Mention the key reason using the dates and number of days the city record remained open before the client incident.
- If case strength is "strong", say the timeline is a strong indicator because the city record remained open 30 or more days before the client incident.
- If case strength is "maybe", say the timeline may support liability because the city record remained open at least 15 days but less than 30 days before the client incident.
- If case strength is "weak", say the available timeline does not show an open city record that had remained unresolved for at least 15 days before the client incident.
- If multiple incidents exist, mention only the strongest supporting one unless the payload says additional records materially support the same conclusion.
- Use cautious phrasing such as "likely" or "may support".
- Do not mention laws, statutes, or legal elements that are not provided in the input.
- Return valid JSON only with schema:
  {"analysis_summary": string}
"""

LIABILITY_ANALYSIS_DISCLAIMER = (
    "This is an internal timeline-based screening aid and not legal advice. "
    "It uses city incident records as a proxy for notice and does not evaluate other legal issues."
)


class OpenAILiabilitySummaryGenerator:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API key is not configured on the backend.",
            )
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate_summary(self, payload: LiabilityPromptPayload) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": LIABILITY_ANALYSIS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(payload.model_dump(mode="json"), ensure_ascii=True),
                    },
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Model returned an empty response.")

            parsed = json.loads(content)
            analysis_summary = parsed.get("analysis_summary")
            if not isinstance(analysis_summary, str) or not analysis_summary.strip():
                raise ValueError("Model returned an invalid analysis summary.")

            return analysis_summary.strip()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI liability analysis request failed.",
            ) from exc


def _days_between_dates(start_date: date, end_date: date) -> int | None:
    diff_days = (end_date - start_date).days
    if diff_days < 0:
        return None
    return diff_days


def summarize_incident_for_client_date(
    incident: dict[str, Any],
    client_incident_date: date,
) -> LiabilityIncidentSummary:
    reported_at = incident["reported_at"]
    closed_at = incident["closed_at"]
    days_open = _days_between_dates(reported_at, client_incident_date)
    was_open_on_client_incident_date = closed_at is None or closed_at > client_incident_date
    qualifies_for_notice_window = (
        days_open is not None and days_open >= 15 and was_open_on_client_incident_date
    )

    return LiabilityIncidentSummary(
        external_id=incident["external_id"],
        reported_at=reported_at,
        closed_at=closed_at,
        status=incident["status"],
        days_open_as_of_client_incident=days_open,
        was_open_on_client_incident_date=was_open_on_client_incident_date,
        qualifies_for_notice_window=qualifies_for_notice_window,
    )


def build_liability_prompt_payload(
    *,
    address: str,
    client_incident_date: date,
    incidents: list[dict[str, Any]],
) -> LiabilityPromptPayload:
    incident_summaries = [
        summarize_incident_for_client_date(incident, client_incident_date) for incident in incidents
    ]
    qualifying_summaries = [
        summary for summary in incident_summaries if summary.qualifies_for_notice_window
    ]
    best_matching_incident = max(
        qualifying_summaries,
        key=lambda summary: summary.days_open_as_of_client_incident or -1,
        default=None,
    )

    if best_matching_incident is None:
        liability_signal = "likely_not_liable"
        case_strength = "weak"
        best_matching_days_open = None
    else:
        best_matching_days_open = best_matching_incident.days_open_as_of_client_incident
        liability_signal = "likely_liable"
        case_strength = "strong" if (best_matching_days_open or 0) >= 30 else "maybe"

    return LiabilityPromptPayload(
        address=address,
        client_incident_date=client_incident_date,
        liability_signal=liability_signal,
        case_strength=case_strength,
        best_matching_incident=best_matching_incident,
        incident_summaries=incident_summaries,
        additional_supporting_incident_count=max(len(qualifying_summaries) - 1, 0),
    )


def build_liability_analysis_response(
    *,
    address: str,
    client_incident_date: date,
    incidents: list[dict[str, Any]],
    summary_generator: OpenAILiabilitySummaryGenerator,
) -> LiabilityAnalysisResponse:
    prompt_payload = build_liability_prompt_payload(
        address=address,
        client_incident_date=client_incident_date,
        incidents=incidents,
    )
    analysis_summary = summary_generator.generate_summary(prompt_payload)

    return LiabilityAnalysisResponse(
        address=address,
        client_incident_date=client_incident_date,
        liability_signal=prompt_payload.liability_signal,
        case_strength=prompt_payload.case_strength,
        best_matching_incident_id=(
            prompt_payload.best_matching_incident.external_id
            if prompt_payload.best_matching_incident is not None
            else None
        ),
        best_matching_days_open=(
            prompt_payload.best_matching_incident.days_open_as_of_client_incident
            if prompt_payload.best_matching_incident is not None
            else None
        ),
        analysis_summary=analysis_summary,
        disclaimer=LIABILITY_ANALYSIS_DISCLAIMER,
    )
