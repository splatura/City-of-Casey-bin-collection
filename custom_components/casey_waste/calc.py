"""Pure date and bin computations for Casey waste collection. No I/O."""
from __future__ import annotations

from datetime import date, timedelta

from .const import BIN_GREEN, BIN_RECYCLING, BIN_RUBBISH, DAYS_OF_WEEK


def parse_collection(collection: str) -> tuple[str | None, str | None]:
    """Parse a dataset 'collection' value like 'Monday_Week_2'.

    Returns (day, week) e.g. ('Monday', '2'); (None, None) if unparseable.
    """
    if not collection or "_" not in collection:
        return (None, None)
    parts = collection.split("_")
    if len(parts) != 3 or parts[1] != "Week":
        return (None, None)
    day, week = parts[0], parts[2]
    if day not in DAYS_OF_WEEK or week not in ("1", "2"):
        return (None, None)
    return (day, week)


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


def bins_for_date(day: date, week_pattern: str, anchor: date) -> list[str]:
    """Bins collected on `day` for an area on `week_pattern` ('1' or '2').

    Rubbish (red) every week; recycling (yellow) when the week's fortnight
    phase matches the area's pattern, otherwise food & garden (green).
    Returns ``[BIN_RUBBISH]`` only if ``week_pattern`` is unrecognised
    (callers validate the pattern via ``parse_collection`` first).
    """
    bins = [BIN_RUBBISH]
    if week_pattern in ("1", "2"):
        if current_week(day, anchor) == int(week_pattern):
            bins.append(BIN_RECYCLING)
        else:
            bins.append(BIN_GREEN)
    return bins


def night_before(collection_day: str) -> str | None:
    """The day name before `collection_day` (when to put bins out)."""
    if collection_day not in DAYS_OF_WEEK:
        return None
    idx = DAYS_OF_WEEK.index(collection_day)
    return DAYS_OF_WEEK[(idx - 1) % 7]
