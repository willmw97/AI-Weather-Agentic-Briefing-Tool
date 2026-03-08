from datetime import datetime

from aviation_briefing.briefing_engine import build_briefing
from aviation_briefing.models import TafRecord


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
