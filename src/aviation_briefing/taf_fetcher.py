"""Functions to fetch TAFs from remote services."""

from __future__ import annotations

import httpx

from .config import get_settings


def fetch_taf(station_id: str) -> str:
    """Fetch a raw TAF string for a station via configured provider URL."""

    settings = get_settings()
    params = {"ids": station_id, "format": "raw", "taf": "true"}
    with httpx.Client(timeout=10.0) as client:
        response = client.get(settings.noaa_taf_url, params=params)
        response.raise_for_status()
    return response.text.strip()


async def fetch_raw_taf(station: str) -> str:
    """Async wrapper retained for CLI compatibility."""

    settings = get_settings()
    params = {"ids": station, "format": "raw", "taf": "true"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.noaa_taf_url, params=params)
        response.raise_for_status()
    return response.text.strip()
