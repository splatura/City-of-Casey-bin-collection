"""Constants for the City of Casey Waste Collection integration."""
from __future__ import annotations

from datetime import date, timedelta

DOMAIN = "casey_waste"

# External endpoints
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "HomeAssistantCaseyWaste/1.0"
CASEY_WASTE_API = (
    "https://data.casey.vic.gov.au/api/explore/v2.1/catalog/"
    "datasets/waste-collection-area/records"
)

# City of Casey collection model (verified against the council schedule):
#   - Rubbish (red lid): WEEKLY, every collection day.
#   - Recycling (yellow) and Food & Garden / FOGO (green): FORTNIGHTLY, alternating.
#   - Glass (purple): every FOUR weeks, on every second FOGO day (from Nov 2026).
# The dataset's zone (e.g. zonename "Thursday_2A", zonedesc "Thursday: Recycling
# Week 2; Garden(FOGO) Week 1; Glass Week 1") gives the area's recycling
# fortnight phase (1/2) and its glass phase (1-4) within a 4-week cycle.
# FORTNIGHT_ANCHOR is a Monday in a "Week 2" collection week
# (validated: Thu 23 Oct 2025, Week-2 areas received recycling; re-validated
# against the council's address search: Thu 8 Oct 2026 recycling for Week 2).
FORTNIGHT_ANCHOR = date(2025, 10, 20)
# GLASS_ANCHOR is a Monday in a "Glass Week 1" week (council address search:
# Thursday_2A's first glass collection is Thu 26 Nov 2026). Glass weeks 1/3
# fall in fortnight week 1, glass weeks 2/4 in fortnight week 2.
GLASS_ANCHOR = date(2026, 11, 23)
# Glass collections start the week of Mon 2 Nov 2026; none before then.
GLASS_START = date(2026, 11, 2)

DEFAULT_SCAN_INTERVAL = timedelta(days=1)

DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# Bin labels
BIN_RUBBISH = "Rubbish (red lid)"
BIN_RECYCLING = "Recycling (yellow lid)"
BIN_GREEN = "Food & Garden (green lid)"
BIN_GLASS = "Glass (purple lid)"

# Config entry data keys
CONF_ADDRESS = "address"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_COLLECTION_DAY = "collection_day"
CONF_WEEK = "week"
CONF_GLASS_WEEK = "glass_week"
CONF_POSTCODE = "postcode"
