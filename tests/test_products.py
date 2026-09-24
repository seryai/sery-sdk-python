"""Product methods against a mocked httpx transport — no network."""

import json

import httpx
import pytest

import sery
from sery.errors import InsufficientTokens, ProductNotFound, ProductUnavailable, QueryError


def _client(handler):
    return sery.Client("sdata_test", _transport=httpx.MockTransport(handler))


def test_query_product_posts_sql_and_maps_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/product/abc123/query"
        assert request.headers["Authorization"] == "Bearer sdata_test"
        assert json.loads(request.content) == {"sql": 'select * from "catchments"'}
        return httpx.Response(200, json={"columns": ["city", "n"], "rows": [["Vancouver", 3]], "row_count": 1, "truncated": False, "tokens_spent": 5})

    with _client(handler) as c:
        r = c.query_product("abc123", 'select * from "catchments"')
    assert r.tokens_spent == 5
    assert list(r) == [{"city": "Vancouver", "n": 3}]
    assert len(r) == 1


def test_product_schema_maps_tables():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "hash": "abc123", "name": "Catchments", "kind": "tabular", "price_per_call": 5,
            "tables": [{"table": "catchments", "columns": [{"name": "city", "type": "VARCHAR", "nullable": True}], "row_count_estimate": 12, "size_bytes": 900, "snapshot_at": None, "description": None}],
        })

    with _client(handler) as c:
        s = c.product_schema("abc123")
    assert s.price_per_call == 5
    assert s.tables[0].table == "catchments"
    assert s.tables[0].columns[0].name == "city"


def test_search_product_sends_limit_and_maps_hits():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/product/abc123/search"
        assert json.loads(request.content) == {"query": "zoning", "limit": 3}
        return httpx.Response(200, json={"hits": [{"doc_id": "d1", "title": "Report", "page": 4, "snippet": "…", "score": 0.91}], "tokens_spent": 5})

    with _client(handler) as c:
        r = c.search_product("abc123", "zoning", limit=3)
    assert r.hits[0].doc_id == "d1" and r.hits[0].page == 4
    assert r.tokens_spent == 5 and len(r) == 1


def test_zero_hit_search_is_free():
    with _client(lambda _: httpx.Response(200, json={"hits": [], "tokens_spent": 0})) as c:
        r = c.search_product("abc123", "nothing")
    assert r.hits == [] and r.tokens_spent == 0


@pytest.mark.parametrize(
    "status,detail,exc",
    [
        (402, "Insufficient tokens: have 1, need 5", InsufficientTokens),
        (404, "Product not found", ProductNotFound),
        (409, "Product is not available", ProductUnavailable),
        (400, "Unknown table: secrets", QueryError),
    ],
)
def test_product_status_codes_map_to_product_errors(status, detail, exc):
    with _client(lambda _: httpx.Response(status, json={"detail": detail})) as c:
        with pytest.raises(exc):
            c.query_product("h", "select 1")
