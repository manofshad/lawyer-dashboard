from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.extractions import (
    RestaurantExtractionItem,
    RestaurantExtractionRequest,
    RestaurantExtractionResponse,
)
from ..services.openai_extractor import OpenAIRestaurantExtractor
from ..services.sample_data import load_tiktok_caption_records
from ..settings import Settings, get_settings


router = APIRouter()


def get_restaurant_extractor(
    settings: Settings = Depends(get_settings),
) -> OpenAIRestaurantExtractor:
    return OpenAIRestaurantExtractor(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


@router.post(
    "/api/extractions/restaurants",
    response_model=RestaurantExtractionResponse,
)
async def extract_restaurants(
    payload: RestaurantExtractionRequest,
    settings: Settings = Depends(get_settings),
    extractor: OpenAIRestaurantExtractor = Depends(get_restaurant_extractor),
) -> RestaurantExtractionResponse:
    records = load_tiktok_caption_records(settings.sample_tiktok_json_resolved_path)
    selected_records = records[payload.offset : payload.offset + payload.limit]

    items = [
        RestaurantExtractionItem(
            source_id=record.source_id,
            caption_text=record.caption_text,
            restaurant_name=extractor.extract_restaurant_name(record).restaurant_name,
            video_url=record.video_url,
            created_at=record.created_at,
        )
        for record in selected_records
    ]

    return RestaurantExtractionResponse(items=items)
