"""Minimal parser for TAF headers."""

from __future__ import annotations

from datetime import datetime

from dateutil import parser as dt_parser

from .models import TafRecord


def parse_taf(raw_taf: str) -> TafRecord:
    """Parse a TAF into a normalized TafRecord.

    Expected header format:
    TAF KJFK 031130Z 0312/0418 ...
    """

    parts = raw_taf.split()
    if len(parts) < 4 or parts[0] != "TAF":
        raise ValueError("Unsupported TAF format")

    station = parts[1]
    issued_token = parts[2]
    validity = parts[3]

    issued_at = _parse_issued(issued_token)
    valid_from, valid_to = _parse_validity(validity, issued_at)

    return TafRecord(
        station=station,
        issued_at=issued_at,
        valid_from=valid_from,
        valid_to=valid_to,
        raw_text=raw_taf,
    )


def _parse_issued(token: str) -> datetime:
    day = int(token[0:2])
    hour = int(token[2:4])
    minute = int(token[4:6])
    now = datetime.utcnow()
    iso_value = f"{now.year:04d}-{now.month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00Z"
    return dt_parser.isoparse(iso_value)


def _parse_validity(token: str, issued_at: datetime) -> tuple[datetime, datetime]:
    start_token, end_token = token.split("/")
    start_day = int(start_token[:2])
    start_hour = int(start_token[2:4])
    end_day = int(end_token[:2])
    end_hour = int(end_token[2:4])

    start = issued_at.replace(day=start_day, hour=start_hour, minute=0, second=0)
    end = issued_at.replace(day=end_day, hour=end_hour, minute=0, second=0)
    return start, end
