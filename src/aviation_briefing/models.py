"""Data models for parsed TAF content and generated briefings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TAFPeriod:
    """A forecast period segment from a TAF report."""

    start_utc: datetime
    end_utc: datetime
    wind: str | None = None
    visibility: str | None = None
    weather: str | None = None
    clouds: str | None = None
    probability: int | None = None


@dataclass
class TAFReport:
    """Structured TAF report with parsed validity windows and periods."""

    station: str
    issue_time: datetime
    valid_from: datetime
    valid_to: datetime
    periods: list[TAFPeriod] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class TafRecord:
    """Backward-compatible normalized TAF representation."""

    station: str
    issued_at: datetime
    valid_from: datetime
    valid_to: datetime
    raw_text: str


@dataclass
class Briefing:
    """Generated briefing output."""

    station: str
    summary: str
    hazards: list[str] = field(default_factory=list)


@dataclass
class HazardBucket:
    """Hazards identified for a specific period window."""

    start_utc: datetime
    end_utc: datetime
    hazards: list[str] = field(default_factory=list)


@dataclass
class BriefingOutput:
    """Structured decision-support briefing output."""

    station: str
    executive_summary: str
    time_bucketed_hazards: list[HazardBucket] = field(default_factory=list)
    confidence_statement: str = ""
    operational_recommendations: str = ""
