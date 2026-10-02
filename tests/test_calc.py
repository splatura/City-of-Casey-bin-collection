"""Unit tests for the pure calc logic."""
from datetime import date, timedelta

from custom_components.casey_waste import calc
from custom_components.casey_waste.const import (
    BIN_GLASS,
    BIN_GREEN,
    BIN_RECYCLING,
    BIN_RUBBISH,
    FORTNIGHT_ANCHOR,
    GLASS_ANCHOR,
    GLASS_START,
)

ANCHOR = FORTNIGHT_ANCHOR  # Monday 2025-10-20, a "Week 2" week


def test_parse_zone_from_zonedesc():
    desc = "Thursday: Recycling Week 2; Garden(FOGO) Week 1; Glass Week 1"
    assert calc.parse_zone("Thursday_2A", desc) == ("Thursday", "2", "1")
    desc = "Monday: Recycling Week 1; Garden(FOGO) Week 2; Glass Week 4"
    assert calc.parse_zone("Monday_1B", desc) == ("Monday", "1", "4")


def test_parse_zone_falls_back_to_zonename():
    # A/B letter -> glass week: A is the first FOGO week of the 4-week cycle.
    assert calc.parse_zone("Thursday_2A", "") == ("Thursday", "2", "1")
    assert calc.parse_zone("Thursday_2B", None) == ("Thursday", "2", "3")
    assert calc.parse_zone("Friday_1A", "") == ("Friday", "1", "2")
    assert calc.parse_zone("Friday_1B", "") == ("Friday", "1", "4")


def test_parse_zone_zonename_without_glass_letter():
    assert calc.parse_zone("Tuesday_1", "") == ("Tuesday", "1", None)


def test_parse_zone_invalid():
    assert calc.parse_zone("", "") == (None, None, None)
    assert calc.parse_zone(None, None) == (None, None, None)
    assert calc.parse_zone("Unknown", "garbage") == (None, None, None)
    assert calc.parse_zone("Saturday_3A", "") == (None, None, None)
    assert calc.parse_zone("Funday_1A", "") == (None, None, None)


def test_parse_zone_rejects_glass_on_recycling_week():
    # Glass rides with FOGO; a glass week in the recycling phase is inconsistent.
    desc = "Thursday: Recycling Week 2; Garden(FOGO) Week 1; Glass Week 2"
    assert calc.parse_zone("Thursday_2A", desc) == ("Thursday", "2", None)


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


def test_glass_week_cycle():
    assert calc.glass_week(GLASS_ANCHOR, GLASS_ANCHOR) == 1
    assert calc.glass_week(date(2026, 11, 26), GLASS_ANCHOR) == 1  # Thu same week
    assert calc.glass_week(date(2026, 11, 30), GLASS_ANCHOR) == 2
    assert calc.glass_week(date(2026, 12, 7), GLASS_ANCHOR) == 3
    assert calc.glass_week(date(2026, 12, 14), GLASS_ANCHOR) == 4
    assert calc.glass_week(date(2026, 12, 21), GLASS_ANCHOR) == 1  # wraps
    assert calc.glass_week(date(2026, 11, 2), GLASS_ANCHOR) == 2  # before anchor


def test_glass_weeks_align_with_fogo_phase():
    # Glass weeks 1/3 fall in fortnight week 1, glass weeks 2/4 in fortnight week 2.
    for offset in range(0, 52 * 7, 7):
        day = GLASS_ANCHOR + timedelta(days=offset)
        g = calc.glass_week(day, GLASS_ANCHOR)
        assert calc.current_week(day, ANCHOR) == (1 if g in (1, 3) else 2)


def test_bins_for_date_includes_glass_on_matching_week():
    # Council: 42 Central Parkway (Thursday_2A) first glass 26 Nov, then 24 Dec.
    for d in (date(2026, 11, 26), date(2026, 12, 24)):
        assert calc.bins_for_date(d, "2", ANCHOR, "1") == [BIN_RUBBISH, BIN_GREEN, BIN_GLASS]
    # FOGO week but the other glass week -> no glass.
    assert calc.bins_for_date(date(2026, 12, 10), "2", ANCHOR, "1") == [BIN_RUBBISH, BIN_GREEN]


def test_bins_for_date_no_glass_before_service_start():
    # 29 Oct 2026 is a Glass-Week-1 Thursday, but the service hasn't started.
    assert date(2026, 10, 29) < GLASS_START
    assert calc.bins_for_date(date(2026, 10, 29), "2", ANCHOR, "1") == [BIN_RUBBISH, BIN_GREEN]
    # First week of service: council says 142 Central Parkway (Week 1, glass week 2) gets 5 Nov.
    assert calc.bins_for_date(date(2026, 11, 5), "1", ANCHOR, "2") == [BIN_RUBBISH, BIN_GREEN, BIN_GLASS]


def test_bins_for_date_without_glass_pattern():
    assert calc.bins_for_date(date(2026, 11, 26), "2", ANCHOR) == [BIN_RUBBISH, BIN_GREEN]


def test_next_glass_date():
    # From before the service, the first Thursday glass for 42 Central Parkway is 26 Nov.
    assert calc.next_glass_date(date(2026, 10, 2), "Thursday", "1") == date(2026, 11, 26)
    assert calc.next_glass_date(date(2026, 11, 26), "Thursday", "1") == date(2026, 11, 26)
    assert calc.next_glass_date(date(2026, 11, 27), "Thursday", "1") == date(2026, 12, 24)
    assert calc.next_glass_date(date(2026, 10, 2), "Thursday", "2") == date(2026, 11, 5)
    assert calc.next_glass_date(date(2026, 10, 2), "Thursday", None) is None
    assert calc.next_glass_date(date(2026, 10, 2), "Notaday", "1") is None
