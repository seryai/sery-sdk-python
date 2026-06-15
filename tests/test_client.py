"""Client tests against a mocked httpx transport — no network."""

import json

import httpx
import pytest

import sery
from sery.errors import (
    AmbiguousMachine,
    AuthError,
    CrossMachineJoinUnsupported,
    MachineNotFound,
    MachinesUnavailable,
    QueryError,
)


def _client(handler):
    """Build a Client whose HTTP calls are served by `handler`."""
    return sery.Client("sery_test", _transport=httpx.MockTransport(handler))


# ─── query: success ────────────────────────────────────────────────────


def test_query_returns_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/query"
        assert request.headers["Authorization"] == "Bearer sery_test"
        body = json.loads(request.content)
        assert body["sql"].startswith("SELECT")
        return httpx.Response(
            200,
            json={
                "columns": ["customer", "total"],
                "rows": [["acme", 42]],
                "row_count": 1,
                "total_rows": 1,
                "machines_queried": ["MacBook"],
                "machines_failed": [],
                "incomplete": False,
                "warnings": [],
            },
        )

    with _client(handler) as client:
        result = client.query("SELECT * FROM 'sery://m1/local/x.parquet'")

    assert result.columns == ["customer", "total"]
    assert result.rows == [["acme", 42]]
    assert result.row_count == 1
    assert list(result) == [{"customer": "acme", "total": 42}]
    assert len(result) == 1


def test_query_to_pandas():
    pd = pytest.importorskip("pandas")

    def handler(request):
        return httpx.Response(
            200,
            json={
                "columns": ["a", "b"],
                "rows": [[1, 2], [3, 4]],
                "row_count": 2,
                "total_rows": 2,
            },
        )

    with _client(handler) as client:
        df = client.query("SELECT * FROM 'sery://m1/local/x.parquet'").to_pandas()

    assert list(df.columns) == ["a", "b"]
    assert df.shape == (2, 2)


def test_query_passes_max_rows():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"columns": [], "rows": [], "row_count": 0, "total_rows": 0}
        )

    with _client(handler) as client:
        client.query("SELECT 1 FROM 'sery://m1/local/x.parquet'", max_rows=50)

    assert seen["body"]["max_rows"] == 50


# ─── query: error mapping ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "status,detail,exc",
    [
        (401, "bad key", AuthError),
        (400, "no sery refs", QueryError),
        (404, "no machine", MachineNotFound),
    ],
)
def test_query_simple_errors(status, detail, exc):
    def handler(request):
        return httpx.Response(status, json={"detail": detail})

    with _client(handler) as client:
        with pytest.raises(exc):
            client.query("SELECT 1 FROM 'sery://x/local/y.parquet'")


def test_query_ambiguous_carries_candidates():
    def handler(request):
        return httpx.Response(
            409,
            json={
                "detail": {
                    "message": "ambiguous",
                    "candidates": [
                        {"machine_id": "m1", "label": "sam"},
                        {"machine_id": "m2", "label": "claire"},
                    ],
                }
            },
        )

    with _client(handler) as client:
        with pytest.raises(AmbiguousMachine) as exc:
            client.query("SELECT 1 FROM 'sery://laptop/local/y.parquet'")

    ids = {c["machine_id"] for c in exc.value.candidates}
    assert ids == {"m1", "m2"}


def test_query_cross_machine_carries_machines():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "detail": {
                    "message": "cross-machine",
                    "machines": [{"machine_id": "m1", "label": "a"}],
                }
            },
        )

    with _client(handler) as client:
        with pytest.raises(CrossMachineJoinUnsupported) as exc:
            client.query("SELECT 1 FROM 'sery://a/local/x' JOIN 'sery://b/local/y'")

    assert exc.value.machines[0]["machine_id"] == "m1"


def test_query_unavailable_carries_failures():
    def handler(request):
        return httpx.Response(
            503,
            json={
                "detail": {
                    "message": "down",
                    "failures": [{"machine": "MacBook", "error": "offline"}],
                }
            },
        )

    with _client(handler) as client:
        with pytest.raises(MachinesUnavailable) as exc:
            client.query("SELECT 1 FROM 'sery://m1/local/x.parquet'")

    assert exc.value.failures == [{"machine": "MacBook", "error": "offline"}]


# ─── catalog ───────────────────────────────────────────────────────────


def test_catalog_parses_sources():
    def handler(request):
        assert request.url.path == "/catalog"
        return httpx.Response(
            200,
            json={
                "sources": [
                    {
                        "sery_uri": "sery://m1/local/orders.parquet",
                        "name": "orders.parquet",
                        "machine": "MacBook",
                        "file_format": "parquet",
                        "size_bytes": 100,
                        "row_count_estimate": 10,
                        "columns": [{"name": "id", "type": "BIGINT"}],
                        "description": "orders",
                    }
                ],
                "total": 1,
            },
        )

    with _client(handler) as client:
        sources = client.catalog()

    assert len(sources) == 1
    assert sources[0].sery_uri == "sery://m1/local/orders.parquet"
    assert sources[0].columns[0].name == "id"


# ─── misc ──────────────────────────────────────────────────────────────


def test_requires_api_key():
    with pytest.raises(ValueError):
        sery.Client("")


def test_default_base_url():
    assert sery.DEFAULT_BASE_URL == "https://data.sery.ai"
