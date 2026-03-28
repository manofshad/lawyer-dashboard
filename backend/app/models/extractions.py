from __future__ import annotations

from pydantic import BaseModel, Field


class RestaurantExtractionRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=25)
    offset: int = Field(default=0, ge=0)


class TikTokCaptionRecord(BaseModel):
    source_id: str
    caption_text: str
    creator_name: str | None = None
    video_url: str
    created_at: str | None = None


class RestaurantExtractionResult(BaseModel):
    restaurant_name: str | None


class RestaurantExtractionItem(BaseModel):
    source_id: str
    caption_text: str
    restaurant_name: str | None = None
    video_url: str
    created_at: str | None = None


class RestaurantExtractionResponse(BaseModel):
    items: list[RestaurantExtractionItem]
