# tapsifood-mcp

Unofficial, read-only MCP server for Tapsi Food (tapsi.food, food and grocery delivery in Iran; not Snappfood).
On GitHub (`sepehr071/tapsifood-mcp`, public); no PyPI release or MCP Registry entry yet. Sibling of `../snapp-mcp`, copies its layout
and idioms; keep them in step.

API map this server is built on (endpoints, samples, quirks, geo-block findings): `../tapsifood/`.

## Layout

- `src/tapsifood_mcp/http.py`: the only HTTP code. One shared `httpx.AsyncClient` (`trust_env=False`) on a Chrome-impersonating
  curl_cffi transport, proxy only from `TAPSIFOOD_MCP_PROXY` (comma list, sticky, next on 403/429/connect error), semaphore (2),
  150-600 ms jitter before each uncached call, 60 s GET cache (64 entries, keyed on URL + query), up to 2 retries on
  timeout/network/5xx/429, no redirects, host allowlist (api.tapsi.food), 5 MB body cap. `fetch(path, params)`: a list value
  repeats the query key, None is dropped. `ApiError(ToolError)` with actionable messages (timeout = geo-block hint, 404 = not served,
  500 "yielded no result" = unknown vendor, not retried). `set_transport()` for tests. No browser fallback: no bot challenge was seen.
- `registry.py`: `@tool("Title")` collects tools. `server.py`: registers them with read-only annotations, holds `INSTRUCTIONS`.
- Tools: `location.py` (find location, reverse geocode, static city list; also `Lat`/`Long`), `discover.py` (dish and vendor search,
  restaurant/grocery hub, Tap Time deals, Food Shots vendors; shared `_feed`), `vendor.py` (menu, costs and hours, reviews).
  11 tools, all `tf_*`.
- `tests/`: `test_tools.py` and `test_http.py` unit tests (MockTransport + trimmed real fixtures in `tests/fixtures/`),
  `test_live.py` one live test per tool (`@pytest.mark.live`, needs an Iranian IP).

## Commands

uv needs the local proxy to download packages; the server and tests call Tapsi directly (env proxies are ignored).

```bash
export HTTPS_PROXY=http://127.0.0.1:10898 HTTP_PROXY=http://127.0.0.1:10898
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q            # unit tests, offline
uv run python -m pytest -m live -q    # live tests, Iranian IP only
uv build
```

## Rules for changes

- Read-only only: no login/OTP, cart, order, payment, wallet, address saving, no POST (`Search/click` is analytics, skip it).
- Output units: prices in **Toman** (the API is Toman, do not divide). Ratings 0-5 (the API already sends 0-5). `server.py` drops
  null/empty values below the top level, so a missing `rating` = not rated; top-level nulls are kept (e.g. `delivery_fee: null` = out of coverage).
  Menu descriptions are cut to 100 chars, review comments to 250 (`clip`). Every tool's reply must stay under ~15 KB at its maximum
  `limit` (tf_menu 25, tf_reviews 20, tf_search_dishes 40; others measured 6-12 KB): measure when adding fields. Input schemas have pydantic `title` keys stripped; there is no outputSchema.
- New tool: `@tool("Title")` async function named `tf_*`, every param `Annotated[..., Field(...)]` with constraints and an example,
  docstring = what it returns + when to use + what to call next, first line one complete sentence, compact dict output. Add a unit test
  with a real trimmed fixture, a live test, a README tool-table row, and an `INSTRUCTIONS` mention.
- Keep `README.md` tool table equal to `list_tools()`. Deps stay `mcp` + `httpx` + `httpx-curl-cffi`/`curl-cffi`.

## Tapsi quirks (keep them)

- Geo-block: from the Turkish v2rayN exit `api.tapsi.food` / `tapsi.food` hang until timeout while other Iranian sites answer through the
  same proxy; the same requests direct work. That is why `trust_env=False` and the opt-in `TAPSIFOOD_MCP_PROXY`. Tests and the server must
  not use `HTTPS_PROXY`. Tapsi's edge does not return a 403; a timeout on every call means the IP is not accepted.
- Served cities: Tehran, Mashhad, Shiraz (static snapshot in `location.CITIES`). Unserved points: feeds 404, search 200 with 0 hits,
  menu 200 with `vendorStatus: OutOfCoverage` and fee -1 (shown as `delivery_fee: null`). HTTP 200 does not mean deliverable.
- Geocoding takes `lng,lat` (`district`, `location`); everything else `latitude`/`longitude`.
- Feeds (`page-content/{slug}`): page 1 holds widgets (filter defs, category chips, banners) that count toward `pageSize`; rows are
  `type 1` vendor / `type 2` product. The row total is `feedMeta.totalItems`. `filtersAndSorts` repeats as a query key; values are the
  option keys (`ratingdesc`, `HasDiscount`, `OwnDelivery`, chip `1-82`); unknown values are silently ignored.
- Dish search has no price sort and ignores `ratingdesc`: `sort=cheapest` / `biggest_discount` / `top_rated` sort the first 100 hits
  client-side (`pageSize=100` works); `nearest` sends `distance` (the site's sort menu: ratingdesc, mostpopular, distance).
  Search `id` is a variation id; `headerId` is the product id (`tf_menu` `product_id`).
- Dish and vendor search return only vendors open now (total 0 at night; the site's search page shows "no results" too, and no
  include-closed param exists). Feeds (`tf_restaurants`, `tf_discounted_vendors`) keep closed vendors with `open: false`.
- Menu and profile disagree on `minimumBasket` for the same vendor; `tf_vendor_info` returns both. Status: menu `vendorStatus` is live
  (Open/Close/OutOfCoverage, matches the site's "فروشگاه بسته است"); profile `vendorStatus` stays `Open` outside working hours (the
  vendor's on/off switch), so `open_now` uses the menu status only.
- `eta` is an upper bound ("تا N دقیقه" on the site, usually 50-65, no lower bound in the API): output as `eta_max`.
- Reviews: profile `pageNumber` is 0-based, the tool's `page` is 1-based. `meta.total` counts all reviews; `insight.reviews` holds only
  those with a comment, so pages come back short (19 of 20). The site's review tab badge is the first page's row count. The API
  returns `writerName`; the tool omits it on purpose (privacy).
- Unknown vendor code: HTTP 500 "The hash provided yielded no result."
- Name matching ignores Arabic ي/ك vs Persian ی/ک and ZWNJ vs space (`_norm`).

## Release (not done yet)

Create the GitHub repo `sepehr071/tapsifood-mcp`, commit, bump nothing (0.1.0 in `pyproject.toml` and both versions in `server.json`),
update `uv.lock`, then `git tag v0.1.0 && git push --tags`. `.github/workflows/publish.yml` (copied from snapp-mcp) tests, publishes to PyPI
(trusted publishing, environment `pypi`, needs setup), creates the GitHub Release and publishes to the MCP Registry. Its `uv run pytest`
step runs offline tests only. Then add the submodule in `../awesome-iran-mcp` per its `AGENTS.md`.
