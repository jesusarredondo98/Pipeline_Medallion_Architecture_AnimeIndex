"""Orquestador de la capa Silver. Compone skills atómicas: limpieza → contrato → (cuarentena |
hash+dedupe+merge) → métricas. No contiene lógica de negocio propia (Agents.md Fase 2)."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from pipeline import skill_loader  # noqa: F401
from pipeline.config import PipelineConfig

import anime_data_contract
import content_hash_builder
import delta_merge_upsert
import html_description_normalizer
import quarantine_writer
import silver_metrics_emitter


def _iter_bronze_records(bronze_dir: Path):
    for path in sorted(bronze_dir.glob("anime_catalog_batch_*.json")):
        envelope = json.loads(path.read_text(encoding="utf-8"))
        ingestion_timestamp = envelope["ingestion_timestamp"]
        for record in envelope["records"]:
            enriched = dict(record)
            enriched["ingestion_timestamp"] = ingestion_timestamp
            yield enriched


def run_silver(config: PipelineConfig) -> silver_metrics_emitter.SilverRunMetrics:
    bronze_dir = Path(config.bronze_dir)
    silver_dir = Path(config.silver_dir)
    silver_anime_dir = silver_dir / "anime"

    filas_leidas = 0
    filas_validas = 0
    filas_en_cuarentena = 0
    valid_rows: list[dict] = []

    for raw in _iter_bronze_records(bronze_dir):
        filas_leidas += 1
        cleaned = html_description_normalizer.clean_description(raw.get("description"))
        try:
            record = anime_data_contract.validate_record(raw, cleaned, config.min_desc_len)
        except anime_data_contract.ContractViolation as exc:
            quarantine_writer.write_quarantine(silver_dir, exc.motivo_rechazo, exc.original_payload)
            filas_en_cuarentena += 1
            continue

        row = record.model_dump()
        row["content_hash"] = content_hash_builder.compute_content_hash(row)
        valid_rows.append(row)
        filas_validas += 1

    delta_merge_upsert.ensure_table(silver_anime_dir)

    if valid_rows:
        df = pl.DataFrame(valid_rows)
        df = delta_merge_upsert.deduplicate_by_id(df)
        merge_result = delta_merge_upsert.upsert(silver_anime_dir, df)
    else:
        merge_result = {"num_target_rows_inserted": 0, "num_target_rows_updated": 0}

    filas_totales_silver = delta_merge_upsert.total_rows(silver_anime_dir)

    return silver_metrics_emitter.build_metrics(
        filas_leidas=filas_leidas,
        filas_validas=filas_validas,
        filas_en_cuarentena=filas_en_cuarentena,
        merge_result=merge_result,
        filas_totales_silver=filas_totales_silver,
    )
