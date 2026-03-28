from __future__ import annotations

import json

from fastapi import HTTPException, status
from openai import OpenAI

from ..models.extractions import RestaurantExtractionResult, TikTokCaptionRecord


SYSTEM_PROMPT = """You extract restaurant names from TikTok captions.

Rules:
- Return valid JSON only.
- The JSON schema is: {"restaurant_name": string|null}
- Extract the single clearly named restaurant if one exists.
- Return null when the caption is a ranked list, roundup, or mentions multiple restaurants.
- Return null when the caption only mentions dishes, neighborhoods, generic food descriptions, or vague praise.
- Do not guess.
- Ignore hashtags unless they explicitly name the restaurant.
- Preserve the restaurant's proper capitalization when clear from the caption.
"""


class OpenAIRestaurantExtractor:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API key is not configured on the backend.",
            )
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def extract_restaurant_name(
        self, record: TikTokCaptionRecord
    ) -> RestaurantExtractionResult:
        user_prompt = (
            "Extract the restaurant name from this TikTok caption.\n"
            "If the caption does not name exactly one restaurant, return null.\n\n"
            f"Caption:\n{record.caption_text}"
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Model returned an empty response.")

            parsed = json.loads(content)
            result = RestaurantExtractionResult.model_validate(parsed)
            return result
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI extraction request failed.",
            ) from exc
