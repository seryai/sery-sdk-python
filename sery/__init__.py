"""Sery Python SDK — query your private data mesh by sery:// address.

    import sery
    client = sery.Client(api_key="sery_...")
    df = client.query("SELECT * FROM 'sery://my-laptop/local/data.parquet'").to_pandas()
"""

from sery.client import DEFAULT_BASE_URL, Client
from sery.errors import (
    AmbiguousMachine,
    APIError,
    AuthError,
    CrossMachineJoinUnsupported,
    InsufficientTokens,
    MachineNotFound,
    MachinesUnavailable,
    ProductNotFound,
    ProductUnavailable,
    QueryError,
    SeryError,
)
from sery.models import (
    CatalogColumn,
    CatalogSource,
    ProductColumn,
    ProductManifest,
    ProductQueryResult,
    ProductSchema,
    ProductSearchHit,
    ProductSearchResult,
    ProductTable,
    QueryResult,
)

__all__ = [
    "Client",
    "DEFAULT_BASE_URL",
    "QueryResult",
    "CatalogSource",
    "CatalogColumn",
    "ProductSchema",
    "ProductTable",
    "ProductColumn",
    "ProductQueryResult",
    "ProductSearchHit",
    "ProductSearchResult",
    "ProductManifest",
    # errors
    "SeryError",
    "AuthError",
    "QueryError",
    "MachineNotFound",
    "AmbiguousMachine",
    "CrossMachineJoinUnsupported",
    "MachinesUnavailable",
    "InsufficientTokens",
    "ProductNotFound",
    "ProductUnavailable",
    "APIError",
]

__version__ = "0.3.0"
