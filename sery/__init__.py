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
    MachineNotFound,
    MachinesUnavailable,
    QueryError,
    SeryError,
)
from sery.models import CatalogColumn, CatalogSource, QueryResult

__all__ = [
    "Client",
    "DEFAULT_BASE_URL",
    "QueryResult",
    "CatalogSource",
    "CatalogColumn",
    # errors
    "SeryError",
    "AuthError",
    "QueryError",
    "MachineNotFound",
    "AmbiguousMachine",
    "CrossMachineJoinUnsupported",
    "MachinesUnavailable",
    "APIError",
]

__version__ = "0.1.0"
