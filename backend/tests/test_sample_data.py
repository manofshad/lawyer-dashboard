from pathlib import Path

from app.services.sample_data import extract_source_id, load_tiktok_caption_records


def test_extract_source_id_uses_numeric_tiktok_video_id() -> None:
    url = "https://www.tiktok.com/@nck.ryn/video/7397432112430828831"
    assert extract_source_id(url) == "7397432112430828831"


def test_extract_source_id_falls_back_to_full_url() -> None:
    url = "https://www.example.com/no-video-id"
    assert extract_source_id(url) == url


def test_load_tiktok_caption_records_maps_valid_items() -> None:
    records = load_tiktok_caption_records(Path("../Pasted code.json"))

    assert records
    first = records[0]
    assert first.caption_text
    assert first.video_url.startswith("https://")
    assert first.source_id


def test_load_tiktok_caption_records_handles_missing_optional_fields(
    tmp_path: Path,
) -> None:
    data_file = tmp_path / "sample.json"
    data_file.write_text(
        '[{"text":"Don Angie is worth the hype","webVideoUrl":"https://www.tiktok.com/@x/video/123"}]'
    )

    records = load_tiktok_caption_records(data_file)

    assert len(records) == 1
    assert records[0].creator_name is None
    assert records[0].created_at is None
