from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:5173"
    supabase_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    sample_tiktok_json_path: str = "Pasted code.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BACKEND_",
        extra="ignore",
    )

    @property
    def sample_tiktok_json_resolved_path(self) -> Path:
        raw_path = Path(self.sample_tiktok_json_path)
        if raw_path.is_absolute():
            return raw_path

        cwd_candidate = Path.cwd() / raw_path
        if cwd_candidate.exists():
            return cwd_candidate

        parent_candidate = Path.cwd().parent / raw_path
        if parent_candidate.exists():
            return parent_candidate

        repo_candidate = Path(__file__).resolve().parents[2] / raw_path
        return repo_candidate


@lru_cache
def get_settings() -> Settings:
    return Settings()
