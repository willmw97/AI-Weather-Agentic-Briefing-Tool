from aviation_briefing.taf_parser import parse_taf


def test_parse_taf_parses_header_fields() -> None:
    taf = "TAF KJFK 031130Z 0312/0418 22012KT P6SM SCT025"

    record = parse_taf(taf)

    assert record.station == "KJFK"
    assert record.valid_from.day == 3
    assert record.valid_to.day == 4


def test_parse_taf_rejects_invalid_input() -> None:
    invalid = "METAR KJFK 031130Z"

    try:
        parse_taf(invalid)
    except ValueError as exc:
        assert "Unsupported TAF format" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid TAF")
