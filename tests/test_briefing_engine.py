from datetime import datetime, timezone

from aviation_briefing.briefing_engine import build_briefing, generate_briefing
from aviation_briefing.models import TAFPeriod, TAFReport, TafRecord


def test_build_briefing_includes_hazards() -> None:
    record = TafRecord(
        station="KDEN",
        issued_at=datetime(2026, 5, 3, 11, 30),
        valid_from=datetime(2026, 5, 3, 12, 0),
        valid_to=datetime(2026, 5, 4, 18, 0),
        raw_text="TAF KDEN 031130Z 0312/0418 TSRA WS020/22040KT",
    )

    briefing = build_briefing(record)

    assert "Hazards" in briefing.summary
    assert "Thunderstorms" in briefing.hazards
    assert "Wind shear" in briefing.hazards


def test_build_briefing_no_hazards_message() -> None:
    record = TafRecord(
        station="KPHX",
        issued_at=datetime(2026, 5, 3, 11, 30),
        valid_from=datetime(2026, 5, 3, 12, 0),
        valid_to=datetime(2026, 5, 4, 18, 0),
        raw_text="TAF KPHX 031130Z 0312/0418 SKC",
    )

    briefing = build_briefing(record)

    assert briefing.hazards == []
    assert "No significant hazards" in briefing.summary


def test_generate_briefing_extracts_hazards_by_bucket() -> None:
    period_1 = TAFPeriod(
        start_utc=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        end_utc=datetime(2026, 5, 3, 16, 0, tzinfo=timezone.utc),
        wind="WS020/22040KT",
        visibility="2SM",
        weather="TSRA",
        clouds="BKN008",
    )
    period_2 = TAFPeriod(
        start_utc=datetime(2026, 5, 3, 16, 0, tzinfo=timezone.utc),
        end_utc=datetime(2026, 5, 3, 20, 0, tzinfo=timezone.utc),
        wind="22012KT",
        visibility="P6SM",
        weather="-RA",
        clouds="SCT040",
    )
    report = TAFReport(
        station="KSEA",
        issue_time=datetime(2026, 5, 3, 11, 30, tzinfo=timezone.utc),
        valid_from=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        valid_to=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
        periods=[period_1, period_2],
        raw_text="",
    )

    briefing = generate_briefing(report, [period_1, period_2], llm_client=None, model_key=None)

    assert briefing.station == "KSEA"
    assert briefing.time_bucketed_hazards[0].hazards == [
        "LLWS",
        "low ceiling",
        "reduced visibility",
        "TSRA risk",
    ]
    assert briefing.time_bucketed_hazards[1].hazards == []


def test_generate_briefing_fallback_is_deterministic_without_llm() -> None:
    period = TAFPeriod(
        start_utc=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        end_utc=datetime(2026, 5, 3, 18, 0, tzinfo=timezone.utc),
        wind="24010KT",
        visibility="P6SM",
        weather=None,
        clouds="FEW050",
        probability=30,
    )
    report = TAFReport(
        station="KPHX",
        issue_time=datetime(2026, 5, 3, 11, 30, tzinfo=timezone.utc),
        valid_from=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        valid_to=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
        periods=[period],
        raw_text="",
    )

    briefing = generate_briefing(report, [period], llm_client=None, model_key=None)

    assert briefing.executive_summary == (
        "Best window: 03 May 12Z-18Z (most favorable). "
        "Worst window: 03 May 12Z-18Z (most favorable)."
    )
    assert "PROB groups" in briefing.confidence_statement
    assert "VFR" in briefing.operational_recommendations
