"""Configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    noaa_taf_url: str = "https://aviationweather.gov/api/data/taf"


def get_settings() -> Settings:
    """Load application settings from environment with sensible defaults."""

    return Settings(noaa_taf_url=os.getenv("NOAA_TAF_URL", Settings.noaa_taf_url))
