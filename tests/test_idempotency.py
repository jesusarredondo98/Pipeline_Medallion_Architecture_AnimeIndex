"""Prueba de Idempotencia (PRD §4, REQ-S4): dos corridas del mismo lote no duplican filas.
La parte de Gold (REQ-G4) se añade en tests/test_semantic.py una vez existe esa capa."""

from __future__ import annotations

from pathlib import Path

import bronze_batch_writer
import contract_test_kit as ctk
import delta_merge_upsert
import idempotency_test_kit as itk

from pipeline import silver_pipeline
from pipeline.config import PipelineConfig


def _write_sample_batch(bronze_dir: Path, page: int, n: int) -> None:
    records = []
    for i in range(n):
        raw = ctk.make_valid_raw_record(id=page * 100 + i, description_len=80)
        raw.pop("ingestion_timestamp", None)  # lo inyecta bronze_batch_writer al nivel del lote
        records.append(raw)
    bronze_batch_writer.write_batch(bronze_dir, page, records)


def test_silver_es_idempotente(tmp_path: Path):
    bronze_dir = tmp_path / "bronze"
    silver_dir = tmp_path / "silver"
    _write_sample_batch(bronze_dir, page=1, n=5)

    config = PipelineConfig(bronze_dir=str(bronze_dir), silver_dir=str(silver_dir))

    metrics_1 = silver_pipeline.run_silver(config)
    assert metrics_1.filas_leidas == 5
    assert metrics_1.filas_validas == 5
    assert metrics_1.filas_en_cuarentena == 0
    assert metrics_1.filas_nuevas == 5
    assert metrics_1.filas_actualizadas == 0
    assert metrics_1.filas_totales_silver == 5

    total_antes = metrics_1.filas_totales_silver
    metrics_2 = silver_pipeline.run_silver(config)

    itk.assert_silver_idempotent(metrics_2, total_antes, metrics_2.filas_totales_silver)


def test_content_hash_estable_entre_corridas(tmp_path: Path):
    """La limpieza determinista + hash estable (INV-4) es la causa de que Silver sea idempotente."""
    bronze_dir = tmp_path / "bronze"
    silver_dir = tmp_path / "silver"
    _write_sample_batch(bronze_dir, page=1, n=3)
    config = PipelineConfig(bronze_dir=str(bronze_dir), silver_dir=str(silver_dir))

    silver_pipeline.run_silver(config)
    dt1 = delta_merge_upsert.DeltaTable(str(silver_dir / "anime"))
    hashes_1 = sorted(dt1.to_pyarrow_table().column("content_hash").to_pylist())

    silver_pipeline.run_silver(config)  # sin cambios en Bronze
    dt2 = delta_merge_upsert.DeltaTable(str(silver_dir / "anime"))
    hashes_2 = sorted(dt2.to_pyarrow_table().column("content_hash").to_pylist())

    assert hashes_1 == hashes_2


def test_cambio_de_negocio_produce_actualizacion(tmp_path: Path):
    """Un campo de negocio distinto para el mismo id SÍ debe disparar num_target_rows_updated."""
    bronze_dir = tmp_path / "bronze"
    silver_dir = tmp_path / "silver"
    _write_sample_batch(bronze_dir, page=1, n=2)
    config = PipelineConfig(bronze_dir=str(bronze_dir), silver_dir=str(silver_dir))
    silver_pipeline.run_silver(config)

    # Reescribe el mismo lote (misma página) con un score distinto -> mismo id, hash distinto.
    records = []
    for i in range(2):
        raw = ctk.make_valid_raw_record(id=100 + i, description_len=80)
        raw.pop("ingestion_timestamp", None)
        raw["averageScore"] = 99
        records.append(raw)
    bronze_batch_writer.write_batch(bronze_dir, page=1, media_records=records)

    metrics_2 = silver_pipeline.run_silver(config)
    assert metrics_2.filas_nuevas == 0
    assert metrics_2.filas_actualizadas == 2
    assert metrics_2.filas_totales_silver == 2
