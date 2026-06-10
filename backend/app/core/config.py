"""Application configuration loaded from environment / .env via pydantic-settings.

Everything secret (API keys) and tunable (model names, weights, caps) lives here
so the rest of the codebase never reads os.environ directly.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-relative paths so the app works regardless of the current working dir.
APP_DIR = Path(__file__).resolve().parent.parent          # backend/app
ARTIFACTS_DIR = APP_DIR / "ml" / "artifacts"              # trained model lives here
DATA_DIR = APP_DIR.parent / "data"                        # training CSVs (gitignored)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Secrets (Groq is 100% free; Tavily has a free tier) ----
    groq_api_key: str = ""
    tavily_api_key: str = ""

    # ---- LLM models (Groq free hosted models) ----
    # Bigger model for judging claims, fast small model for cheap extraction.
    assessor_model: str = "llama-3.3-70b-versatile"
    extractor_model: str = "llama-3.1-8b-instant"

    # ---- LLM tuning ----
    llm_temperature: float = 0.1   # low — we want consistent, factual judgments
    llm_max_tokens: int = 1024

    # ---- Retrieval ----
    # "tavily" uses the free-tier API key; "ddgs" is keyless/unlimited DuckDuckGo.
    search_provider: str = "tavily"
    max_claims: int = 5            # check-worthy claims to extract per article
    results_per_claim: int = 3     # evidence snippets to retrieve per claim

    # ---- Fusion (how the two signals combine) ----
    # final_fake_prob = ml_weight * ml_score + (1 - ml_weight) * llm_fake_share
    ml_weight: float = 0.4
    # Bands for the final label off the fused fake-probability.
    fake_threshold: float = 0.60   # >= this -> "fake"
    real_threshold: float = 0.40   # <= this -> "real"; in between -> "uncertain"

    # ---- ML artifacts ----
    model_path: str = str(ARTIFACTS_DIR / "model.pkl")
    vectorizer_path: str = str(ARTIFACTS_DIR / "vectorizer.pkl")

    # ---- Server ----
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
