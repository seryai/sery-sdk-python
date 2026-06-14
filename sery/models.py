"""Result and catalog value objects returned by the client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class QueryResult:
    """The outcome of ``client.query(...)``.

    ``rows`` are plain lists aligned to ``columns``. ``incomplete`` is True
    when one or more targeted machines didn't respond — read ``warnings``
    before trusting an aggregate.
    """

    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    total_rows: int
    machines_queried: List[str] = field(default_factory=list)
    machines_failed: List[dict] = field(default_factory=list)
    incomplete: bool = False
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def _from_json(cls, data: dict) -> "QueryResult":
        return cls(
            columns=data.get("columns", []),
            rows=data.get("rows", []),
            row_count=data.get("row_count", 0),
            total_rows=data.get("total_rows", data.get("row_count", 0)),
            machines_queried=data.get("machines_queried", []),
            machines_failed=data.get("machines_failed", []),
            incomplete=data.get("incomplete", False),
            warnings=data.get("warnings", []),
        )

    def to_pandas(self):
        """Return the result as a pandas DataFrame.

        pandas is an optional dependency — install ``sery[pandas]`` (or
        just ``pip install pandas``) to use this.
        """
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - import guard
            raise ImportError(
                "to_pandas() needs pandas — install with "
                "`pip install sery-sdk[pandas]`"
            ) from exc
        return pd.DataFrame(self.rows, columns=self.columns)

    def __iter__(self):
        """Iterate rows as dicts keyed by column name."""
        for row in self.rows:
            yield dict(zip(self.columns, row))

    def __len__(self) -> int:
        return self.row_count


@dataclass
class CatalogColumn:
    name: str
    type: str


@dataclass
class CatalogSource:
    """One addressable source in the workspace. Pass ``sery_uri`` straight
    into ``client.query(...)``."""

    sery_uri: Optional[str]
    name: str
    machine: Optional[str]
    file_format: str
    size_bytes: int
    row_count_estimate: Optional[int]
    columns: List[CatalogColumn]
    description: Optional[str]

    @classmethod
    def _from_json(cls, data: dict) -> "CatalogSource":
        return cls(
            sery_uri=data.get("sery_uri"),
            name=data.get("name", ""),
            machine=data.get("machine"),
            file_format=data.get("file_format", ""),
            size_bytes=data.get("size_bytes", 0),
            row_count_estimate=data.get("row_count_estimate"),
            columns=[
                CatalogColumn(name=c.get("name", ""), type=c.get("type", ""))
                for c in data.get("columns", [])
            ],
            description=data.get("description"),
        )
