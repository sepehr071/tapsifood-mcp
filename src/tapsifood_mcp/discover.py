"""Search and browse tools: dishes, vendors, restaurant and grocery lists, flash deals, discounted vendors."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from .http import fetch
from .location import Lat, Long
from .registry import tool

Query = Annotated[str, Field(min_length=2, description="Dish or restaurant word, e.g. 'پیتزا'.")]
Page = Annotated[int, Field(ge=1, le=50, description="Page number, from 1.")]

FEED = "/v1/api/search-discovery/page-content/"
SEARCH = "/v1/api/search-discovery/Search/"
DELIVERY = {"tapsi": "OfoodDelivery", "vendor": "OwnDelivery"}


def _stars(v: float | None) -> float | None:
    return round(v, 1) if v else None


def _dish(d: dict[str, Any]) -> dict[str, Any]:
    p, v = d["productInfo"], d.get("vendorInfo") or {}
    return {
        "id": p["id"],
        "product_id": str(p["headerId"]) if p.get("headerId") is not None else None,
        "name": p["name"].strip(),
        "price": p["price"],
        "discount_pct": p.get("discountRatio") or 0,
        "final_price": p["priceAfterDiscount"],
        "rating": _stars(p.get("rate")),
        "vendor_code": v.get("vendorCode"),
        "vendor": (v.get("title") or "").strip(),
        "vendor_rating": _stars(v.get("rate")),
        "delivery_fee": v.get("deliveryPrice"),
        "eta_max": v.get("eta"),
        "open": v.get("vendorStatus"),
    }


def _vendor(code: str, title: str | None, v: dict[str, Any]) -> dict[str, Any]:
    """One vendor card; search rows and feed rows name the same facts differently."""
    badges = [b["name"] for b in v.get("badges") or [] if b.get("name")]
    return {
        "code": code,
        "title": (title or "").strip(),
        "rating": _stars(v.get("rate")),
        "ratings_count": v.get("ratesCount"),
        "open": v["isOpen"] if "isOpen" in v else v.get("vendorStatus") == "Open",
        "delivery_fee": v.get("deliveryPrice"),
        "delivery_by": "vendor" if v.get("deliveryType") == "OwnDelivery" else "tapsi",
        "min_order": int(v["minimumBasket"]) if v.get("minimumBasket") else None,
        "eta_max": v.get("eta"),
        "discount_pct": int(v["discount"]) if v.get("discount") else None,
        "badges": badges,
    }


@tool("Search dishes")
async def tf_search_dishes(
    query: Query,
    lat: Lat,
    long: Long,
    sort: Annotated[
        Literal["relevance", "cheapest", "biggest_discount", "top_rated", "nearest"],
        Field(
            description="Order of the results; cheapest / biggest_discount / top_rated sort the first 100 matches "
            "(top_rated = dish rating, then restaurant rating; unrated last). nearest is Tapsi's own order."
        ),
    ] = "relevance",
    discounted_only: Annotated[bool, Field(description="Only dishes with a discount.")] = False,
    page: Page = 1,
    limit: Annotated[int, Field(ge=1, le=40, description="Max dishes (40 keeps the reply under 15 KB).")] = 10,
) -> dict[str, Any]:
    """Search dishes by name near a delivery point, with price, discount and restaurant.

    Use for "find X near me" or "cheapest / discounted X". Prices are the search index's and can lag
    the menu: confirm with tf_menu before recommending. Then call tf_vendor_info for fee and minimum order.
    Tapsi's search lists only restaurants open now: at night total can be 0 (the site shows the same);
    tf_restaurants / tf_discounted_vendors also list closed vendors.
    """
    pooled = sort in ("cheapest", "biggest_discount", "top_rated")  # the API ignores ratingdesc for dishes
    filters = ["HasDiscount"] if discounted_only else []
    if sort == "nearest":
        filters.append("distance")
    body = await fetch(
        SEARCH + "product-search",
        {
            "latitude": lat,
            "longitude": long,
            "query": query,
            "pageNumber": 1 if pooled else page,
            "pageSize": 100 if pooled else limit,
            "filtersAndSorts": filters or None,
        },
    )
    dishes = [_dish(d) for d in body.get("data") or []]
    if sort == "cheapest":
        dishes.sort(key=lambda d: d["final_price"])
    elif sort == "biggest_discount":
        dishes.sort(key=lambda d: -d["discount_pct"])
    elif sort == "top_rated":
        dishes.sort(key=lambda d: (-(d["rating"] or 0), -(d["vendor_rating"] or 0)))
    if pooled:  # the pool is page 1 of 100 hits; slice the requested page out of it
        dishes = dishes[(page - 1) * limit :]
    return {"total": body["meta"]["totalItems"], "dishes": dishes[:limit]}


@tool("Search vendors")
async def tf_search_vendors(
    query: Query,
    lat: Lat,
    long: Long,
    page: Page = 1,
    limit: Annotated[int, Field(ge=1, le=50, description="Max vendors.")] = 10,
) -> dict[str, Any]:
    """Search restaurants and stores by name or cuisine near a delivery point.

    Use to find a vendor code by name. No dish prices: use tf_menu or tf_search_dishes.
    Tapsi's search lists only restaurants open now (total 0 at night, as on the site); tf_restaurants also lists closed ones.
    """
    body = await fetch(
        SEARCH + "vendor-search",
        {"latitude": lat, "longitude": long, "query": query, "pageNumber": page, "pageSize": limit},
    )
    return {
        "total": body["meta"]["totalItems"],
        "vendors": [_vendor(r["vendorCode"], (i := r["vendorInfo"])["title"], i) for r in body.get("data") or []],
    }


async def _feed(slug: str, lat: float, long: float, filters: list[str], page: int, size: int) -> dict[str, Any]:
    """One page of a CMS feed. Page 1 also carries filter and banner widgets, so it holds fewer rows."""
    body = await fetch(
        FEED + slug,
        {
            "latitude": lat,
            "longitude": long,
            "bypassCache": "false",
            "pageNumber": page,
            "pageSize": size,
            "filtersAndSorts": filters or None,
        },
    )
    rows, chips = [], []
    for c in body.get("content") or []:
        if c["type"] in (1, 2) and c.get("defaultFeedContent"):
            rows.append(c)
        elif (c.get("component") or {}).get("type") == 1039:  # category chips, only on page 1
            chips = [
                {"title": i["payload"]["title"], "filter": i["filterValue"]}
                for i in c["component"]["items"]
                if i.get("filterValue")
            ]
    meta = body["meta"]
    total = rows[0].get("feedMeta", {}).get("totalItems") if rows else 0
    return {
        "rows": [r["defaultFeedContent"] for r in rows],
        "chips": chips,
        "total": total if total is not None else meta["totalItems"],
        "has_more": meta["pageNumber"] * meta["pageSize"] < meta["totalItems"],
    }


def _filters(sort: str | None, discounted_only: bool, delivery: str, new_only: bool, category: str | None) -> list[str]:
    out = [category] if category else []
    out += [sort] if sort else []
    out += ["HasDiscount"] if discounted_only else []
    out += [DELIVERY[delivery]] if delivery in DELIVERY else []
    out += ["NewVendor"] if new_only else []
    return out


@tool("List restaurants")
async def tf_restaurants(
    lat: Lat,
    long: Long,
    kind: Annotated[
        Literal["restaurants", "groceries"], Field(description="restaurants, or grocery stores (خواربار).")
    ] = "restaurants",
    category: Annotated[
        str | None,
        Field(description="Cuisine chip filter from the 'categories' of a page-1 result, e.g. '1-82' (kebab)."),
    ] = None,
    sort: Annotated[
        Literal["default", "top_rated", "popular", "nearest"], Field(description="Order of the results.")
    ] = "default",
    discounted_only: Annotated[bool, Field(description="Only vendors with a discount.")] = False,
    delivery: Annotated[
        Literal["any", "tapsi", "vendor"], Field(description="Courier: Tapsi's own, or the vendor's.")
    ] = "any",
    new_only: Annotated[bool, Field(description="Only new vendors.")] = False,
    page: Page = 1,
    page_size: Annotated[
        int,
        Field(
            ge=5, le=50, description="Feed items per page; page 1 spends some on widgets, so it lists fewer vendors."
        ),
    ] = 20,
) -> dict[str, Any]:
    """List restaurants (or grocery stores) delivering to a point, with rating, delivery fee, minimum order and ETA.

    Use to browse or rank vendors. Page 1 also returns 'categories' (cuisine filters for the category param).
    No dish prices: use tf_menu. Returns 404 outside the served cities (tf_list_cities).
    """
    sort_key = {"top_rated": "ratingdesc", "popular": "mostpopular", "nearest": "distance"}.get(sort)
    slug = "business-line-15" if kind == "restaurants" else "business-line-7"
    f = await _feed(slug, lat, long, _filters(sort_key, discounted_only, delivery, new_only, category), page, page_size)
    return {
        "total": f["total"],
        "has_more": f["has_more"],
        "categories": f["chips"],
        "vendors": [_vendor(r["vendorCode"], r["title"], r) for r in f["rows"]],
    }


@tool("Flash deals")
async def tf_deals(
    lat: Lat,
    long: Long,
    sort: Annotated[
        Literal["default", "most_discounted", "most_purchased", "cheapest", "top_rated"],
        Field(description="Order of the deals."),
    ] = "most_discounted",
    category: Annotated[str | None, Field(description="Cuisine chip filter from 'categories', e.g. '1-82'.")] = None,
    page: Page = 1,
    page_size: Annotated[
        int,
        Field(ge=5, le=50, description="Feed items per page; page 1 spends some on widgets, so it lists fewer deals."),
    ] = 20,
) -> dict[str, Any]:
    """List the Tap Time flash deals (تپ تایم): discounted dishes with a limited stock, near a point.

    Use for "today's best deals". Not the same as Snappfood's FoodParty. Check stock_left, it runs out.
    Then tf_menu / tf_vendor_info for the restaurant.
    """
    sort_key = {
        "most_discounted": "mostdiscounted",
        "most_purchased": "mostpurchased",
        "cheapest": "cheapest",
        "top_rated": "ratingdesc",
    }.get(sort)
    f = await _feed("تپ-تایم", lat, long, _filters(sort_key, False, "any", False, category), page, page_size)
    return {
        "total": f["total"],
        "has_more": f["has_more"],
        "categories": f["chips"],
        "deals": [
            {
                "id": r["productVariationId"],
                "product_id": r.get("headerId"),
                "name": r["productName"].strip(),
                "price": r["price"],
                "discount_pct": int(r.get("discountRatio") or 0),
                "final_price": r["priceAfterDiscount"],
                "stock_left": r.get("discountStock"),
                "rating": _stars(r.get("productRate")),
                "vendor_code": r["vendorCode"],
                "vendor": (r.get("vendorName") or "").strip(),
                "delivery_fee": r.get("deliveryPrice"),
                "open": r.get("vendorStatus") == "Open",
            }
            for r in f["rows"]
        ],
    }


@tool("Discounted vendors")
async def tf_discounted_vendors(
    lat: Lat,
    long: Long,
    sort: Annotated[
        Literal["default", "top_rated", "popular", "nearest"], Field(description="Order of the results.")
    ] = "default",
    page: Page = 1,
    page_size: Annotated[
        int,
        Field(
            ge=5, le=50, description="Feed items per page; page 1 spends some on widgets, so it lists fewer vendors."
        ),
    ] = 20,
) -> dict[str, Any]:
    """List the vendors in Tapsi Food's 'Food Shots' (فودشات) discount campaign near a point.

    Use for "which restaurants have the biggest discount". discount_pct is the vendor-wide percentage.
    The campaign is curated, so not every discounted vendor is in it (tf_restaurants with discounted_only is wider).
    """
    sort_key = {"top_rated": "ratingdesc", "popular": "mostpopular", "nearest": "distance"}.get(sort)
    f = await _feed("فودشات", lat, long, _filters(sort_key, False, "any", False, None), page, page_size)
    return {
        "total": f["total"],
        "has_more": f["has_more"],
        "vendors": [_vendor(r["vendorCode"], r["title"], r) for r in f["rows"]],
    }
