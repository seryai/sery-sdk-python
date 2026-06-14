# Sery Python SDK

Query your private data mesh by **`sery://` address** — one SQL statement, run on whichever machine holds the data. Raw data never moves through Sery; only result rows come back.

```bash
pip install sery          # core
pip install sery[pandas]  # + .to_pandas()
```

## Quick start

```python
import sery

client = sery.Client(api_key="sery_...")  # from app.sery.ai → Settings → API Keys

df = client.query("""
    SELECT customer, SUM(amount) AS total
    FROM 'sery://sam-laptop/local/sales/orders.parquet'
    GROUP BY customer
    ORDER BY total DESC
""").to_pandas()
```

## Addresses

Sources are addressed as `sery://<machine>/<protocol>/<path>`:

- `<machine>` — a machine's stable id or its name (e.g. `sam-laptop`)
- `<protocol>` — `local`, `s3`, or `https`
- `<path>` — the file path / bucket key

Discover what's addressable with the catalog:

```python
for src in client.catalog():
    print(src.sery_uri, "—", src.machine, src.file_format)
    # sery://sam-laptop/local/sales/orders.parquet — sam-laptop parquet
```

Pass any `sery_uri` straight into `query()`.

## Results

```python
result = client.query("SELECT * FROM 'sery://my-mac/local/data.parquet' LIMIT 5")

result.columns          # ['id', 'name', ...]
result.rows             # [[1, 'a'], [2, 'b'], ...]
for row in result:      # iterate as dicts
    print(row["name"])
result.to_pandas()      # DataFrame (needs pandas)

result.incomplete       # True if a machine didn't respond
result.warnings         # human-readable warnings to surface
```

> When `incomplete` is `True`, one or more machines were offline — check
> `warnings` before trusting an aggregate (a SUM/COUNT may undercount).

## Errors

Every failure is a typed exception (`sery.errors`):

| Exception | When |
|-----------|------|
| `AuthError` | missing / invalid API key (401) |
| `QueryError` | no `sery://` refs, bad address, unsupported protocol (400) |
| `MachineNotFound` | unknown machine (404) |
| `AmbiguousMachine` | a name matched >1 machine — `.candidates` lists machine_ids (409) |
| `CrossMachineJoinUnsupported` | the query spans machines — `.machines` (422) |
| `MachinesUnavailable` | every targeted machine offline — `.failures` (503) |

```python
import sery

try:
    client.query("SELECT * FROM 'sery://laptop/local/x.parquet'")
except sery.AmbiguousMachine as e:
    for c in e.candidates:
        print(c["label"], c["machine_id"])  # re-issue with the machine_id
```

## Limitations (v1)

- All sources in one query must live on the **same machine** — cross-machine joins raise `CrossMachineJoinUnsupported`.
- Routable protocols: `local`, `s3`, `https`.

## License

MIT
