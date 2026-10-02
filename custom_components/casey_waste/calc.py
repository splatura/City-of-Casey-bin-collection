"""Pure date and bin computations for Casey waste collection. No I/O."""
from __future__ import annotations

import re
from datetime import date, timedelta

from .const import (
    BIN_GLASS,
    BIN_GREEN,
    BIN_RECYCLING,
    BIN_RUBBISH,
    DAYS_OF_WEEK,
    GLASS_ANCHOR,
    GLASS_START,
)


_ZONEDESC_RE = re.compile(
    r"^\s*(?P<day>[A-Za-z]+)\s*:.*?Recycling\s+Week\s+(?P<week>\d)"
    r"(?:.*?Glass\s+Week\s+(?P<glass>\d))?",
    re.IGNORECASE,
)
_ZONENAME_RE = re.compile(r"^(?P<day>[A-Za-z]+)_(?P<week>\d)(?P<letter>[AB])?$")


def parse_zone(
    zonename: str | None, zonedesc: str | None
) -> tuple[str | None, str | None, str | None]:
    """Parse a dataset zone into (day, week, glass_week).

    `zonedesc` (e.g. 'Thursday: Recycling Week 2; Garden(FOGO) Week 1; Glass
    Week 1') is preferred; `zonename` (e.g. 'Thursday_2A') is the fallback,
    where A/B picks the first/second FOGO week of the 4-week glass cycle.
    Returns e.g. ('Thursday', '2', '1'); (None, None, None) if unparseable.
    `glass_week` is None when absent or inconsistent with the FOGO phase.
    """
    day = week = glass = None
    match = _ZONEDESC_RE.match(zonedesc or "")
    if match:
        day, week, glass = match["day"].capitalize(), match["week"], match["glass"]
    else:
        match = _ZONENAME_RE.match((zonename or "").strip())
        if match:
            day, week = match["day"].capitalize(), match["week"]
            if match["letter"] and week in ("1", "2"):
                fogo_week = 3 - int(week)
                glass = str(fogo_week + (2 if match["letter"] == "B" else 0))
    if day not in DAYS_OF_WEEK or week not in ("1", "2"):
        return (None, None, None)
    if glass not in ("1", "2", "3", "4") or _glass_fortnight(int(glass)) == int(week):
        # Glass is collected with FOGO, never on the area's recycling week.
        glass = None
    return (day, week, glass)


def _glass_fortnight(glass: int) -> int:
    """Fortnight phase (1 or 2) of a glass week (1-4)."""
    return 1 if glass in (1, 3) else 2


def current_week(day: date, anchor: date) -> int:
    """Fortnight phase (1 or 2) for the week containing `day`.

    `anchor` must be a Monday that falls in a Week-2 collection week.
    """
    week_index = (day - anchor).days // 7
    return 2 if week_index % 2 == 0 else 1


def next_collection_date(today: date, collection_day: str) -> date | None:
    """Next date on/after `today` matching `collection_day`.

    Rubbish is weekly, so the next collection is the next occurrence of the
    area's weekday (today included when it matches).
    """
    if collection_day not in DAYS_OF_WEEK:
        return None
    target = DAYS_OF_WEEK.index(collection_day)
    offset = (target - today.weekday()) % 7
    return today + timedelta(days=offset)


def glass_week(day: date, anchor: date) -> int:
    """Glass phase (1-4) for the week containing `day`.

    `anchor` must be a Monday that falls in a Glass-Week-1 week.
    """
    return (day - anchor).days // 7 % 4 + 1


def _is_glass_day(
    day: date, glass_pattern: str | None, glass_anchor: date, glass_start: date
) -> bool:
    return (
        glass_pattern in ("1", "2", "3", "4")
        and day >= glass_start
        and glass_week(day, glass_anchor) == int(glass_pattern)
    )


def bins_for_date(
    day: date,
    week_pattern: str,
    anchor: date,
    glass_pattern: str | None = None,
    glass_anchor: date = GLASS_ANCHOR,
    glass_start: date = GLASS_START,
) -> list[str]:
    """Bins collected on `day` for an area on `week_pattern` ('1' or '2').

    Rubbish (red) every week; recycling (yellow) when the week's fortnight
    phase matches the area's pattern, otherwise food & garden (green). Glass
    (purple) is added when the week's glass phase matches `glass_pattern`
    ('1'-'4') on or after `glass_start`.
    Returns ``[BIN_RUBBISH]`` only if ``week_pattern`` is unrecognised
    (callers validate the pattern via ``parse_zone`` first).
    """
    bins = [BIN_RUBBISH]
    if week_pattern in ("1", "2"):
        if current_week(day, anchor) == int(week_pattern):
            bins.append(BIN_RECYCLING)
        else:
            bins.append(BIN_GREEN)
    if _is_glass_day(day, glass_pattern, glass_anchor, glass_start):
        bins.append(BIN_GLASS)
    return bins


def next_glass_date(
    today: date,
    collection_day: str,
    glass_pattern: str | None,
    glass_anchor: date = GLASS_ANCHOR,
    glass_start: date = GLASS_START,
) -> date | None:
    """Next glass collection on/after `today` (never before `glass_start`)."""
    if glass_pattern not in ("1", "2", "3", "4"):
        return None
    first = next_collection_date(max(today, glass_start), collection_day)
    if first is None:
        return None
    for weeks in range(4):
        candidate = first + timedelta(weeks=weeks)
        if _is_glass_day(candidate, glass_pattern, glass_anchor, glass_start):
            return candidate
    return None


def night_before(collection_day: str) -> str | None:
    """The day name before `collection_day` (when to put bins out)."""
    if collection_day not in DAYS_OF_WEEK:
        return None
    idx = DAYS_OF_WEEK.index(collection_day)
    return DAYS_OF_WEEK[(idx - 1) % 7]
