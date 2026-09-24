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


# ── Products (marketplace) ─────────────────────────────────────────────


@dataclass
class ProductColumn:
    name: str
    type: str
    nullable: bool = True


@dataclass
class ProductTable:
    """One table a product sells. Reference it by ``table`` in
    ``client.query_product(...)``."""

    table: str
    columns: List[ProductColumn]
    row_count_estimate: Optional[int]
    size_bytes: int
    snapshot_at: Optional[str]
    description: Optional[str]

    @classmethod
    def _from_json(cls, d: dict) -> "ProductTable":
        return cls(
            table=d.get("table", ""),
            columns=[
                ProductColumn(name=c.get("name", ""), type=c.get("type", ""), nullable=c.get("nullable", True))
                for c in d.get("columns", [])
            ],
            row_count_estimate=d.get("row_count_estimate"),
            size_bytes=d.get("size_bytes", 0),
            snapshot_at=d.get("snapshot_at"),
            description=d.get("description"),
        )


@dataclass
class ProductSchema:
    """Tables and columns a product sells. Free to read."""

    hash: str
    name: str
    kind: str  # "tabular" | "document"
    price_per_call: int
    tables: List[ProductTable]

    @classmethod
    def _from_json(cls, d: dict) -> "ProductSchema":
        return cls(
            hash=d.get("hash", ""),
            name=d.get("name", ""),
            kind=d.get("kind", "tabular"),
            price_per_call=d.get("price_per_call", 0),
            tables=[ProductTable._from_json(t) for t in d.get("tables", [])],
        )


@dataclass
class ProductQueryResult:
    """The outcome of ``client.query_product(...)``."""

    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    tokens_spent: int

    @classmethod
    def _from_json(cls, d: dict) -> "ProductQueryResult":
        rows = d.get("rows", [])
        return cls(
            columns=d.get("columns", []),
            rows=rows,
            row_count=d.get("row_count", len(rows)),
            truncated=d.get("truncated", False),
            tokens_spent=d.get("tokens_spent", 0),
        )

    def to_pandas(self):
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - import guard
            raise ImportError("to_pandas() needs pandas — `pip install sery[pandas]`") from exc
        return pd.DataFrame(self.rows, columns=self.columns)

    def __iter__(self):
        for row in self.rows:
            yield dict(zip(self.columns, row))

    def __len__(self) -> int:
        return self.row_count


@dataclass
class ProductSearchHit:
    """One passage from a document product. Never a document."""

    doc_id: str
    title: Optional[str]
    page: Optional[int]
    snippet: str
    score: float


@dataclass
class ProductSearchResult:
    hits: List[ProductSearchHit]
    tokens_spent: int  # 0 when nothing matched — zero-hit searches are free

    @classmethod
    def _from_json(cls, d: dict) -> "ProductSearchResult":
        return cls(
            hits=[
                ProductSearchHit(
                    doc_id=h.get("doc_id", ""),
                    title=h.get("title"),
                    page=h.get("page"),
                    snippet=h.get("snippet", ""),
                    score=float(h.get("score", 0.0)),
                )
                for h in d.get("hits", [])
            ],
            tokens_spent=d.get("tokens_spent", 0),
        )

    def __iter__(self):
        return iter(self.hits)

    def __len__(self) -> int:
        return len(self.hits)


@dataclass
class ProductManifest:
    """Shape of a document product. Free to read."""

    documents: int
    passages: int
    has_page_citations: bool
    titles: List[dict]
    sample_passages: List[str]
    price_per_search: int

    @classmethod
    def _from_json(cls, d: dict) -> "ProductManifest":
        return cls(
            documents=d.get("documents", 0),
            passages=d.get("passages", 0),
            has_page_citations=d.get("has_page_citations", False),
            titles=d.get("titles", []),
            sample_passages=d.get("sample_passages", []),
            price_per_search=d.get("price_per_search", 0),
        )
