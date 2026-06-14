"""The Sery client — query your data mesh by sery:// address.

    import sery

    client = sery.Client(api_key="sery_...")
    df = client.query('''
        SELECT customer, SUM(amount) AS total
        FROM 'sery://sam-laptop/local/sales/orders.parquet'
        GROUP BY customer
    ''').to_pandas()

Data never moves through Sery — the query runs on the machine that holds the
file, and only result rows come back.
"""

from __future__ import annotations

from typing import List, Optional

import httpx

from sery.errors import raise_for_response
from sery.models import CatalogSource, QueryResult

DEFAULT_BASE_URL = "https://data.sery.ai"
_DEFAULT_TIMEOUT = 120.0


class Client:
    """A synchronous client for the Sery data API (data.sery.ai).

    Args:
        api_key: A workspace API key (``sery_…``), minted at
            app.sery.ai → Settings → API Keys.
        base_url: Override the API host (e.g. for staging or self-host).
        timeout: Per-request timeout in seconds. Queries against large remote
            files can take a while; the default is generous.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        _transport: Optional[httpx.BaseTransport] = None,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": f"sery-sdk-python/{_version()}",
            },
            timeout=timeout,
            transport=_transport,
        )

    # ── context manager ────────────────────────────────────────────────

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # ── requests ───────────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code // 100 != 2:
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001 - non-JSON error body
                body = resp.text
            raise_for_response(resp.status_code, body)
        return resp.json()

    # ── API ────────────────────────────────────────────────────────────

    def query(self, sql: str, *, max_rows: int = 10_000) -> QueryResult:
        """Run a sery:// addressed SQL query.

        Reference sources by their ``sery://<machine>/<protocol>/<path>``
        address (get them from :meth:`catalog`). All sources in one query
        must live on the same machine.

        Raises a typed :mod:`sery.errors` exception on failure
        (MachineNotFound, AmbiguousMachine, CrossMachineJoinUnsupported,
        MachinesUnavailable, QueryError, AuthError).
        """
        data = self._request(
            "POST",
            "/public/v1/query",
            json={"sql": sql, "max_rows": max_rows},
        )
        return QueryResult._from_json(data)

    def catalog(self) -> List[CatalogSource]:
        """List the workspace's addressable sources, each with its sery://
        address and column schema."""
        data = self._request("GET", "/public/v1/catalog")
        return [CatalogSource._from_json(s) for s in data.get("sources", [])]


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("sery")
    except Exception:  # noqa: BLE001 - not installed as a dist (editable/source)
        return "0.0.0"
