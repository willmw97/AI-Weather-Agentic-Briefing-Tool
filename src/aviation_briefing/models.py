"""Data models for parsed TAF content and generated briefings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TafRecord(BaseModel):
    """Normalized TAF representation."""

    station: str
    issued_at: datetime
    valid_from: datetime
    valid_to: datetime
    raw_text: str


class Briefing(BaseModel):
    """Generated briefing output."""

    station: str
    summary: str
    hazards: list[str] = Field(default_factory=list)
