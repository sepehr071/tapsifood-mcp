<!-- mcp-name: io.github.sepehr071/tapsifood-mcp -->

# tapsifood-mcp: Tapsi Food MCP server for AI agents

**Let your AI agent shop around on Tapsi Food (تپسی‌فود).**
An unofficial, read-only MCP server for Tapsi's food and grocery delivery in Iran: search dishes and restaurants near an
address, read live menus and reviews, check delivery fees and minimum orders, and catch the Tap Time flash deals.

## For AI agents

- **What:** unofficial MCP server for Tapsi Food (tapsi.food) in Iran. Queries in Persian match best; prices in Toman.
- **Install:** `uvx tapsifood-mcp` or `claude mcp add tapsifood -- uvx tapsifood-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none. Tapsi Food hangs connections from non-Iranian IPs: run it from Iran without a VPN, or set `TAPSIFOOD_MCP_PROXY` to an HTTP proxy that exits in Iran.
- **Access:** read-only. No login, basket, orders or payment, so no confirmation is needed before calling any tool.
- **Tools:** 11, all `tf_*`. Most need `lat` and `long` (not `tf_reviews`, `tf_find_location`, `tf_list_cities`).
  Typical sequence: `tf_find_location` -> `tf_search_dishes` -> `tf_vendor_info` (-> `tf_menu`, `tf_reviews`).
- **Coverage:** Tehran, Mashhad, Shiraz. Elsewhere the API answers 404 or `OutOfCoverage`.
- **Output:** compact JSON. Prices in Toman, ratings 0-5. Null and empty fields are omitted (a missing `rating` = not rated); menu descriptions
  are cut to 100 characters and review comments to 250 (`full_text: true` for the whole text, which lifts the size cap).
  Replies stay under about 15 KB at the maximum `limit` (`tf_menu` 25, `tf_reviews` 20, `tf_search_dishes` 40).

## Quick start

```bash
claude mcp add tapsifood -- uvx tapsifood-mcp
# behind a proxy that exits in Iran:
claude mcp add tapsifood -e TAPSIFOOD_MCP_PROXY=http://127.0.0.1:8080 -- uvx tapsifood-mcp
```

## Tools

| Tool | What it does |
|---|---|
| `tf_find_location` | Turn a place name or address into latitude/longitude. |
| `tf_reverse_geocode` | Describe coordinates as an address with province and city. |
| `tf_list_cities` | List the cities Tapsi Food shows, with a center point and whether it delivers there. |
| `tf_search_dishes` | Search dishes by name near a point; sort by relevance, cheapest, biggest discount, rating or distance. |
| `tf_search_vendors` | Search restaurants and stores by name or cuisine near a point. |
| `tf_restaurants` | List restaurants or grocery stores with rating, delivery fee, minimum order, ETA; filter by cuisine, discount, courier. |
| `tf_deals` | List the Tap Time flash deals (limited-stock discounted dishes). |
| `tf_discounted_vendors` | List the vendors in the Food Shots discount campaign. |
| `tf_menu` | Read a vendor's live menu with price, discount and stock. |
| `tf_vendor_info` | Get a vendor's delivery fee to a point, minimum order, packaging, ETA, status, hours, address and rating spread. |
| `tf_reviews` | Read customer reviews of a vendor with per-dish ratings. |

## Notes

- Prices in the search index can lag the menu: confirm with `tf_menu`. Menu and profile minimums sometimes differ; `tf_vendor_info` returns both (`min_order`, `min_order_profile`).
- Dish and vendor search list only restaurants open now (the site does the same), so at night `total` can be 0; `tf_restaurants` and
  `tf_discounted_vendors` also list closed vendors, flagged `open: false`. `tf_search_dishes` `top_rated` / `cheapest` / `biggest_discount`
  sort the first 100 matches, not the whole result set.
- `eta_max` is the site's "up to N minutes" (its dialog shows roughly 20 to N); the API sends no lower bound. `tf_vendor_info.open_now`
  follows the menu status (the live state the site shows); the profile's own status is just the vendor's on/off switch and is not returned.
- `tf_reviews`: `total` counts every review including rating-only ones; only reviews with a comment are listed, so a page can hold fewer
  than `limit` (keep paging while `has_more`). The site's tab badge shows just the first page's count. Writer names are left out on purpose.
- Coupons are not exposed by the site's anonymous API.
- Page 1 of the browse tools also carries filter and banner widgets, so it lists fewer vendors than `page_size`.
- API map this server is built on: [`tapsifood/`](https://github.com/sepehr071/api-mcp) (endpoints, samples, quirks).

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline unit tests
uv run python -m pytest -m live -q  # real API; needs an Iranian IP
uv build
```

Unofficial: not affiliated with Tapsi. MIT licensed.
