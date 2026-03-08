"""Parser for TAF reports and period slicing utilities."""

from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from .models import TAFPeriod, TAFReport

_FM_RE = re.compile(r"^FM(\d{2})(\d{2})(\d{2})$")
_RANGE_RE = re.compile(r"^(\d{2})(\d{2})/(\d{2})(\d{2})$")
_PROB_RE = re.compile(r"^PROB(30|40)$")
_WIND_RE = re.compile(r"^(VRB|\d{3})\d{2,3}(G\d{2,3})?KT$")
_VIS_RE = re.compile(r"^(P?\d{1,2}(?:/\d)?SM|\d{4})$")
_CLOUD_RE = re.compile(r"^(FEW|SCT|BKN|OVC|VV|SKC|NSC)")
_WEATHER_RE = re.compile(r"^[+-]?(?:MI|PR|BC|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+$")
_CHANGE_PREFIXES = ("FM", "TEMPO", "BECMG", "PROB30", "PROB40")


def parse_taf(raw_taf: str) -> TAFReport:
    """Parse a TAF string into a structured TAFReport."""

    tokens = raw_taf.split()
    if len(tokens) < 4 or tokens[0] != "TAF":
        raise ValueError("Unsupported TAF format")

    offset = 1
    if tokens[offset] in {"AMD", "COR"}:
        offset += 1

    station = tokens[offset]
    issue_time = _parse_issue_time(tokens[offset + 1])
    valid_from, valid_to = _parse_validity(tokens[offset + 2], issue_time)

    body_tokens = tokens[offset + 3 :]
    periods = _parse_periods(body_tokens, valid_from, valid_to)

    return TAFReport(
        station=station,
        issue_time=issue_time,
        valid_from=valid_from,
        valid_to=valid_to,
        periods=periods,
        raw_text=raw_taf,
    )


def slice_periods_next_24h(report: TAFReport, now_utc: datetime) -> list[TAFPeriod]:
    """Return periods that overlap with [now_utc, now_utc + 24h], clipped to window."""

    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    window_end = now_utc + timedelta(hours=24)

    sliced: list[TAFPeriod] = []
    for period in report.periods:
        if period.end_utc <= now_utc or period.start_utc >= window_end:
            continue
        sliced.append(
            replace(
                period,
                start_utc=max(period.start_utc, now_utc),
                end_utc=min(period.end_utc, window_end),
            )
        )
    return sliced


def _parse_periods(tokens: list[str], valid_from: datetime, valid_to: datetime) -> list[TAFPeriod]:
    groups: list[dict] = []
    idx = 0

    base_tokens: list[str] = []
    while idx < len(tokens) and not _is_change_token(tokens[idx]):
        base_tokens.append(tokens[idx])
        idx += 1

    groups.append({"kind": "BASE", "tokens": base_tokens, "start": valid_from, "end": valid_to, "prob": None})

    while idx < len(tokens):
        token = tokens[idx]
        if _FM_RE.match(token):
            fm_dt = _parse_fm_time(token, valid_from)
            idx += 1
            group_tokens: list[str] = []
            while idx < len(tokens) and not _is_change_token(tokens[idx]):
                group_tokens.append(tokens[idx])
                idx += 1
            groups.append({"kind": "FM", "tokens": group_tokens, "start": fm_dt, "end": valid_to, "prob": None})
            continue

        if token in {"TEMPO", "BECMG"}:
            if idx + 1 >= len(tokens):
                break
            start, end = _parse_range(tokens[idx + 1], valid_from)
            idx += 2
            group_tokens = []
            while idx < len(tokens) and not _is_change_token(tokens[idx]):
                group_tokens.append(tokens[idx])
                idx += 1
            groups.append({"kind": token, "tokens": group_tokens, "start": start, "end": end, "prob": None})
            continue

        prob_match = _PROB_RE.match(token)
        if prob_match:
            probability = int(prob_match.group(1))
            idx += 1
            if idx < len(tokens) and tokens[idx] == "TEMPO":
                idx += 1
            if idx >= len(tokens):
                break
            start, end = _parse_range(tokens[idx], valid_from)
            idx += 1
            group_tokens = []
            while idx < len(tokens) and not _is_change_token(tokens[idx]):
                group_tokens.append(tokens[idx])
                idx += 1
            groups.append({"kind": "PROB", "tokens": group_tokens, "start": start, "end": end, "prob": probability})
            continue

        idx += 1

    groups.sort(key=lambda g: g["start"])
    for i, group in enumerate(groups):
        if group["kind"] in {"BASE", "FM"} and i + 1 < len(groups):
            next_start = groups[i + 1]["start"]
            group["end"] = min(group["end"], next_start)

    periods = []
    for group in groups:
        if group["start"] >= group["end"]:
            continue
        wind, visibility, weather, clouds = _extract_conditions(group["tokens"])
        periods.append(
            TAFPeriod(
                start_utc=group["start"],
                end_utc=group["end"],
                wind=wind,
                visibility=visibility,
                weather=weather,
                clouds=clouds,
                probability=group["prob"],
            )
        )
    return periods


def _extract_conditions(tokens: list[str]) -> tuple[str | None, str | None, str | None, str | None]:
    wind = next((t for t in tokens if _WIND_RE.match(t)), None)
    visibility = next((t for t in tokens if _VIS_RE.match(t)), None)
    weather_tokens = [t for t in tokens if _WEATHER_RE.match(t) and not _CLOUD_RE.match(t)]
    cloud_tokens = [t for t in tokens if _CLOUD_RE.match(t)]
    weather = " ".join(weather_tokens) if weather_tokens else None
    clouds = " ".join(cloud_tokens) if cloud_tokens else None
    return wind, visibility, weather, clouds


def _parse_issue_time(token: str) -> datetime:
    if not token.endswith("Z") or len(token) < 7:
        raise ValueError("Unsupported TAF issue time")

    day = int(token[0:2])
    hour = int(token[2:4])
    minute = int(token[4:6])
    now = datetime.now(timezone.utc)
    candidate = _resolve_day(day, now, hour, minute)
    return candidate


def _parse_validity(token: str, reference: datetime) -> tuple[datetime, datetime]:
    match = _RANGE_RE.match(token)
    if not match:
        raise ValueError("Unsupported TAF validity token")

    start_day, start_hour, end_day, end_hour = map(int, match.groups())
    start = _resolve_day(start_day, reference, start_hour, 0)
    end = _resolve_day(end_day, start, 0 if end_hour == 24 else end_hour, 0)
    if end_hour == 24:
        end += timedelta(days=1)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _parse_range(token: str, reference: datetime) -> tuple[datetime, datetime]:
    match = _RANGE_RE.match(token)
    if not match:
        raise ValueError(f"Unsupported range token: {token}")
    start_day, start_hour, end_day, end_hour = map(int, match.groups())
    start = _resolve_day(start_day, reference, start_hour, 0)
    end = _resolve_day(end_day, start, 0 if end_hour == 24 else end_hour, 0)
    if end_hour == 24:
        end += timedelta(days=1)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _parse_fm_time(token: str, reference: datetime) -> datetime:
    match = _FM_RE.match(token)
    if not match:
        raise ValueError(f"Invalid FM token: {token}")
    day, hour, minute = map(int, match.groups())
    return _resolve_day(day, reference, hour, minute)


def _is_change_token(token: str) -> bool:
    return token.startswith(_CHANGE_PREFIXES)


def _resolve_day(day: int, reference: datetime, hour: int, minute: int) -> datetime:
    tz = reference.tzinfo or timezone.utc
    year = reference.year
    month = reference.month
    max_day = monthrange(year, month)[1]

    if day > max_day:
        month += 1
        if month > 12:
            month = 1
            year += 1

    candidate = datetime(year, month, min(day, monthrange(year, month)[1]), hour, minute, tzinfo=tz)
    delta_days = (candidate - reference).days

    if delta_days > 20:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        candidate = datetime(year, month, min(day, monthrange(year, month)[1]), hour, minute, tzinfo=tz)
    elif delta_days < -20:
        month += 1
        if month > 12:
            month = 1
            year += 1
        candidate = datetime(year, month, min(day, monthrange(year, month)[1]), hour, minute, tzinfo=tz)

    return candidate
