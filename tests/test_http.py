import httpx
import pytest

from tapsifood_mcp import http
from tapsifood_mcp.registry import clip


@pytest.mark.anyio
async def test_get_cached_and_retried_once(api, monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr(http.asyncio, "sleep", no_sleep)
    hits = iter([httpx.Response(503), httpx.Response(200, json={"a": 1})])
    api["/x"] = lambda request: next(hits)

    assert await http.fetch("/x", {"q": 1}) == {"a": 1}
    assert await http.fetch("/x", {"q": 1}) == {"a": 1}  # served from cache
    assert len(api.calls) == 2


@pytest.mark.anyio
async def test_list_param_repeats_key_and_none_is_dropped(api):
    api["/x"] = {"ok": True}
    await http.fetch("/x", {"f": ["a", "b"], "skip": None})
    assert api.calls[0].url.query.decode() == "f=a&f=b"


@pytest.mark.anyio
async def test_cached_body_is_not_shared(api):
    api["/m"] = lambda request: httpx.Response(200, json={"a": [1]})
    first = await http.fetch("/m")
    first["a"].append(2)
    assert await http.fetch("/m") == {"a": [1]}


@pytest.mark.anyio
async def test_redirect_refused(api):
    api["/r"] = lambda request: httpx.Response(302, headers={"Location": "https://evil.example/"})
    with pytest.raises(http.ApiError, match="non-JSON"):
        await http.fetch("/r")
    assert len(api.calls) == 1


def test_proxy_env_is_comma_list(monkeypatch):
    monkeypatch.setenv("TAPSIFOOD_MCP_PROXY", " http://a:1 ,http://b:2,")
    assert http._proxies() == ["http://a:1", "http://b:2"]


def test_clip():
    assert clip(None) is None and clip("ab") == "ab"
    assert clip("x" * 500) == "x" * 400 + "...[cut]"
    assert clip("x" * 500, True) == "x" * 500
