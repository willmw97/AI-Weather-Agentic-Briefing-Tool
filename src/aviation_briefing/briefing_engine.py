"""Build human-readable briefings from parsed TAF records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import Briefing, BriefingOutput, HazardBucket, TAFPeriod, TAFReport, TafRecord


class BriefingLLMClient(Protocol):
    """Adapter interface for optional LLM rendering of a briefing."""

    def generate(self, prompt: str) -> str:
        """Return a grounded briefing response for the provided prompt."""


@dataclass(frozen=True)
class _WindowAssessment:
    label: str
    score: int


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


def generate_briefing(
    report: TAFReport,
    window_periods: list[TAFPeriod],
    llm_client: BriefingLLMClient | None = None,
    model_key: str | None = None,
) -> BriefingOutput:
    """Generate decision-support briefing from parsed periods with deterministic fallback."""

    hazard_buckets = _extract_hazard_buckets(window_periods)
    executive_summary = _build_executive_summary(hazard_buckets)
    confidence_statement = _build_confidence_statement(report, window_periods)
    recommendations = _build_operational_recommendations(hazard_buckets)

    if llm_client is not None and model_key:
        prompt = _build_prompt(report, window_periods, hazard_buckets)
        llm_summary = llm_client.generate(prompt).strip()
        if llm_summary:
            executive_summary = llm_summary

    return BriefingOutput(
        station=report.station,
        executive_summary=executive_summary,
        time_bucketed_hazards=hazard_buckets,
        confidence_statement=confidence_statement,
        operational_recommendations=recommendations,
    )


def _extract_hazard_buckets(periods: list[TAFPeriod]) -> list[HazardBucket]:
    buckets: list[HazardBucket] = []

    for period in periods:
        hazards: list[str] = []
        if _has_llws(period):
            hazards.append("LLWS")
        if _has_low_ceiling(period):
            hazards.append("low ceiling")
        if _has_reduced_visibility(period):
            hazards.append("reduced visibility")
        if _has_tsra_risk(period):
            hazards.append("TSRA risk")

        buckets.append(
            HazardBucket(start_utc=period.start_utc, end_utc=period.end_utc, hazards=hazards)
        )

    return buckets


def _build_executive_summary(hazard_buckets: list[HazardBucket]) -> str:
    if not hazard_buckets:
        return "No forecast periods available in the selected window."

    assessments = [_score_bucket(bucket) for bucket in hazard_buckets]
    best = min(assessments, key=lambda a: a.score)
    worst = max(assessments, key=lambda a: a.score)

    return (
        f"Best window: {best.label} ({_score_word(best.score)}). "
        f"Worst window: {worst.label} ({_score_word(worst.score)})."
    )


def _score_bucket(bucket: HazardBucket) -> _WindowAssessment:
    score = 0
    for hazard in bucket.hazards:
        score += {
            "LLWS": 3,
            "low ceiling": 2,
            "reduced visibility": 2,
            "TSRA risk": 3,
        }[hazard]

    label = f"{bucket.start_utc:%d %b %HZ}-{bucket.end_utc:%HZ}"
    return _WindowAssessment(label=label, score=score)


def _score_word(score: int) -> str:
    if score == 0:
        return "most favorable"
    if score <= 2:
        return "manageable hazards"
    if score <= 5:
        return "elevated risk"
    return "highest risk"


def _build_confidence_statement(report: TAFReport, periods: list[TAFPeriod]) -> str:
    if not periods:
        return "Low confidence: no periods available after slicing the requested window."

    complete_periods = [
        p
        for p in periods
        if p.wind is not None and p.visibility is not None and (p.clouds is not None or p.weather is not None)
    ]
    completeness = len(complete_periods) / len(periods)
    prob_periods = sum(1 for p in periods if p.probability is not None)

    level = "High" if completeness >= 0.75 else "Moderate" if completeness >= 0.5 else "Low"
    return (
        f"{level} confidence: {len(complete_periods)}/{len(periods)} periods have core fields "
        f"(wind/vis/weather-cloud layer). {prob_periods} period(s) include PROB groups, "
        "which adds uncertainty to timing and severity."
    )


def _build_operational_recommendations(hazard_buckets: list[HazardBucket]) -> str:
    if not hazard_buckets:
        return "Insufficient period coverage for VFR/IFR suitability hints."

    high_risk = sum(1 for b in hazard_buckets if len(b.hazards) >= 2 or "TSRA risk" in b.hazards)
    if high_risk == 0:
        return "Predominantly VFR-favorable trend; monitor for localized IFR transitions if ceilings/vis degrade."
    if high_risk <= max(1, len(hazard_buckets) // 3):
        return "Mixed VFR/IFR suitability. Consider planning around higher-risk buckets and alternate options."
    return "IFR-leaning operational environment in much of the window; evaluate alternates, fuel, and delay options."


def _has_llws(period: TAFPeriod) -> bool:
    return bool(period.wind and "WS" in period.wind)


def _has_low_ceiling(period: TAFPeriod) -> bool:
    if not period.clouds:
        return False
    tokens = period.clouds.split()
    for token in tokens:
        if token.startswith(("BKN", "OVC", "VV")) and token[-3:].isdigit() and int(token[-3:]) <= 10:
            return True
    return False


def _has_reduced_visibility(period: TAFPeriod) -> bool:
    if not period.visibility:
        return False

    vis = period.visibility
    if vis.endswith("SM"):
        numeric = vis.removesuffix("SM").replace("P", "")
        if "/" in numeric:
            num, den = numeric.split("/", maxsplit=1)
            try:
                value = float(num) / float(den)
            except ValueError:
                return False
            return value < 3
        try:
            return float(numeric) < 3
        except ValueError:
            return False

    if vis.isdigit() and len(vis) == 4:
        return int(vis) < 5000
    return False


def _has_tsra_risk(period: TAFPeriod) -> bool:
    return bool(period.weather and ("TS" in period.weather or "TSRA" in period.weather))


def _build_prompt(report: TAFReport, periods: list[TAFPeriod], hazards: list[HazardBucket]) -> str:
    template = _load_prompt_template()
    period_lines = []
    for idx, period in enumerate(periods, start=1):
        hazard_list = ", ".join(hazards[idx - 1].hazards) or "none"
        period_lines.append(
            "- "
            f"{period.start_utc:%Y-%m-%d %H:%MZ} to {period.end_utc:%H:%MZ}; "
            f"wind={period.wind or 'missing'}, vis={period.visibility or 'missing'}, "
            f"weather={period.weather or 'none'}, clouds={period.clouds or 'none'}, "
            f"prob={period.probability if period.probability is not None else 'none'}, hazards={hazard_list}"
        )

    grounded_data = "\n".join(period_lines) if period_lines else "- No periods in selected window"
    return template.format(station=report.station, periods_block=grounded_data)


def _load_prompt_template() -> str:
    prompt_path = Path(__file__).with_name("prompts") / "taf_briefing.md"
    return prompt_path.read_text(encoding="utf-8")
