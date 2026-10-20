"""Smoke tests against the real Tapsi Food API (Tehran test point). Run with: pytest -m live

Needs an Iranian IP: Tapsi Food hangs connections from other exits.
"""

import pytest

pytestmark = [pytest.mark.anyio, pytest.mark.live]

TEHRAN = {"lat": 35.6892, "long": 51.389}
VENDOR = "2y97wk"


async def call(client, name, args):
    result = await client.call_tool(name, args)
    assert not result.is_error, result.content[0].text
    return result.structured_content


async def test_find_location(client):
    out = await call(client, "tf_find_location", {"query": "ونک"})
    assert out["places"] and out["places"][0]["lat"] > 30


async def test_reverse_geocode(client):
    out = await call(client, "tf_reverse_geocode", TEHRAN)
    assert out["city"] == "تهران"


async def test_list_cities(client):
    out = await call(client, "tf_list_cities", {"query": "shiraz"})
    assert out["cities"][0]["served"] is True


async def test_search_dishes(client):
    out = await call(client, "tf_search_dishes", {"query": "پیتزا", **TEHRAN, "sort": "cheapest", "limit": 5})
    if not out["total"]:
        pytest.skip("Tapsi search lists open vendors only; none open now")
    prices = [d["final_price"] for d in out["dishes"]]
    assert prices and prices == sorted(prices) and out["dishes"][0]["vendor_code"]
    top = await call(client, "tf_search_dishes", {"query": "پیتزا", **TEHRAN, "sort": "top_rated", "limit": 10})
    rates = [d.get("rating", 0) for d in top["dishes"]]
    assert rates == sorted(rates, reverse=True)


async def test_search_vendors(client):
    out = await call(client, "tf_search_vendors", {"query": "پیتزا", **TEHRAN, "limit": 5})
    if not out["total"]:
        pytest.skip("Tapsi search lists open vendors only; none open now")
    assert out["vendors"] and out["vendors"][0]["code"]


async def test_restaurants(client):
    out = await call(client, "tf_restaurants", {**TEHRAN, "sort": "top_rated", "page_size": 20})
    assert out["vendors"] and out["categories"] and all(v["code"] for v in out["vendors"])
    groceries = await call(client, "tf_restaurants", {**TEHRAN, "kind": "groceries"})
    assert groceries["vendors"]


async def test_deals(client):
    out = await call(client, "tf_deals", {**TEHRAN, "page_size": 10})
    if not out["total"]:
        pytest.skip("no Tap Time deals running now")
    assert out["deals"] and all(d["final_price"] <= d["price"] for d in out["deals"])


async def test_discounted_vendors(client):
    out = await call(client, "tf_discounted_vendors", {**TEHRAN, "page_size": 10})
    assert out["vendors"] and out["vendors"][0]["code"]


async def test_menu(client):
    out = await call(client, "tf_menu", {"vendor_code": VENDOR, **TEHRAN, "limit": 5})
    assert out["vendor"]["code"] == VENDOR and out["categories"]
    assert out["items"] and all(i["final_price"] > 0 for i in out["items"])


async def test_vendor_info(client):
    out = await call(client, "tf_vendor_info", {"vendor_code": VENDOR, **TEHRAN})
    assert out["code"] == VENDOR and out["min_order"] > 0 and out["ratings_count"] > 0
    assert isinstance(out["open_now"], bool)


async def test_reviews(client):
    out = await call(client, "tf_reviews", {"vendor_code": VENDOR, "limit": 3})
    assert out["total"] > 0 and out["reviews"]


async def test_unknown_vendor_is_actionable(client):
    result = await client.call_tool("tf_menu", {"vendor_code": "zzzzzz", **TEHRAN})
    assert result.is_error and "Unknown vendor code" in result.content[0].text
