<!-- mcp-name: io.github.sepehr071/tapsifood-mcp -->

<div align="center">

# tapsifood-mcp: Tapsi Food MCP server for AI agents

**Let your AI agent shop around on Tapsi Food (تپسی&zwnj;فود).**<br>
An unofficial, read-only MCP server for [Tapsi Food](https://tapsi.food), the food and grocery delivery service in Iran:<br>
search dishes and restaurants near an address, read live menus and reviews, check delivery fees and minimum orders, and catch Tap Time flash deals, from Claude, Cursor or Copilot.

[![PyPI](https://img.shields.io/pypi/v/tapsifood-mcp?color=2563eb)](https://pypi.org/project/tapsifood-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/tapsifood-mcp)](https://pypi.org/project/tapsifood-mcp/)
[![CI](https://github.com/sepehr071/tapsifood-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehr071/tapsifood-mcp/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.sepehr071%2Ftapsifood--mcp-7c3aed)](https://registry.modelcontextprotocol.io/?q=tapsifood-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/tapsifood-mcp/blob/main/LICENSE)

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_tapsifood--mcp-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=tapsifood&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22tapsifood-mcp%22%5D%7D)

[For AI agents](#for-ai-agents) · [Why](#why) · [What it can do](#what-it-can-do) · [Quick start](#quick-start) · [Tools](#tools) · [How it works](#how-it-works) · [Good to know](#good-to-know) · [FAQ](#faq) · [Configuration](#configuration) · [فارسی](#فارسی) · [Development](#development) · [Related](#related-servers)

</div>

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for Tapsi Food (tapsi.food), food and grocery delivery in Iran. Not Snappfood. Queries in Persian match best; prices in Toman.
- **Install:** `uvx tapsifood-mcp` or `claude mcp add tapsifood -- uvx tapsifood-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none, no API key or account. Tapsi Food hangs connections from non-Iranian IPs: run it from Iran without a VPN, or set `TAPSIFOOD_MCP_PROXY` to an HTTP proxy that exits in Iran.
- **Access:** read-only. No login, basket, orders or payment, so no confirmation is needed before calling any tool.
- **Tools:** 11, all prefixed `tf_`. Most need `lat` and `long` (not `tf_reviews`, `tf_find_location`, `tf_list_cities`).
  Typical sequence: `tf_find_location` -> `tf_search_dishes` -> `tf_vendor_info` (-> `tf_menu`, `tf_reviews`).
- **Use when:** the user wants to find a dish or restaurant near an address in Tehran, Mashhad or Shiraz, compare prices and fees, read a menu or reviews, or find discounts.
- **Do not use when:** the user wants to order, pay or log in, or asks about a city Tapsi Food does not serve.
- **Coverage:** Tehran, Mashhad, Shiraz. Elsewhere the API answers 404 or `OutOfCoverage`.
- **Output:** compact JSON. Prices in Toman, ratings 0-5. Null and empty fields are omitted (a missing `rating` = not rated). Menu descriptions are cut to 100 characters and review comments to 250 (`full_text: true` for the whole text). Replies stay under about 15 KB at the maximum `limit`.
- **Machine-readable:** [`server.json`](https://github.com/sepehr071/tapsifood-mcp/blob/main/server.json) and the
  [awesome-iran-mcp catalog](https://github.com/sepehr071/awesome-iran-mcp) (`TOOLS.md`, `servers.json`, `llms.txt`).

## Why

Picking dinner on a delivery app means opening a restaurant, scrolling the menu, then finding out the delivery fee
and minimum order. Asking "what is the cheapest burger near me that is open now, and what will it really cost?" takes
many taps. With `tapsifood-mcp` an agent finds the dish, then checks the restaurant's fee, packaging and minimum order
for your address, and answers with the true cost: dish price minus discount plus packaging plus delivery fee.

> **You:** Cheapest pizza near Valiasr Square, and is it worth the delivery fee?
>
> **Agent:** *calls* `tf_find_location` -> `tf_search_dishes(sort="cheapest")` -> `tf_vendor_info`
>
> It lists the cheapest open matches with price and discount, then checks the chosen restaurant's delivery fee to
> your point, its minimum order and its status.

## What it can do

- **Geocode** a place name or address to coordinates, reverse a point back to an address, and list the cities Tapsi Food shows
- **Search dishes** by name near a delivery point, sorted by relevance, cheapest, biggest discount, rating or distance
- **Search restaurants and stores** by name or cuisine near a point
- **Browse** restaurants or grocery stores with rating, delivery fee, minimum order and ETA, filtered by cuisine, discount, courier or new vendors
- **Catch deals**: Tap Time (تپ تایم) flash deals and the Food Shots (فودشات) discount campaign
- **Read a live menu**: every dish with price, discount and stock
- **Check a vendor** before ordering: delivery fee to your point, minimum order, packaging, ETA, open or closed, hours, address and rating spread
- **Read reviews** with the rating of each ordered dish
- **Read-only by design**: no login, no basket, no orders, no payment

Example prompts:

- "Find the cheapest burger near Enghelab Square in Tehran that is open now."
- "Which restaurants near me have a discount and a delivery fee under 30,000 Toman?"
- "Show the menu of this restaurant and tell me its minimum order."
- "What are the Tap Time flash deals around Azadi Tower right now?"
- "Read the latest reviews of this restaurant. Are people happy with the delivery?"
- <span dir="rtl">ارزان&zwnj;ترین پیتزا نزدیک میدان ولیعصر کدام است؟</span>
- <span dir="rtl">رستوران&zwnj;های تخفیف&zwnj;دار نزدیک من را با هزینه ارسال و حداقل سفارش نشان بده.</span>
- <span dir="rtl">تپ تایم امروز چه غذاهایی دارد؟</span>

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). No API key or account. Run it from Iran, or add `TAPSIFOOD_MCP_PROXY` (see [Configuration](#configuration)).

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add tapsifood -- uvx tapsifood-mcp
# behind a proxy that exits in Iran:
claude mcp add tapsifood -e TAPSIFOOD_MCP_PROXY=http://127.0.0.1:8080 -- uvx tapsifood-mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Settings → Developer → Edit Config, then add:

```json
{
  "mcpServers": {
    "tapsifood": { "command": "uvx", "args": ["tapsifood-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

Add the Claude Desktop block above to `~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project).
</details>

<details>
<summary><b>VS Code (Copilot agent mode)</b></summary>

Click **Install in VS Code** above, or add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "tapsifood": { "type": "stdio", "command": "uvx", "args": ["tapsifood-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Codex CLI</b></summary>

```bash
codex mcp add tapsifood -- uvx tapsifood-mcp
```

Or in `~/.codex/config.toml`:

```toml
[mcp_servers.tapsifood]
command = "uvx"
args = ["tapsifood-mcp"]
```
</details>

<details>
<summary><b>Gemini CLI</b></summary>

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "tapsifood": { "command": "uvx", "args": ["tapsifood-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Windsurf</b></summary>

Add the Claude Desktop block to `~/.codeium/windsurf/mcp_config.json`.
</details>

<details>
<summary><b>Anything else</b></summary>

It is a standard stdio MCP server: run `uvx tapsifood-mcp`, or `pip install tapsifood-mcp` and run `tapsifood-mcp`.
</details>

## Tools

Start with a place: `tf_find_location` or `tf_list_cities` give the `lat` and `long` the other tools need. Vendor codes look like `2y97wk`.

<details open>
<summary><b>Location</b> (3)</summary>

| Tool | What it does |
|---|---|
| `tf_find_location` | Turn a place name or address into latitude/longitude |
| `tf_reverse_geocode` | Describe coordinates as an address with province and city |
| `tf_list_cities` | List the cities Tapsi Food shows, with a center point and whether it delivers there |
</details>

<details open>
<summary><b>Find food and restaurants</b> (5)</summary>

| Tool | What it does |
|---|---|
| `tf_search_dishes` | Search dishes by name near a point; sort by relevance, cheapest, biggest discount, rating or distance |
| `tf_search_vendors` | Search restaurants and stores by name or cuisine near a point |
| `tf_restaurants` | List restaurants or grocery stores with rating, delivery fee, minimum order and ETA; filter by cuisine, discount, courier |
| `tf_deals` | List the Tap Time (تپ تایم) flash deals: discounted dishes with limited stock |
| `tf_discounted_vendors` | List the vendors in the Food Shots (فودشات) discount campaign |
</details>

<details open>
<summary><b>Vendor details</b> (3)</summary>

| Tool | What it does |
|---|---|
| `tf_menu` | Read a vendor's live menu with price, discount and stock |
| `tf_vendor_info` | Get a vendor's delivery fee to a point, minimum order, packaging, ETA, status, hours, address and rating spread |
| `tf_reviews` | Read customer reviews of a vendor with per-dish ratings |
</details>

All 11 tools are annotated `readOnlyHint: true` and return compact JSON.

## How it works

```text
  AI agent  (Claude, Cursor, Copilot, ...)
      │
      │  MCP over stdio
      ▼
  tapsifood-mcp  (runs on your machine)
      │
      │  HTTPS
      └──────▶  api.tapsi.food   dishes, vendors, menus, reviews, deals
```

`tapsifood-mcp` runs locally and calls the same endpoints the tapsi.food web app uses. There is no hosted server in
between and no API key. Requests go out through a Chrome-impersonating client, at most 2 at a time with a little
jitter. GET answers are cached for 60 seconds, a timeout, network error, 5xx or 429 is retried up to twice, and it
only talks to `api.tapsi.food`. It only reads.

## Good to know

- **Prices are in Toman**, as the API sends them. Ratings are 0-5.
- **Delivery depends on the point.** Menus, fees and coverage change with the latitude and longitude you pass. HTTP 200 does not mean the vendor delivers there: `delivery_fee: null` means out of coverage.
- **Coverage:** Tehran, Mashhad and Shiraz. Elsewhere feeds answer 404, search finds nothing and the menu says `OutOfCoverage`.
- **Network:** Tapsi Food hangs connections from non-Iranian IPs (a timeout on every call is the sign). Run it from Iran without a VPN, or set `TAPSIFOOD_MCP_PROXY`. System proxy variables are ignored on purpose.
- **Open vendors only in search.** Dish and vendor search list only restaurants open now (the site does the same), so at night `total` can be 0. `tf_restaurants` and `tf_discounted_vendors` also list closed vendors, flagged `open: false`.
- **Search-index prices can lag the menu:** confirm with `tf_menu`. Menu and profile minimums sometimes differ; `tf_vendor_info` returns both (`min_order`, `min_order_profile`).
- **Sorting dishes:** `top_rated`, `cheapest` and `biggest_discount` sort the first 100 matches, not the whole result set.
- **ETA is an upper bound:** `eta_max` is the site's "up to N minutes"; the API sends no lower bound.
- **Reviews:** `total` counts every review including rating-only ones; only reviews with a comment are listed, so a page can hold fewer than `limit` (keep paging while `has_more`). Writer names are left out on purpose.
- **Browse pages:** page 1 also carries filter and banner widgets, so it lists fewer vendors than `page_size`.
- **What it does not do:** no login, basket, orders or payment. Coupons are not exposed by the site's anonymous API.

## FAQ

<details>
<summary><b>Is there a Tapsi Food API or MCP server for AI agents?</b></summary>

Tapsi Food has no documented public API. `tapsifood-mcp` is an unofficial MCP server with 11 read-only tools that calls
the same endpoints the tapsi.food web app uses and returns compact JSON for AI agents.
</details>

<details>
<summary><b>How do I use Tapsi Food with Claude, Cursor or Copilot?</b></summary>

Add the server with `claude mcp add tapsifood -- uvx tapsifood-mcp`, or use the matching config in
[Quick start](#quick-start), then ask in plain language, in Persian or English.
</details>

<details>
<summary><b>Is it official, safe and free?</b></summary>

It is unofficial and not affiliated with Tapsi. It is read-only (no login, basket or payment), runs on your machine,
and is free under the MIT license.
</details>

<details>
<summary><b>Can it order food for me?</b></summary>

No, and that is deliberate. It has no login and never calls basket, order or payment endpoints. The agent finds the
best option; you order in the Tapsi app.
</details>

<details>
<summary><b>Do I need an Iranian IP?</b></summary>

Yes, in practice. Tapsi Food hangs connections from non-Iranian IPs, so every call times out. Run it from Iran without a
VPN, or set `TAPSIFOOD_MCP_PROXY` to an HTTP proxy that exits in Iran.
</details>

<details>
<summary><b>Which cities are covered?</b></summary>

Tehran, Mashhad and Shiraz. `tf_list_cities` shows what Tapsi Food lists and whether it delivers there. For a point outside
coverage, feeds answer 404 and `tf_menu` reports `OutOfCoverage`.
</details>

<details>
<summary><b>Why does a search return no results at night?</b></summary>

Dish and vendor search only return restaurants open now, like the site's own search. Use `tf_restaurants` to list closed
vendors too; they are flagged `open: false`.
</details>

<details>
<summary><b>Is the delivery fee and minimum order exact?</b></summary>

`tf_vendor_info` gives the fee to the point you pass, the minimum order, packaging and ETA from Tapsi. The menu and the
vendor profile sometimes disagree on the minimum order, so both are returned. ETA is an upper bound.
</details>

<details>
<summary><b>How do I debug what the agent sees?</b></summary>

```bash
npx @modelcontextprotocol/inspector uvx tapsifood-mcp
```
</details>

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TAPSIFOOD_MCP_PROXY` | unset | Optional HTTP proxy URL. Tapsi Food does not answer non-Iranian exit IPs (connections hang); system proxy settings are ignored. Also accepts a comma-separated list: one is used until it gets blocked or fails to connect, then the next |

<a id="فارسی"></a>

## فارسی

<div dir="rtl">

### سرور MCP تپسی&zwnj;فود برای دستیار هوش مصنوعی

**tapsifood-mcp** یک سرور MCP غیررسمی و فقط&zwnj;خواندنی برای تپسی&zwnj;فود (Tapsi Food)، سرویس سفارش آنلاین غذا و سوپرمارکت در ایران، است. این سرور به دستیار هوش مصنوعی شما (Claude، Cursor، Copilot و ...) اجازه می&zwnj;دهد
غذا و رستوران نزدیک یک آدرس را جستجو کند، منوی زنده و نظرات را بخواند و هزینه ارسال و حداقل سفارش را بررسی کند.

**چه کارهایی می&zwnj;کند**

- **پیدا کردن آدرس**: نام مکان یا آدرس را به مختصات تبدیل می&zwnj;کند و فهرست شهرهای تپسی&zwnj;فود را نشان می&zwnj;دهد.
- **جستجوی غذا** نزدیک آدرس شما، مرتب&zwnj;شده بر اساس ارزان&zwnj;ترین، بیشترین تخفیف، امتیاز یا فاصله.
- **جستجوی رستوران و فروشگاه** بر اساس نام یا نوع غذا، و فهرست رستوران&zwnj;ها و سوپرمارکت&zwnj;ها با امتیاز، هزینه ارسال، حداقل سفارش و زمان تحویل.
- **تخفیف&zwnj;ها**: پیشنهادهای تپ تایم و رستوران&zwnj;های فودشات.
- **منوی زنده** هر رستوران با قیمت، تخفیف و موجودی.
- **بررسی رستوران** پیش از سفارش: هزینه ارسال تا آدرس شما، حداقل سفارش، هزینه بسته&zwnj;بندی، ساعت کاری و باز یا بسته بودن.
- **نظرات مشتریان** با امتیاز هر غذای سفارش&zwnj;داده&zwnj;شده.

**نکته&zwnj;ها**

- فقط خواندنی است: وارد حساب نمی&zwnj;شود، سبد خرید نمی&zwnj;سازد و سفارش ثبت نمی&zwnj;کند.
- همه قیمت&zwnj;ها به تومان است و امتیازها از ۵.
- شهرهای تهران، مشهد و شیراز پوشش داده می&zwnj;شوند.
- تپسی&zwnj;فود از IP خارج از ایران پاسخ نمی&zwnj;دهد: بدون VPN و از ایران اجرا کنید، یا متغیر `TAPSIFOOD_MCP_PROXY` را روی یک پراکسی HTTP با خروجی ایران بگذارید.
- جستجوی غذا و رستوران فقط رستوران&zwnj;های باز را نشان می&zwnj;دهد، پس شب&zwnj;ها ممکن است نتیجه&zwnj;ای نباشد.
- کلید API لازم نیست و روی سیستم خود شما اجرا می&zwnj;شود.

**کلیدواژه&zwnj;ها:** تپسی&zwnj;فود، تپسی فود، tapsi food، سفارش آنلاین غذا، سفارش غذا، پیتزا، برگر، رستوران نزدیک من، تپ تایم، فودشات، سوپرمارکت آنلاین، سرور MCP تپسی&zwnj;فود.

**نصب** (اول [uv](https://docs.astral.sh/uv/getting-started/installation/) را نصب کنید). در Claude Code:

</div>

```bash
claude mcp add tapsifood -- uvx tapsifood-mcp
```

<div dir="rtl">

در Claude Desktop، Cursor و بقیه برنامه&zwnj;ها همان تنظیم بخش [Quick start](#quick-start) را بگذارید.

**نمونه پرسش&zwnj;ها**

- «ارزان&zwnj;ترین پیتزا نزدیک میدان ولیعصر کدام است؟»
- «رستوران&zwnj;های تخفیف&zwnj;دار نزدیک من را با هزینه ارسال و حداقل سفارش نشان بده.»
- «منوی این رستوران را بده و بگو حداقل سفارشش چقدر است.»
- «تپ تایم امروز چه غذاهایی دارد؟»
- «نظرات اخیر این رستوران را بخوان؛ از ارسال راضی بودند؟»

</div>

## Development

```bash
git clone https://github.com/sepehr071/tapsifood-mcp && cd tapsifood-mcp
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline unit tests
uv run python -m pytest -m live -q  # real API; needs an Iranian IP
uv build
```

Tools live in `src/tapsifood_mcp/location.py`, `discover.py` and `vendor.py`; each is a typed async function with a
docstring that tells the agent when to use it. Issues and PRs are welcome.

Releases: bump the version in `pyproject.toml` and `server.json`, then push a `v*` tag. GitHub Actions tests, publishes
to PyPI and the [MCP Registry](https://registry.modelcontextprotocol.io), and creates the GitHub Release.

## Related servers

- [awesome-iran-mcp](https://github.com/sepehr071/awesome-iran-mcp): catalog of all Iranian-service MCP servers
- [Snapp MCP server](https://github.com/sepehr071/snapp-mcp) for Snappfood and SnappMarket food and grocery delivery
- [Okala MCP server](https://github.com/sepehr071/okala-mcp) for online grocery shopping
- [Digikala MCP server](https://github.com/sepehr071/digikala-mcp) for Iran's largest online store
- [Torob MCP server](https://github.com/sepehr071/torob-mcp) for price comparison across Iranian shops

## Disclaimer

Unofficial and not affiliated with or endorsed by Tapsi. It is read-only and uses the endpoints of the tapsi.food web
app, which can change without notice. Please keep request rates reasonable.

## Author

<a href="https://www.linkedin.com/in/sepehr-radmard"><img src="https://raw.githubusercontent.com/sepehr071/awesome-iran-mcp/main/assets/author-banner.png" alt="Sepehr Radmard: open-source MCP servers for the Iranian web. LinkedIn: linkedin.com/in/sepehr-radmard" width="100%"></a>

Built and maintained by **Sepehr Radmard** (سپهر رادمرد). Connect on [LinkedIn](https://www.linkedin.com/in/sepehr-radmard) or follow [@sepehr071 on GitHub](https://github.com/sepehr071) for more MCP servers for Iranian websites, all listed in [awesome-iran-mcp](https://github.com/sepehr071/awesome-iran-mcp). If this saves you time, a star on the repo helps other people find it.

## License

[MIT](https://github.com/sepehr071/tapsifood-mcp/blob/main/LICENSE)
