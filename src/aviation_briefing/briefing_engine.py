"""Build human-readable briefings from parsed TAF records."""

from __future__ import annotations

from .models import Briefing, TAFReport, TafRecord


def build_briefing(record: TafRecord | TAFReport) -> Briefing:
    """Generate a basic weather briefing summary from a parsed TAF record."""

    text = record.raw_text.upper()
    hazards: list[str] = []

    for hazard_token, label in [
        ("TS", "Thunderstorms"),
        ("FZ", "Freezing precipitation"),
        ("WS", "Wind shear"),
        ("IFR", "Potential IFR conditions"),
    ]:
        if hazard_token in text:
            hazards.append(label)

    summary = (
        f"{record.station}: valid {record.valid_from:%d %b %H%MZ} to "
        f"{record.valid_to:%d %b %H%MZ}."
    )

    if hazards:
        summary += " Hazards: " + ", ".join(hazards) + "."
    else:
        summary += " No significant hazards detected from token scan."

    return Briefing(station=record.station, summary=summary, hazards=hazards)
