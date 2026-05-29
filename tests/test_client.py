"""Tests for the async Casey client using mocked HTTP."""
import re

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from custom_components.casey_waste import client

NOM = re.compile(r"^https://nominatim\.openstreetmap\.org/search.*$")
CAS = re.compile(r"^https://data\.casey\.vic\.gov\.au/.*$")


async def test_geocode_success():
    with aioresponses() as m:
        m.get(NOM, payload=[{"lat": "-38.1", "lon": "145.3"}])
        async with ClientSession() as session:
            result = await client.geocode(session, "2 Patrick Northeast Drive, Narre Warren")
    assert result.lat == -38.1
    assert result.lon == 145.3


async def test_geocode_falls_back_to_suburb():
    with aioresponses() as m:
        m.get(NOM, payload=[])  # full address: no result
        m.get(NOM, payload=[{"lat": "-38.0", "lon": "145.2"}])  # suburb: hit
        async with ClientSession() as session:
            result = await client.geocode(session, "999 Nowhere St, Narre Warren")
    assert result.lat == -38.0


async def test_geocode_not_found_raises():
    with aioresponses() as m:
        m.get(NOM, payload=[])
        m.get(NOM, payload=[])
        async with ClientSession() as session:
            with pytest.raises(client.AddressNotFound):
                await client.geocode(session, "999 Nowhere St, Narre Warren")


async def test_geocode_connection_error_raises():
    with aioresponses() as m:
        m.get(NOM, exception=ConnectionError("boom"))
        async with ClientSession() as session:
            with pytest.raises(client.CannotConnect):
                await client.geocode(session, "2 Patrick Northeast Drive")


async def test_find_area_within_distance():
    with aioresponses() as m:
        m.get(CAS, payload={"results": [{"collection": "Thursday_Week_2", "postcode": 3980}]})
        async with ClientSession() as session:
            area = await client.find_collection_area(session, -38.1, 145.3)
    assert area.collection == "Thursday_Week_2"
    assert area.postcode == "3980"


async def test_find_area_falls_back_to_distance():
    with aioresponses() as m:
        m.get(CAS, payload={"results": []})  # within_distance: empty
        m.get(CAS, payload={"results": [{"collection": "Monday_Week_1", "postcode": 3805}]})
        async with ClientSession() as session:
            area = await client.find_collection_area(session, -38.1, 145.3)
    assert area.collection == "Monday_Week_1"


async def test_find_area_none_raises():
    with aioresponses() as m:
        m.get(CAS, payload={"results": []})
        m.get(CAS, payload={"results": []})
        async with ClientSession() as session:
            with pytest.raises(client.AreaNotFound):
                await client.find_collection_area(session, -38.1, 145.3)


async def test_find_area_connection_error_raises():
    with aioresponses() as m:
        m.get(CAS, exception=ConnectionError("boom"))
        async with ClientSession() as session:
            with pytest.raises(client.CannotConnect):
                await client.find_collection_area(session, -38.1, 145.3)


async def test_geocode_suburb_fallback_skips_unit_prefix():
    # Unit-prefixed address: the suburb is the second-to-last segment, not the
    # street that follows the unit number.
    with aioresponses() as m:
        m.get(NOM, payload=[])  # full address: no result
        m.get(NOM, payload=[{"lat": "-38.05", "lon": "145.25"}])  # suburb query
        async with ClientSession() as session:
            result = await client.geocode(
                session, "Unit 2, 2 Patrick Northeast Drive, Narre Warren, VIC"
            )
    assert result.lat == -38.05
    # The second geocode query must have used the suburb, not "2 Patrick Northeast Drive".
    suburb_request = [
        call
        for key, calls in m.requests.items()
        for call in calls
        if "Narre Warren, Victoria, Australia" in str(call.kwargs.get("params", ""))
    ]
    assert suburb_request
