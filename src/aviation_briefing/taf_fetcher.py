"""Functions to fetch TAFs from remote services."""

from __future__ import annotations

import httpx

from .config import get_settings


async def fetch_raw_taf(station: str) -> str:
    """Fetch a raw TAF string for a station."""

    settings = get_settings()
    params = {"ids": station, "format": "raw", "taf": "true"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.noaa_taf_url, params=params)
        response.raise_for_status()
    return response.text.strip()
