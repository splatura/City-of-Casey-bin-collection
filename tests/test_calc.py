"""Unit tests for the pure calc logic."""
from datetime import date

from custom_components.casey_waste import calc
from custom_components.casey_waste.const import (
    BIN_GREEN,
    BIN_RECYCLING,
    BIN_RUBBISH,
    FORTNIGHT_ANCHOR,
)

ANCHOR = FORTNIGHT_ANCHOR  # Monday 2025-10-20, a "Week 2" week


def test_parse_collection_valid():
    assert calc.parse_collection("Thursday_Week_2") == ("Thursday", "2")
    assert calc.parse_collection("Monday_Week_1") == ("Monday", "1")


def test_parse_collection_invalid():
    assert calc.parse_collection("Unknown") == (None, None)
    assert calc.parse_collection("") == (None, None)
    assert calc.parse_collection("Saturday_Week_3") == (None, None)
    assert calc.parse_collection("Funday_Week_1") == (None, None)


def test_current_week_anchor_is_week_2():
    assert calc.current_week(ANCHOR, ANCHOR) == 2
    assert calc.current_week(date(2025, 10, 23), ANCHOR) == 2  # Thu same week
    assert calc.current_week(date(2025, 10, 27), ANCHOR) == 1  # next Monday
    assert calc.current_week(date(2025, 11, 3), ANCHOR) == 2  # two weeks on, cycle wraps
    assert calc.current_week(date(2025, 10, 13), ANCHOR) == 1  # week before anchor
    assert calc.current_week(date(2025, 10, 6), ANCHOR) == 2  # two weeks before anchor


def test_next_collection_date_includes_today():
    # Thu 2025-10-23 is a Thursday -> today
    assert calc.next_collection_date(date(2025, 10, 23), "Thursday") == date(2025, 10, 23)


def test_next_collection_date_future():
    # Mon 2025-10-20 -> next Thursday is 2025-10-23
    assert calc.next_collection_date(date(2025, 10, 20), "Thursday") == date(2025, 10, 23)
    # Fri 2025-10-24 -> next Thursday wraps to 2025-10-30
    assert calc.next_collection_date(date(2025, 10, 24), "Thursday") == date(2025, 10, 30)


def test_next_collection_date_unknown_day():
    assert calc.next_collection_date(date(2025, 10, 20), "Notaday") is None


def test_bins_for_date_week2_matching_gets_recycling():
    # current_week == 2, area pattern "2" -> recycling
    assert calc.bins_for_date(date(2025, 10, 23), "2", ANCHOR) == [BIN_RUBBISH, BIN_RECYCLING]


def test_bins_for_date_week1_nonmatching_gets_green():
    # current_week == 2, area pattern "1" -> green
    assert calc.bins_for_date(date(2025, 10, 23), "1", ANCHOR) == [BIN_RUBBISH, BIN_GREEN]


def test_bins_for_date_alternates_next_week():
    # Following week current_week == 1
    assert calc.bins_for_date(date(2025, 10, 30), "2", ANCHOR) == [BIN_RUBBISH, BIN_GREEN]
    assert calc.bins_for_date(date(2025, 10, 30), "1", ANCHOR) == [BIN_RUBBISH, BIN_RECYCLING]


def test_night_before():
    assert calc.night_before("Thursday") == "Wednesday"
    assert calc.night_before("Monday") == "Sunday"  # wraps
    assert calc.night_before("Notaday") is None
