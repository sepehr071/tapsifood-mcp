import httpx
import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio

TEHRAN = {"lat": 35.6892, "long": 51.389}
FEED = "/v1/api/search-discovery/page-content/"
SEARCH = "/v1/api/search-discovery/Search/"


async def test_all_tools_are_read_only(client):
    tools = (await client.list_tools()).tools
    assert len(tools) == 11 and all(t.name.startswith("tf_") for t in tools)
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.description and t.title, t.name
        assert "title" not in str(t.input_schema.get("properties", {}).get("lat", {})), t.name


async def test_find_location(client, api):
    api["/v1/api/Map/geocode/forward"] = fixture("geocode_forward.json")
    result = await client.call_tool("tf_find_location", {"query": "ونک", "limit": 2})
    places = result.structured_content["places"]
    assert len(places) == 2 and places[0] == {
        "name": "ونک",
        "description": "تهران،ونک",
        "lat": 35.763658,
        "long": 51.399225,
        "type": "Neighborhood",
    }
    assert api.calls[0].url.params["district"] == "51.389,35.6892"  # lng,lat order


async def test_reverse_geocode(client, api):
    api["/v1/api/Map/geocode/reverse"] = fixture("geocode_reverse.json")
    result = await client.call_tool("tf_reverse_geocode", TEHRAN)
    assert result.structured_content["city"] == "تهران" and result.structured_content["district"] == "مرکزی"
    assert api.calls[0].url.params["location"] == "51.389,35.6892"


async def test_list_cities_filter(client):
    result = await client.call_tool("tf_list_cities", {"query": "mashhad"})
    assert [c["title"] for c in result.structured_content["cities"]] == ["مشهد"]
    result = await client.call_tool("tf_list_cities", {})
    assert [c["served"] for c in result.structured_content["cities"]] == [True, True, True, False, False]


async def test_search_dishes_cheapest_sorts_pool(client, api):
    api[SEARCH + "product-search"] = fixture("product_search.json")
    result = await client.call_tool("tf_search_dishes", {"query": "پیتزا", **TEHRAN, "sort": "cheapest", "limit": 2})
    out = result.structured_content
    assert out["total"] == 607
    assert [d["final_price"] for d in out["dishes"]] == [465000, 486000]
    assert out["dishes"][1]["discount_pct"] == 55 and out["dishes"][1]["vendor_code"] == "2y97wk"
    assert api.calls[0].url.params["pageSize"] == "100"
    page2 = await client.call_tool(
        "tf_search_dishes", {"query": "پیتزا", **TEHRAN, "sort": "cheapest", "limit": 2, "page": 2}
    )
    ids = [d["id"] for d in out["dishes"]]
    assert page2.structured_content["dishes"] and not set(ids) & {d["id"] for d in page2.structured_content["dishes"]}


async def test_search_dishes_top_rated_sorts_pool_by_dish_rating(client, api):
    body = fixture("product_search.json")
    rows = body["data"]
    for row, (dish, vendor) in zip(rows, [(4.5, 3.0), (None, 5.0), (4.5, 4.0)], strict=True):
        row["productInfo"]["rate"], row["vendorInfo"]["rate"] = dish, vendor
    api[SEARCH + "product-search"] = body
    result = await client.call_tool(
        "tf_search_dishes", {"query": "پیتزا", **TEHRAN, "sort": "top_rated", "discounted_only": True, "limit": 3}
    )
    got = [(d.get("rating"), d["vendor_rating"]) for d in result.structured_content["dishes"]]
    assert got == [(4.5, 4.0), (4.5, 3.0), (None, 5.0)]  # unrated last
    p = api.calls[0].url.params
    assert p.get_list("filtersAndSorts") == ["HasDiscount"] and p["pageSize"] == "100"  # API ignores ratingdesc


async def test_search_dishes_nearest_uses_api_sort(client, api):
    api[SEARCH + "product-search"] = fixture("product_search.json")
    await client.call_tool("tf_search_dishes", {"query": "پیتزا", **TEHRAN, "sort": "nearest", "page": 2})
    p = api.calls[0].url.params
    assert p.get_list("filtersAndSorts") == ["distance"] and p["pageNumber"] == "2"


async def test_search_dishes_limit_is_capped_for_reply_size(client):
    result = await client.call_tool("tf_search_dishes", {"query": "پیتزا", **TEHRAN, "limit": 41})
    assert result.is_error and "less than or equal to 40" in result.content[0].text


@pytest.mark.parametrize("city", [(36.295289, 59.585015), (29.67185, 52.499858)])
async def test_closed_hours_search_is_empty_but_feeds_keep_closed_vendors(client, api, city):
    lat, long = city  # Mashhad, Shiraz at night: search lists open vendors only, feeds keep closed ones
    empty = {"data": [], "meta": {"pageSize": 10, "pageNumber": 1, "totalItems": 0}}
    api[SEARCH + "product-search"] = api[SEARCH + "vendor-search"] = empty
    for name in ("tf_search_dishes", "tf_search_vendors"):
        out = (await client.call_tool(name, {"query": "کباب", "lat": lat, "long": long})).structured_content
        assert out["total"] == 0 and not out.get("dishes") and not out.get("vendors")
    feed = fixture("restaurants.json")
    for c in feed["content"]:
        if c.get("defaultFeedContent"):
            c["defaultFeedContent"]["vendorStatus"] = "Closed"
    api[FEED + "business-line-15"] = api[FEED + "فودشات"] = feed
    for name in ("tf_restaurants", "tf_discounted_vendors"):
        vendors = (await client.call_tool(name, {"lat": lat, "long": long})).structured_content["vendors"]
        assert vendors and all(v["open"] is False for v in vendors)
    assert api.calls[-1].url.params["latitude"] == str(lat)


async def test_find_location_needs_both_near_coordinates(client, api):
    for args in ({"near_lat": 35.7}, {"near_long": 51.4}):
        result = await client.call_tool("tf_find_location", {"query": "ونک", **args})
        assert result.is_error and "both near_lat and near_long" in result.content[0].text
    assert not api.calls


async def test_search_vendors(client, api):
    api[SEARCH + "vendor-search"] = fixture("vendor_search.json")
    result = await client.call_tool("tf_search_vendors", {"query": "پیتزا", **TEHRAN})
    vendors = result.structured_content["vendors"]
    assert vendors[0]["code"] == "5z68lm" and vendors[0]["delivery_fee"] == 32000 and vendors[0]["open"] is True
    assert vendors[1]["badges"] == ["ارسال رایگان"]


async def test_restaurants_filters_and_categories(client, api):
    api[FEED + "business-line-15"] = fixture("restaurants.json")
    result = await client.call_tool(
        "tf_restaurants",
        {**TEHRAN, "category": "1-82", "sort": "top_rated", "discounted_only": True, "delivery": "vendor"},
    )
    out = result.structured_content
    assert api.calls[0].url.params.get_list("filtersAndSorts") == ["1-82", "ratingdesc", "HasDiscount", "OwnDelivery"]
    assert {"title": "کباب", "filter": "1-82"} in out["categories"]
    v = out["vendors"][0]
    assert v["code"] == "5rw6ny" and v["min_order"] == 300000 and v["open"] is True and v["discount_pct"] == 10
    assert out["total"] == 177 and out["has_more"] is True


async def test_groceries_use_business_line_7(client, api):
    api[FEED + "business-line-7"] = fixture("groceries.json")
    result = await client.call_tool("tf_restaurants", {**TEHRAN, "kind": "groceries"})
    assert result.structured_content["vendors"][0]["badges"] == ["کوپن خرید"]


async def test_deals(client, api):
    api[FEED + "تپ-تایم"] = fixture("taptime.json")
    result = await client.call_tool("tf_deals", {**TEHRAN})
    deals = result.structured_content["deals"]
    assert type(deals[0]["discount_pct"]) is int
    assert deals[0]["stock_left"] == 79 and deals[0]["final_price"] == 726000 and deals[0]["open"] is True
    assert api.calls[0].url.params["filtersAndSorts"] == "mostdiscounted"


async def test_discounted_vendors(client, api):
    api[FEED + "فودشات"] = fixture("foodshots.json")
    result = await client.call_tool("tf_discounted_vendors", {**TEHRAN})
    assert result.structured_content["vendors"][0]["discount_pct"] == 70


async def test_menu_filters_by_query(client, api):
    api["/v2/api/Vendor/2y97wk/vendor"] = fixture("vendor_menu.json")
    result = await client.call_tool("tf_menu", {"vendor_code": "2y97wk", **TEHRAN, "query": "بیکن"})
    out = result.structured_content
    assert out["vendor"]["status"] == "Open" and len(out["categories"]) == 2
    assert [i["product_id"] for i in out["items"]] == ["1472036"] and out["items"][0]["in_stock"] is True
    assert api.calls[0].url.params["latitude"] == "35.6892"


async def test_menu_names_size_variations_after_the_dish(client, api):
    menu = fixture("vendor_menu.json")
    var = menu["data"]["categories"][0]["products"][0]["productVariations"][0]
    pname = menu["data"]["categories"][0]["products"][0]["productName"]
    var["productVariationName"] = "21 سانتی متری"
    api["/v2/api/Vendor/2y97wk/vendor"] = menu
    out = (await client.call_tool("tf_menu", {"vendor_code": "2y97wk", **TEHRAN})).structured_content
    assert out["items"][0]["name"] == f"{pname.strip()} (21 سانتی متری)"


async def test_reviews_unknown_vendor_is_an_error(client, api):
    api["/v1/api/Vendor/zzzzzz/profile"] = {
        "statusCode": 500,
        "message": "Error while getting Vendor Profile.",
        "data": {},
    }
    result = await client.call_tool("tf_reviews", {"vendor_code": "zzzzzz"})
    assert result.is_error and "Unknown vendor code" in result.content[0].text


async def test_vendor_info_combines_menu_and_profile(client, api):
    api["/v2/api/Vendor/2y97wk/vendor"] = fixture("vendor_menu.json")
    api["/v1/api/Vendor/2y97wk/profile"] = fixture("vendor_profile.json")
    result = await client.call_tool("tf_vendor_info", {"vendor_code": "2y97wk", **TEHRAN})
    out = result.structured_content
    assert out["delivery_fee"] == 61500 and out["min_order"] == 400000 and out["min_order_profile"] == 300000
    assert out["status"] == "Open" and out["open_now"] is True and out["delivery_by"] == "tapsi"
    assert "status_profile" not in out and out["eta_max"] == 55  # the profile status is only an on/off switch
    assert out["hours_today"] == "11:00-23:45" and out["ratings_count"] == 1757


async def test_out_of_coverage_has_no_fee(client, api):
    menu = fixture("vendor_menu.json")
    menu["data"]["vendor"].update(
        vendorStatus="OutOfCoverage", deliveryTypes=[{"deliveryType": "Unknown", "deliveryPrice": -1}]
    )
    api["/v2/api/Vendor/2y97wk/vendor"] = menu
    api["/v1/api/Vendor/2y97wk/profile"] = fixture("vendor_profile.json")
    result = await client.call_tool("tf_vendor_info", {"vendor_code": "2y97wk", **TEHRAN})
    assert result.structured_content["status"] == "OutOfCoverage" and result.structured_content["delivery_fee"] is None
    assert result.structured_content["open_now"] is False


async def test_vendor_info_closed_menu_beats_open_profile_switch(client, api):
    menu = fixture("vendor_menu.json")
    menu["data"]["vendor"]["vendorStatus"] = "Close"
    prof = fixture("vendor_profile.json")
    prof["data"]["info"]["vendorStatus"] = "Open"
    api["/v2/api/Vendor/2y97wk/vendor"], api["/v1/api/Vendor/2y97wk/profile"] = menu, prof
    out = (await client.call_tool("tf_vendor_info", {"vendor_code": "2y97wk", **TEHRAN})).structured_content
    assert out["open_now"] is False


async def test_reviews_page_is_zero_based_upstream(client, api):
    api["/v1/api/Vendor/2y97wk/profile"] = fixture("vendor_profile.json")
    result = await client.call_tool("tf_reviews", {"vendor_code": "2y97wk", "page": 1, "limit": 3})
    out = result.structured_content
    assert out["total"] == 90 and len(out["reviews"]) == 3 and out["reviews"][0]["date"] == "2026-10-18"
    assert out["has_more"] is True and api.calls[0].url.params["pageNumber"] == "0"
    last = await client.call_tool("tf_reviews", {"vendor_code": "2y97wk", "page": 9, "limit": 10})
    assert last.structured_content["has_more"] is False


async def test_review_comments_are_cut_unless_full_text(client, api):
    prof = fixture("vendor_profile.json")
    prof["data"]["insight"]["reviews"][0]["orderItems"][0]["comment"] = "ب" * 300
    api["/v1/api/Vendor/2y97wk/profile"] = prof
    args = {"vendor_code": "2y97wk", "limit": 1}
    cut = (await client.call_tool("tf_reviews", args)).structured_content["reviews"][0]["items"][0]["comment"]
    full = (await client.call_tool("tf_reviews", {**args, "full_text": True})).structured_content
    assert cut == "ب" * 250 + "...[cut]" and full["reviews"][0]["items"][0]["comment"] == "ب" * 300


async def test_menu_pages_with_offset_and_cuts_descriptions(client, api):
    menu = fixture("vendor_menu.json")
    menu["data"]["categories"][0]["products"][0]["productDescription"] = "ب" * 300
    api["/v2/api/Vendor/2y97wk/vendor"] = menu
    args = {"vendor_code": "2y97wk", **TEHRAN}
    first = (await client.call_tool("tf_menu", {**args, "limit": 2})).structured_content
    second = (await client.call_tool("tf_menu", {**args, "limit": 2, "offset": 2})).structured_content
    assert first["items"][0]["description"] == "ب" * 100 + "...[cut]"
    assert first["total"] == second["total"] > 4 and not {i["id"] for i in first["items"]} & {
        i["id"] for i in second["items"]
    }
    too_big = await client.call_tool("tf_menu", {**args, "limit": 26})
    assert too_big.is_error


async def test_unknown_vendor_not_retried(client, api):
    api["/v2/api/Vendor/zzzzzz/vendor"] = lambda r: httpx.Response(
        500, json={"detail": "The hash provided yielded no result."}
    )
    result = await client.call_tool("tf_menu", {"vendor_code": "zzzzzz", **TEHRAN})
    assert result.is_error and "Unknown vendor code" in result.content[0].text
    assert len(api.calls) == 1


async def test_unserved_city_is_actionable(client, api):
    api[FEED + "business-line-15"] = lambda r: httpx.Response(404, json={"status": 404, "message": "Not Found"})
    result = await client.call_tool("tf_restaurants", {"lat": 32.65, "long": 51.69})
    assert result.is_error and "Tehran, Mashhad and Shiraz" in result.content[0].text


async def test_geo_block_timeout_is_actionable(client, api):
    def hang(request):
        raise httpx.ConnectTimeout("hang", request=request)

    api["/v1/api/Map/geocode/reverse"] = hang
    result = await client.call_tool("tf_reverse_geocode", TEHRAN)
    assert result.is_error and "TAPSIFOOD_MCP_PROXY" in result.content[0].text


def test_review_dates_are_tehran_days():
    from tapsifood_mcp.vendor import _tehran_date

    assert _tehran_date("2026-10-18T21:00:00.000Z") == "2026-10-19" and _tehran_date(None) is None
