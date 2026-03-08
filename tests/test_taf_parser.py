from datetime import datetime, timedelta, timezone

from aviation_briefing.taf_parser import parse_taf, slice_periods_next_24h


def test_parse_taf_supports_fm_tempo_becmg_prob_groups() -> None:
    taf = (
        "TAF KJFK 031130Z 0312/0418 "
        "22012KT P6SM SCT025 "
        "TEMPO 0312/0316 3SM -RA BKN015 "
        "FM031600 24018G28KT P6SM SCT030 "
        "BECMG 0320/0322 28012KT "
        "PROB30 0400/0404 2SM TSRA BKN012CB"
    )

    report = parse_taf(taf)

    assert report.station == "KJFK"
    assert report.valid_from.day == 3
    assert report.valid_to.day == 4
    assert any(p.probability == 30 for p in report.periods)
    assert any(p.start_utc.hour == 16 for p in report.periods)
    assert any(p.weather == "-RA" for p in report.periods)


def test_slice_periods_next_24h_handles_overlap_clipping() -> None:
    taf = (
        "TAF KDEN 312300Z 0100/0206 "
        "22012KT P6SM SCT025 "
        "FM010600 26020KT P6SM FEW050 "
        "TEMPO 0110/0114 2SM -SN BKN015"
    )
    report = parse_taf(taf)

    now_utc = datetime(report.valid_from.year, report.valid_from.month, 1, 5, 0, tzinfo=timezone.utc)
    sliced = slice_periods_next_24h(report, now_utc)

    assert sliced
    assert all(p.end_utc > now_utc for p in sliced)
    assert all(p.start_utc < now_utc + timedelta(hours=24) for p in sliced)


def test_parse_taf_handles_midnight_rollover_and_no_tempo() -> None:
    taf = "TAF KSEA 312330Z 0100/0124 18008KT P6SM OVC030 FM011200 21010KT P6SM SCT040"

    report = parse_taf(taf)

    assert report.valid_from.day == 1
    assert report.valid_to.day == 2
    assert len(report.periods) == 2
    assert all(period.probability is None for period in report.periods)


def test_parse_taf_rejects_invalid_input() -> None:
    invalid = "METAR KJFK 031130Z"

    try:
        parse_taf(invalid)
    except ValueError as exc:
        assert "Unsupported TAF format" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid TAF")
