import pytest
from fastapi import HTTPException

from app.models.extractions import TikTokCaptionRecord
from app.services.openai_extractor import OpenAIRestaurantExtractor


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


def _record() -> TikTokCaptionRecord:
    return TikTokCaptionRecord(
        source_id="7397432112430828831",
        caption_text="Finally tried one of the best restaurants in new york city - Don Angie",
        creator_name="nck.ryn",
        video_url="https://www.tiktok.com/@nck.ryn/video/7397432112430828831",
        created_at="2024-07-30T14:14:54.000Z",
    )


def test_extractor_returns_restaurant_name() -> None:
    extractor = OpenAIRestaurantExtractor(api_key="test-key", model="gpt-test")
    extractor._client = _FakeClient(_FakeCompletions('{"restaurant_name":"Don Angie"}'))

    result = extractor.extract_restaurant_name(_record())

    assert result.restaurant_name == "Don Angie"


def test_extractor_preserves_null_value() -> None:
    extractor = OpenAIRestaurantExtractor(api_key="test-key", model="gpt-test")
    extractor._client = _FakeClient(_FakeCompletions('{"restaurant_name":null}'))

    result = extractor.extract_restaurant_name(_record())

    assert result.restaurant_name is None


def test_extractor_raises_bad_gateway_for_invalid_model_output() -> None:
    extractor = OpenAIRestaurantExtractor(api_key="test-key", model="gpt-test")
    extractor._client = _FakeClient(_FakeCompletions('{"wrong_key":"Don Angie"}'))

    with pytest.raises(HTTPException) as exc_info:
        extractor.extract_restaurant_name(_record())

    assert exc_info.value.status_code == 502
