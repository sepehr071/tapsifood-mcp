"""Location tools: place name to coordinates and back, plus the cities Tapsi Food serves."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .http import fetch
from .registry import tool

Lat = Annotated[float, Field(ge=24, le=40, description="Delivery point latitude, e.g. 35.7577.")]
Long = Annotated[float, Field(ge=44, le=64, description="Delivery point longitude, e.g. 51.4095.")]

# Tehran center, used to bias place search when no point is given.
TEHRAN = (35.6892, 51.389)

# Snapshot: the site's city selector has no API. Isfahan and Tabriz show "coming soon" and return no catalog.
CITIES = [
    {"title": "تهران", "code": "tehran", "lat": 35.6892, "long": 51.389, "served": True},
    {"title": "مشهد", "code": "mashhad", "lat": 36.295289, "long": 59.585015, "served": True},
    {"title": "شیراز", "code": "shiraz", "lat": 29.67185, "long": 52.499858, "served": True},
    {"title": "اصفهان", "code": "isfahan", "lat": 32.651789, "long": 51.693768, "served": False},
    {"title": "تبریز", "code": "tabriz", "lat": 38.080028, "long": 46.2919, "served": False},
]


@tool("Find location")
async def tf_find_location(
    query: Annotated[
        str,
        Field(min_length=2, description="Place, street or landmark, e.g. 'میدان ونک'."),
    ],
    near_lat: Annotated[
        float | None, Field(description="Bias latitude (e.g. a city center from tf_list_cities).")
    ] = None,
    near_long: Annotated[float | None, Field(description="Bias longitude.")] = None,
    limit: Annotated[int, Field(ge=1, le=20, description="Max places to return.")] = 5,
) -> dict[str, Any]:
    """Turn a place name or address into latitude/longitude.

    Use first when the user gives an address; every other tf_* tool needs lat/long.
    Biased toward near_lat/near_long (default Tehran): pass a city center for other cities.
    A found place can still be outside Tapsi Food's delivery area (tf_list_cities).
    """
    if (near_lat is None) != (near_long is None):
        raise ToolError("Give both near_lat and near_long (or neither, which biases toward Tehran).")
    lat, lon = (near_lat, near_long) if near_lat is not None else TEHRAN
    body = await fetch("/v1/api/Map/geocode/forward", {"search_text": query, "district": f"{lon},{lat}"})
    return {
        "places": [
            {
                "name": (g := p["geo_location"])["title"],
                "description": p.get("description"),
                "lat": g["center"]["lat"],
                "long": g["center"]["lng"],
                "type": g.get("category"),
            }
            for p in (body.get("results") or [])[:limit]
            if p.get("geo_location")
        ]
    }


@tool("Describe coordinates")
async def tf_reverse_geocode(lat: Lat, long: Long) -> dict[str, Any]:
    """Describe coordinates as an address with province and city.

    Use to confirm a delivery point with the user before searching.
    """
    body = await fetch(
        "/v1/api/Map/geocode/reverse", {"subdivision": "true", "local_address": "true", "location": f"{long},{lat}"}
    )
    s = body.get("subdivisions") or {}
    return {
        "address": body.get("address"),
        "province": (s.get("ostan") or {}).get("title"),
        "city": (s.get("shahrestan") or {}).get("title"),
        "district": (s.get("bakhsh") or {}).get("title"),
        "certainty": body.get("certainty"),
    }


@tool("List cities")
async def tf_list_cities(
    query: Annotated[str | None, Field(description="Filter on Persian title or English code, e.g. 'شیراز'.")] = None,
) -> dict[str, Any]:
    """List the cities Tapsi Food shows, with a center point and whether it delivers there.

    Use the center as a rough delivery point when the user only names a city. Static snapshot
    (2026-10-19): the site has no city API, and unserved cities return no restaurants.
    """
    q = (query or "").strip().lower()
    return {"cities": [c for c in CITIES if q in c["title"] or q in c["code"]]}
