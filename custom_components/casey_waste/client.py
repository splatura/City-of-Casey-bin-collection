"""Async API client for geocoding and the City of Casey waste dataset."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import CASEY_WASTE_API, NOMINATIM_URL, NOMINATIM_USER_AGENT

_TIMEOUT = ClientTimeout(total=15)


class CaseyClientError(Exception):
    """Base error for the Casey client."""


class CannotConnect(CaseyClientError):
    """An upstream request failed or timed out."""


class AddressNotFound(CaseyClientError):
    """Geocoding produced no usable result."""


class AreaNotFound(CaseyClientError):
    """No Casey collection area contains the point."""


@dataclass
class GeoResult:
    lat: float
    lon: float


@dataclass
class AreaResult:
    collection: str
    postcode: str | None


async def geocode(session: ClientSession, address: str) -> GeoResult:
    """Geocode `address` via Nominatim, retrying with the suburb on failure."""
    result = await _geocode_query(session, address)
    if result is None and "," in address:
        # Retry with the suburb. It's the second-to-last comma segment for a
        # full address (street, suburb, state[, postcode]); fall back to the
        # last segment for a bare "street, suburb" so a unit/street prefix
        # doesn't get mistaken for the suburb.
        parts = [p.strip() for p in address.split(",") if p.strip()]
        suburb = (parts[-2] if len(parts) >= 3 else parts[-1])
        result = await _geocode_query(session, f"{suburb}, Victoria, Australia")
    if result is None:
        raise AddressNotFound(address)
    return result


async def _geocode_query(session: ClientSession, query: str) -> GeoResult | None:
    params = {"format": "json", "q": query, "limit": 1}
    headers = {"User-Agent": NOMINATIM_USER_AGENT}
    try:
        async with session.get(
            NOMINATIM_URL, params=params, headers=headers, timeout=_TIMEOUT
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (ClientError, ConnectionError, TimeoutError) as err:
        raise CannotConnect(str(err)) from err
    if not data:
        return None
    try:
        return GeoResult(lat=float(data[0]["lat"]), lon=float(data[0]["lon"]))
    except (KeyError, IndexError, TypeError, ValueError) as err:
        raise CannotConnect(f"Unexpected geocode response: {err}") from err


async def find_collection_area(
    session: ClientSession, lat: float, lon: float
) -> AreaResult:
    """Find the Casey collection area containing (lat, lon)."""
    record = await _area_query(
        session,
        {
            "where": f"within_distance(geo_shape, geom'POINT({lon} {lat})', 1m)",
            "limit": 1,
        },
    )
    if record is None:
        record = await _area_query(
            session, {"geofilter.distance": f"{lat},{lon},1000", "limit": 1}
        )
    if record is None:
        raise AreaNotFound(f"{lat},{lon}")
    postcode = record.get("postcode")
    return AreaResult(
        collection=record.get("collection", ""),
        postcode=str(postcode) if postcode is not None else None,
    )


async def _area_query(
    session: ClientSession, params: dict[str, Any]
) -> dict[str, Any] | None:
    try:
        async with session.get(
            CASEY_WASTE_API, params=params, timeout=_TIMEOUT
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (ClientError, ConnectionError, TimeoutError) as err:
        raise CannotConnect(str(err)) from err
    results = data.get("results") or []
    return results[0] if results else None
