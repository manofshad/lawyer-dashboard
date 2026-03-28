from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from ..models.extractions import TikTokCaptionRecord


VIDEO_ID_PATTERN = re.compile(r"/video/(\d+)")


def extract_source_id(video_url: str) -> str:
    match = VIDEO_ID_PATTERN.search(video_url)
    if match:
        return match.group(1)
    return video_url


def _normalize_item(item: dict[str, Any]) -> TikTokCaptionRecord:
    caption_text = item.get("text")
    video_url = item.get("webVideoUrl")

    if not isinstance(caption_text, str) or not caption_text.strip():
        raise ValueError("Sample item is missing a usable text field.")
    if not isinstance(video_url, str) or not video_url.strip():
        raise ValueError("Sample item is missing a usable webVideoUrl field.")

    creator_name = item.get("authorMeta.name")
    created_at = item.get("createTimeISO")

    return TikTokCaptionRecord(
        source_id=extract_source_id(video_url),
        caption_text=caption_text.strip(),
        creator_name=creator_name if isinstance(creator_name, str) else None,
        video_url=video_url,
        created_at=created_at if isinstance(created_at, str) else None,
    )


def load_tiktok_caption_records(path: Path) -> list[TikTokCaptionRecord]:
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sample TikTok JSON file not found: {path}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sample TikTok JSON file is not valid JSON: {path}",
        ) from exc

    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sample TikTok JSON must contain a top-level array.",
        )

    records: list[TikTokCaptionRecord] = []
    for index, raw_item in enumerate(payload):
        if not isinstance(raw_item, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sample item at index {index} is not an object.",
            )

        try:
            records.append(_normalize_item(raw_item))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid TikTok sample item at index {index}: {exc}",
            ) from exc

    return records
