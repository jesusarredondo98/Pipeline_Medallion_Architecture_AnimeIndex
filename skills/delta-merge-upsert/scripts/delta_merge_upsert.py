"""Crea/abre /silver/anime como Delta table y ejecuta el MERGE nativo de delta-rs (REQ-S3).
El esquema se deriva del contrato Pydantic (anime-data-contract) — nunca se infiere desde una
tabla vacía sin tipos explícitos (trampa conocida, Agents.md §6)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

# Deriva 1:1 de AnimeRecord (anime-data-contract) + content_hash (content-hash-builder).
SCHEMA_COLUMNS: list[tuple[str, pa.DataType]] = [
    ("id", pa.int64()),
    ("id_mal", pa.int64()),
    ("title_romaji", pa.string()),
    ("title_english", pa.string()),
    ("title_native", pa.string()),
    ("format", pa.string()),
    ("status", pa.string()),
    ("episodes", pa.int64()),
    ("duration", pa.int64()),
    ("season", pa.string()),
    ("season_year", pa.int64()),
    ("average_score", pa.int64()),
    ("popularity", pa.int64()),
    ("favourites", pa.int64()),
    ("genres", pa.list_(pa.string())),
    ("studios", pa.list_(pa.string())),
    ("start_year", pa.int64()),
    ("start_month", pa.int64()),
    ("start_day", pa.int64()),
    ("end_year", pa.int64()),
    ("end_month", pa.int64()),
    ("end_day", pa.int64()),
    ("description", pa.string()),
    ("ingestion_timestamp", pa.string()),
    ("content_hash", pa.string()),
]

_COLUMN_NAMES = [name for name, _ in SCHEMA_COLUMNS]


def arrow_schema() -> pa.Schema:
    return pa.schema(SCHEMA_COLUMNS)


def ensure_table(silver_anime_dir: Path) -> DeltaTable:
    """REQ-S3 paso 1: crea la tabla vacía con el esquema del contrato si no existe."""
    path_str = str(silver_anime_dir)
    if not DeltaTable.is_deltatable(path_str):
        empty = pa.table({name: pa.array([], type=dtype) for name, dtype in SCHEMA_COLUMNS}, schema=arrow_schema())
        write_deltalake(path_str, empty, mode="overwrite")
    return DeltaTable(path_str)


def deduplicate_by_id(df: pl.DataFrame) -> pl.DataFrame:
    """REQ-S3 paso 2: conserva la última ocurrencia por id. El MERGE de Delta falla o da
    resultado indefinido si el source tiene ids repetidos."""
    return df.unique(subset=["id"], keep="last", maintain_order=True)


def upsert(silver_anime_dir: Path, df: pl.DataFrame) -> dict:
    """`df` ya debe estar deduplicada por id y traer `content_hash`. REQ-S3 paso 4: MERGE con
    `whenMatchedUpdate` condicionado a hash distinto + `whenNotMatchedInsertAll`."""
    dt = ensure_table(silver_anime_dir)
    source = df.select(_COLUMN_NAMES).to_arrow()

    updates = {col: f"source.{col}" for col in _COLUMN_NAMES}
    merger = dt.merge(
        source=source,
        predicate="target.id = source.id",
        source_alias="source",
        target_alias="target",
    )
    merger = merger.when_matched_update(
        updates=updates,
        predicate="target.content_hash != source.content_hash",
    )
    merger = merger.when_not_matched_insert_all()
    return merger.execute()


def total_rows(silver_anime_dir: Path) -> int:
    """`filas_totales_silver`: conteo post-merge de la Delta table (REQ-S4)."""
    dt = DeltaTable(str(silver_anime_dir))
    return dt.to_pyarrow_table().num_rows
