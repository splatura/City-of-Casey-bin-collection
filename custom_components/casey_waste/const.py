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
# The dataset's Week_1/Week_2 tag is the area's fortnight phase for recycling.
# FORTNIGHT_ANCHOR is a Monday in a "Week 2" collection week
# (validated: Thu 23 Oct 2025, Week-2 areas received recycling).
FORTNIGHT_ANCHOR = date(2025, 10, 20)

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

# Config entry data keys
CONF_ADDRESS = "address"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_COLLECTION_DAY = "collection_day"
CONF_WEEK = "week"
CONF_POSTCODE = "postcode"
